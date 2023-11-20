import pathlib
import shutil
import tempfile
import uuid
from io import BytesIO
from pathlib import Path
import tarfile
from typing import Dict, Tuple, List, Any
import json
import docx
import multiprocessing as mp
import gc
from docx.document import Document
import logging

from orm.models import DocMetadataRecordDB, PageMetadataRecordDB
from src.annotation import language_detection as lang_detect
from src.annotation import sanity_checks
from src.annotation.annotation_objects import *
from src.annotation.annotation_quality import calc_annotation_quality_score
from src.annotation.colorization import ColorizationHandler
from src.annotation.colorization.colorize_doc import colorize_word_doc
from src.annotation.config import AnnotationConfig
from src.annotation.entity_detection import detect_entities_in_document
from src.annotation.oxml_metadata import get_oxml_metadata
from src.annotation.postprocessing import *
from src.annotation.preprocessing.highlighting import sanitize_highlighting
from src.annotation.soffice.conversion_manager import ConversionManager
from src.annotation.text.text_entity_matching import assign_entities_to_words
from src.annotation.text.text_extraction import *
from src.annotation.utils.identifiers import get_page_num_from_page_id
from src.annotation.utils.pdf_utils import *
from src.annotation.utils.docx_utils import get_page_count
from src.exceptions import *
from src.annotation.utils.zip_bomb import *

import settings.entities
import settings.filesystem as fs_settings

STATUS_SUCCESS = "SUCCESS"
STATUS_FAIL = "FAIL"


class AnnotatorProcess(mp.Process):

    def __init__(
            self,
            annotator_id: str,
            soffice_executable: str,
            annotations_dir: Path,
            meta_dir: Path,
            text_dir: Path,
            failed_dir: Path,
            crawl_id: str,
            config: AnnotationConfig,
            input_tars: List[Path],
            output_queue: mp.Queue,
            max_docs: int,
            logger_name: str
    ):
        super(AnnotatorProcess, self).__init__()
        self.annotator_id = annotator_id
        self.annotations_dir = annotations_dir
        self.meta_dir = meta_dir
        self.text_dir = text_dir
        self.failed_dir = failed_dir
        self.soffice_executable = soffice_executable
        self.crawl_id = crawl_id
        self.config = config
        self.input_tars = input_tars
        self.output_queue = output_queue
        self.max_docs = max_docs

        # init logger
        self.logger = logging.getLogger(name=logger_name)
        self.logger.setLevel(logging.DEBUG)

        if (
                self.config.image_height is None
                and
                self.config.image_width is None
        ):
            self.target_size = None
        else:
            self.target_size = (
                self.config.image_width,
                self.config.image_height
            )

        self._page_meta_fields = None
        self._doc_meta_fields = None
        self.shard_num = 0
        self.shard_size = 0
        self.worker_hash = uuid.uuid4().hex
        self.shard_id = self.worker_hash + "_{:05d}"

        # unoserver management
        self.conversion_manager = ConversionManager(
            soffice_executable, config, logger_name=logger_name
        )

        # init output files
        self._init_output_files()

        self.logger.info(f"initialized.")
        self.logger.info(f"input_tars={self.input_tars}")

    def _init_output_files(self):
        fn = "page_meta_" + self.shard_id.format(self.shard_num) + ".jsonl"
        self._page_meta_file = open(
            file=Path(self.meta_dir, fn), mode="w"
        )

        fn = "doc_meta_" + self.shard_id.format(self.shard_num) + ".jsonl"
        self._doc_meta_file = open(
            file=Path(self.meta_dir, fn), mode="w"
        )

        fn = "failed_" + self.shard_id.format(self.shard_num) + ".jsonl"
        self._failed_file = open(
            file=Path(self.failed_dir, fn), mode="w"
        )

        self._annotations_tarfile = self._create_annotations_tarfile(
            tar_fn="docs_" + self.shard_id.format(self.shard_num) + ".tar.gz"
        )

        fn = "doc_text_" + self.shard_id.format(self.shard_num) + ".jsonl"
        self._doc_text_data_file = open(
            file=Path(self.text_dir, fn), mode="w"
        )

        fn = "page_text_" + self.shard_id.format(self.shard_num) + ".jsonl"
        self._page_text_data_file = open(
            file=Path(self.text_dir, fn), mode="w"
        )

    def run(self):
        for input_tar in self.input_tars:
            # self._handle_tar(input_tar=input_tar)
            try:
                self._handle_tar(input_tar=input_tar)
            except Exception as e:
                self.logger.error(f"(self.run) {e.__class__.__name__}: {e}")

        self.logger.info(f"{self.annotator_id} finished. Shutting down.")
        self.shutdown()

    def _handle_tar(self, input_tar: Path):
        src_shard_id = input_tar.name
        counts = 0

        self.logger.info(f"{self.annotator_id} start processing {input_tar}.")

        with tarfile.open(name=input_tar, mode='r:gz') as tar:

            for member in tar.getmembers():

                counts += 1
                doc_fn = member.name
                url_hash = Path(doc_fn).stem[4:]

                if counts > self.max_docs > 0:
                    raise StopIteration(f"Reached max_docs={counts - 1}")

                if not doc_fn.endswith((".docx", ".doc")):
                    self.logger.info(f"({self.annotator_id}) "
                                     f"skipping {member.name}...")
                    continue

                # load doc bytes
                try:
                    doc_bytes = self._load_doc_bytes(member=member, tar=tar)
                except Exception as e:
                    self._record_fail(
                        url_hash=url_hash,
                        doc_fn=doc_fn,
                        exception=e.__class__.__name__,
                        msg=str(e),
                        sources_shard_id=src_shard_id
                    )
                    msg = f"(self._load_doc_bytes) {e.__class__.__name__}: {e}"
                    self.output_queue.put({
                        "annotator_id": self.annotator_id,
                        "status": STATUS_FAIL,
                        "err_msg": msg,
                        "doc_fn": doc_fn,
                        "num_pages": 0
                    })
                    continue

                # annotate doc
                temp_dir = tempfile.mkdtemp(dir=fs_settings.TMP_DIR)
                try:
                    annotated_doc: AnnotatedDocument = self.annotate0(
                        Path(doc_fn), doc_bytes, temp_dir=Path(temp_dir),
                        sources_shard_id=input_tar.name, url_hash=url_hash
                    )
                except Exception as e:
                    msg = f"(self.annotate0) {e.__class__.__name__}: {e}"
                    self._record_fail(
                        url_hash=url_hash,
                        doc_fn=doc_fn,
                        exception=e.__class__.__name__,
                        msg=str(e),
                        sources_shard_id=src_shard_id
                    )
                    self.output_queue.put({
                        "annotator_id": self.annotator_id,
                        "status": STATUS_FAIL,
                        "err_msg": msg,
                        "doc_fn": doc_fn,
                        "num_pages": 0
                    })

                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.logger.warning(
                            f"WARNING: could not remove temp dir "
                            f"{temp_dir}: {e.__class__.__name__}: {e}"
                        )
                    continue

                # write instance to disk
                try:
                    self._save_instance(annotated_doc, temp_dir=Path(temp_dir))
                except Exception as e:
                    msg = f"(self._save_instance) {e.__class__.__name__}: {e}"
                    self._record_fail(
                        url_hash=url_hash,
                        doc_fn=doc_fn,
                        exception=e.__class__.__name__,
                        msg=str(e),
                        sources_shard_id=src_shard_id
                    )
                    self.output_queue.put({
                        "annotator_id": self.annotator_id,
                        "status": STATUS_FAIL,
                        "err_msg": msg,
                        "doc_fn": doc_fn,
                        "num_pages": 0
                    })

                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.logger.warning(
                            f"WARNING: could not remove temp dir "
                            f"{temp_dir}: {e.__class__.__name__}: {e}"
                        )
                    continue

                # cleanup
                try:
                    self._cleanup_annotate(temp_dir=temp_dir)
                except Exception as e:
                    msg = f"(self._cleanup_annotate)" \
                          f"{e.__class__.__name__}: {e}"
                    self._record_fail(
                        url_hash=url_hash,
                        doc_fn=doc_fn,
                        exception=e.__class__.__name__,
                        msg=str(e),
                        sources_shard_id=src_shard_id
                    )
                    self.output_queue.put({
                        "annotator_id": self.annotator_id,
                        "status": STATUS_FAIL,
                        "err_msg": msg,
                        "doc_fn": doc_fn,
                        "num_pages": 0
                    })

                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        self.logger.warning(
                            f"WARNING: could not remove temp dir "
                            f"{temp_dir}: {e.__class__.__name__}: {e}"
                        )
                    continue

                self.output_queue.put({
                    "annotator_id": self.annotator_id,
                    "status": STATUS_SUCCESS,
                    "err_msg": "",
                    "doc_fn": doc_fn,
                    "num_pages": annotated_doc.metadata.num_pages
                })

    def _load_doc_bytes(self, member: tarfile.TarInfo, tar: tarfile.TarFile):

        doc_fn = member.name

        # check if uncompressed size is too large
        if member.size > self.config.max_doc_bytes:
            raise CompressedFileSizeExceededException(
                f"{doc_fn} is too large ({member.size} > "
                f"{self.config.max_doc_bytes})"
            )

        fobj = tar.extractfile(member)
        fobj.seek(0)
        doc_bytes = fobj.read()

        # check if file is a valid zip file
        uncompressed_size = get_uncompressed_file_size(
            doc_bytes=doc_bytes, doc_fn=pathlib.Path(doc_fn)
        )

        if uncompressed_size > self.config.max_doc_bytes:
            raise UncompressedFileSizeExceededException(
                f"{doc_fn} is too large "
                f"({uncompressed_size} > "
                f"{self.config.max_doc_bytes})"
            )

        return doc_bytes

    def _save_instance(
            self, annotated_doc: AnnotatedDocument, temp_dir: pathlib.Path
    ):
        # 1) save multimodal (page level) data
        for page in annotated_doc.pages:
            with open(temp_dir / f"words_{page.page_id}.json", "w") as f:
                json.dump(page.words_to_json(), f)
            with open(temp_dir / f"entities_{page.page_id}.json", "w") as f:
                json.dump(page.entities_to_json(), f)
            with open(temp_dir / f"text_{page.page_id}.json", "w") as f:
                json.dump(page.text_to_json(), f)

        # package into tar
        self._write_to_annotations_tar(temp_dir=temp_dir)

        # 2.1) save text data page level
        for page in annotated_doc.pages:
            self._write_page_text_data(page_text=page.text_to_json())

        # 2.1) save text data document level
        self._write_doc_text_data(doc_text=annotated_doc.text_to_json())

        # 3.1) save metadata page level
        for page in annotated_doc.pages:
            self._write_page_meta(page_meta=page.meta_to_json())

        # 3.2) save metadata doc level
        self._write_doc_meta(doc_meta=annotated_doc.meta_to_json())

    def _cleanup_annotate(self, temp_dir: pathlib.Path):
        self.flush()

        if self.shard_size > self.config.max_bytes_in_shard:
            self._reset_shards()

        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            self.logger.warning(f"WARNING: could not remove temp dir "
                                f"{temp_dir}: {e.__class__.__name__}: {e}")

        # collect garbage
        gc.collect()

    def annotate0(
            self, doc_fn: Path, doc_bytes: bytes, temp_dir: Path,
            sources_shard_id: str, url_hash: str
    ) -> AnnotatedDocument:
        r"""Annotates a word document with entities and extracts text. The
        functions also generates the images of the pages of the document and
        stores them in the target directory.

        @param doc_fn: filename of the document (extracted from tar archive)
        @param doc_bytes: bytes of the document
        @param temp_dir: path to the temp directory
        @param sources_shard_id: id of the shard of the sources tar archive
        @param url_hash: hash of the url of the document

        @return: annotated document

        @raises:
            - ConversionFailedException: if conversion of doc to docx or docx
                to pdf fails
            - InconsistentPageCountError: if the number of pages extracted from
                the pdf and the number of pages extracted from the word
                document do not match
            - InconsistentAspectRatiosError: if the aspect ratios of the pages
                extracted from the pdf and the word document do not match
            - Exception: if any other exception occurs
        """
        # doc id is the name of the doc
        doc_id = doc_fn.stem

        # build filepaths
        doc_fp = temp_dir / f"{doc_id}.docx"
        doc_fp_colorized = temp_dir / f"colorized_{doc_id}.docx"

        if doc_fn.suffix == ".doc":
            with open(temp_dir / doc_fn, "wb") as f:
                f.write(doc_bytes)
            doc_fp = self.conversion_manager.doc_to_docx(temp_dir / doc_fn)
            doc_bytes = doc_fp.read_bytes()

            uncompressed_size = get_uncompressed_file_size(
                doc_bytes=doc_bytes, doc_fn=doc_fn
            )

            if uncompressed_size > self.config.max_doc_bytes:
                raise UncompressedFileSizeExceededException(
                    f"{doc_fn} is too large "
                    f"({uncompressed_size} > "
                    f"{self.config.max_doc_bytes})"
                )

        # check if docx contains image decompression bombs; if image size
        # exceeds threshold, an ImageDecompressionBombError is raised
        detect_image_decompression_bombs(doc_bytes=doc_bytes, doc_fn=doc_fn)

        with BytesIO(initial_bytes=doc_bytes) as file:
            doc: Document = docx.Document(file)

        # try to get page count from word document
        try:
            page_count = get_page_count(doc)
        except UnknownPageCountException:
            page_count = None

        if page_count is not None and page_count > self.config.max_doc_pages:
            raise PageCountExceededException(
                f"Page count of document {doc_id} exceeds maximum "
                f"page count ({page_count} > {self.config.max_doc_pages})."
            )

        # convert to pdf
        doc.save(doc_fp)
        pdf_fp = self.conversion_manager.docx_to_pdf(doc_fp=doc_fp)

        # get page count from pdf
        page_count = get_page_count_from_pdf(pdf_fp)

        # if page count is still None, raise exception
        if page_count is None:
            raise UnknownPageCountException(
                f"Unknown page count for {doc_id}. Skipping."
            )

        if page_count > self.config.max_doc_pages:
            raise PageCountExceededException(
                f"Page count of document {doc_id} exceeds maximum "
                f"page count ({page_count} > {self.config.max_doc_pages})."
            )

        # preprocess word document
        # - remove existing shading (e.g. highlighted text)
        doc = sanitize_highlighting(word_doc=doc)

        # extract text from docx
        text = extract_text_from_docx(doc=doc)
        doc_text: DocumentText = DocumentText(text=text)

        if doc_text.num_chars < self.config.min_text_chars:
            raise TextTooShortException(
                f"char count of document {doc_id} too short"
                f"({doc_text.num_chars} < {self.config.min_text_chars})"
            )

        # handle the colorizations (need to pass element_tracker to this)
        colorization_handler = ColorizationHandler()

        # colorize the document
        doc = colorize_word_doc(
            doc, colorization_handler, temp_dir=temp_dir, config=self.config
        )

        # convert to colorized pdf
        doc.save(doc_fp_colorized)
        pdf_fp_col = self.conversion_manager.docx_to_pdf(doc_fp_colorized)

        # generate page images of original document
        page_images_paths: Dict[str, str]
        page_dims_renderings: Dict[str, Tuple[int, int]]
        (
            page_images_paths, page_dims_renderings
        ) = extract_page_images_and_dimensions_from_pdf(
            doc_id=doc_id, pdf_fp=pdf_fp, target_dir=temp_dir,
            fmt=self.config.image_format,
            size=self.target_size,
            dpi=self.config.image_dpi
        )

        # extract text from document using pdfplumber
        pages_words: Dict[str, List[Word]]
        page_dims_pdf_parser: Dict[str, Tuple[int, int]]
        (
            pages_words, page_dims_pdf_parser
        ) = extract_text_pdf_plumber(
            pdf_fp=pdf_fp, doc_id=doc_id
        )

        # detect languages on pages
        pages_langs: Dict[str, Dict[str, float]] = \
            lang_detect.inference.predict_lang_per_page(
                pages_words=pages_words, k=self.config.top_k_languages, lm=None
            )

        # detect entities on pages
        pages_entities: Dict[str, Dict[int, List[Entity]]]
        pages_entities = detect_entities_in_document(
            doc_id=doc_id, temp_pdf_fp=pdf_fp_col,
            colorization_handler=colorization_handler, debug_dir=None,
            word_doc_fp=None,
            dpi=self.config.image_dpi,
            size=(self.config.image_width, self.config.image_height)
        )

        # make sure page counts are consistent
        sanity_checks.page_counts_consistency(
            set(pages_entities.keys()),
            set(pages_words.keys())
        )

        # make sure aspect ratios are consistent
        sanity_checks.pages_aspect_ratios(
            page_dims_pdf_parser,
            page_dims_renderings
        )

        # postprocess text bounding boxes
        pages_words = postprocess_words(
            pages_dims_img=page_dims_renderings,
            pages_dims_pdf=page_dims_pdf_parser,
            pages_words=pages_words
        )

        # postprocess entity bounding boxes
        # ! important: this has to be done *after* adjusting the text bounding
        # ! boxes because these are computed based on different page
        # ! dimensions: in the pdfplumber case, the page dimensions are
        # ! extracted from the pdf itself, whereas in the case of the images,
        # ! the page dimensions are extracted from the rendered images)
        pages_entities = postprocess_entities(
            pages_dims_img=page_dims_renderings,
            pages_entities=pages_entities,
        )

        # compile table cells into rows and columns
        pages_entities = postprocess_tables(
            pages_entities=pages_entities, doc_id=doc_id
        )

        # assign each word to an entity
        pages_words: Dict[str, List[Word]] = assign_entities_to_words(
            pages_entities=pages_entities,
            pages_words=pages_words,
            threshold=self.config.word_2_entity_overlap_threshold
        )

        # filter out entities with no words (except for tables related
        # entities)
        pages_entities = postprocess_entities_content_based(
            pages_entities=pages_entities,
            pages_words=pages_words
        )

        # predict languages on document level
        doc_langs: Dict[str, float] = lang_detect.inference.predict_lang(
            text=doc_text.text, k=self.config.top_k_languages, lm=None
        )

        # delete all intermediate files
        pdf_fp_col.unlink()
        pdf_fp.unlink()

        # build page annotations list
        annotated_pages: List[AnnotatedPage] = self._build_page_annotations(
            doc_id=doc_id, doc_fn=str(doc_fn),
            sources_shard_id=sources_shard_id, url_hash=url_hash,
            page_dimensions=page_dims_renderings, pages_words=pages_words,
            pages_entities=pages_entities, pages_langs=pages_langs
        )

        # build document annotations
        annotated_doc: AnnotatedDocument = self._build_document_annotations(
            doc=doc, doc_id=doc_id, doc_fn=str(doc_fn),
            sources_shard_id=sources_shard_id, url_hash=url_hash,
            annotated_pages=annotated_pages, doc_text=doc_text,
            doc_langs=doc_langs, colorization_handler=colorization_handler
        )

        del doc

        return annotated_doc

    def _build_document_annotations(
            self, doc: Document, doc_id: str, doc_fn: str,
            sources_shard_id: str, url_hash: str,
            annotated_pages: List[AnnotatedPage], doc_text: DocumentText,
            doc_langs: Dict[str, float],
            colorization_handler: ColorizationHandler
    ) -> AnnotatedDocument:

        # collect metadata from oxml
        oxml_meta = get_oxml_metadata(doc)

        # collect basic metadata
        doc_meta = DocMetadataRecordDB()

        doc_meta.url_hash = url_hash
        doc_meta.crawl_id = self.crawl_id
        doc_meta.sources_shard_id = sources_shard_id
        doc_meta.annotated_shard_id = self.shard_id.format(self.shard_num)
        doc_meta.num_pages = len(annotated_pages)
        doc_meta.sources_filename = doc_fn

        # will be added via join
        doc_meta.filename = None
        doc_meta.url = None

        # text metrics
        doc_meta.word_count = doc_text.num_words
        doc_meta.char_count = doc_text.num_chars
        doc_meta.alph_chars_count = doc_text.num_alph_chars
        doc_meta.numeric_chars_count = doc_text.num_numeric_chars
        doc_meta.alphnum_chars_count = doc_text.num_alphnum_chars
        doc_meta.alnum_prop = doc_text.alnum_prop
        doc_meta.alph_to_num_ratio = doc_text.alph_to_num_ratio
        doc_meta.languages_fasttext = doc_langs
        doc_meta.languages_autocorrect = oxml_meta.languages_autocorrect
        doc_meta.top_lang = max(doc_langs, key=doc_langs.get)
        doc_meta.top_lang_score = doc_langs[doc_meta.top_lang]

        # get entity counts
        entity_counts = {}
        for entity_name in settings.entities.ALL_ENTITY_NAMES:
            count = sum(
                getattr(page.metadata, "num_" + entity_name)
                for page in annotated_pages
            )
            setattr(doc_meta, "num_" + entity_name, count)
            entity_id = settings.entities.ENTITY_NAME_TO_ID[entity_name]
            entity_counts[entity_id] = count

        # get quality metrics
        quality_score, builtin_props = calc_annotation_quality_score(
            colorization_decisions=colorization_handler.colorization_decisions,
            entity_counts=entity_counts
        )

        annotation_sources = \
            colorization_handler.aggregate_colorization_decisions()

        doc_meta.annotation_quality_score = quality_score
        doc_meta.annotation_sources = annotation_sources
        doc_meta.builtin_proportion_per_entity = builtin_props

        # oxml metadata
        doc_meta.core_category = oxml_meta.core_category
        doc_meta.core_comments = oxml_meta.core_comments
        doc_meta.core_content_status = oxml_meta.core_content_status
        doc_meta.core_created = oxml_meta.core_created
        doc_meta.core_identifier = oxml_meta.core_identifier
        doc_meta.core_keywords = oxml_meta.core_keywords
        doc_meta.core_last_printed = oxml_meta.core_last_printed
        doc_meta.core_modified = oxml_meta.core_modified
        doc_meta.core_subject = oxml_meta.core_subject
        doc_meta.core_title = oxml_meta.core_title
        doc_meta.core_version = oxml_meta.core_version

        annotated_document = AnnotatedDocument(
            doc_id=doc_id,
            text=doc_text,
            pages=annotated_pages,
            metadata=doc_meta
        )

        return annotated_document

    def _build_page_annotations(
            self, doc_id: str, doc_fn: str, sources_shard_id: str,
            url_hash: str, page_dimensions: Dict[str, Tuple[int, int]],
            pages_words: Dict[str, List[Word]],
            pages_entities: Dict[str, Dict[int, List[Entity]]],
            pages_langs: Dict[str, Dict[str, float]]
    ) -> List[AnnotatedPage]:
        page_annotations: List[AnnotatedPage] = []

        for page_id, entities in pages_entities.items():
            words = pages_words[page_id]
            langs = pages_langs[page_id]
            width, height = page_dimensions[page_id]

            # collect metadata
            page_meta = PageMetadataRecordDB()
            page_meta.page_id = page_id
            page_meta.url = None
            page_meta.url_hash = url_hash
            page_meta.crawl_id = self.crawl_id
            page_meta.sources_shard_id = sources_shard_id
            page_meta.annotated_shard_id = self.shard_id.format(self.shard_num)
            page_meta.filename = doc_fn
            page_meta.pdf_word_count = len(words)
            page_meta.languages_fasttext = langs
            page_meta.top_lang = max(langs, key=langs.get)
            page_meta.top_lang_score = langs[page_meta.top_lang]
            page_meta.page_height = height
            page_meta.page_width = width
            page_meta.page_number = get_page_num_from_page_id(page_id)

            # get entity counts
            for entity_name in settings.entities.ALL_ENTITY_NAMES:
                entity_id = settings.entities.ENTITY_NAME_TO_ID[entity_name]
                count = len(entities.get(entity_id) or [])
                setattr(page_meta, f'num_{entity_name}', count)

            # get page text
            page_text = DocumentText(text=" ".join(w.text for w in words))

            # initialize page annotation object
            page_annotation = AnnotatedPage(
                doc_id=doc_id,
                page_id=page_id,
                page_text=page_text,
                words=words,
                entities=entities,
                metadata=page_meta
            )

            page_annotations.append(page_annotation)

        return page_annotations

    def flush(self):
        self._doc_meta_file.flush()
        self._page_meta_file.flush()
        self._failed_file.flush()
        self._doc_text_data_file.flush()
        self._page_text_data_file.flush()

    def shutdown(self):
        # close files
        self._doc_meta_file.close()
        self._page_meta_file.close()
        self._annotations_tarfile.close()
        self._doc_text_data_file.close()
        self._page_text_data_file.close()
        self._failed_file.close()

        # shutdown soffice
        self.conversion_manager.shutdown_soffice()

    def _reset_shards(self):
        # close tarfile
        self._annotations_tarfile.close()
        self.shard_size = 0

        # close metadata
        self._doc_meta_file.close()
        self._page_meta_file.close()

        # close text data
        self._doc_text_data_file.close()
        self._page_text_data_file.close()

        self.shard_num += 1

        # create new output files
        self._init_output_files()

    def _record_fail(self, url_hash, doc_fn, exception, msg, sources_shard_id):
        self._failed_file.write(json.dumps({
            "annotator_id": self.annotator_id,
            "url_hash": url_hash,
            "doc_fn": doc_fn,
            "exception": exception,
            "msg": msg,
            "sources_shard_id": sources_shard_id,
        }) + "\n")
        self._failed_file.flush()

    def _write_to_annotations_tar(self, temp_dir: pathlib.Path):
        # get page ids
        page_ids = set(fp.stem for fp in temp_dir.glob("*.jpg"))

        for page_id in page_ids:

            data_files = [
                temp_dir / f"{page_id}.jpg",
                temp_dir / f"text_{page_id}.json",
                temp_dir / f"words_{page_id}.json",
                temp_dir / f"entities_{page_id}.json"
            ]

            if any(not fp.is_file() for fp in data_files):
                raise Exception(f"Missing file for {page_id}")

            # get size of files
            for fp in data_files:
                self.shard_size += fp.stat().st_size

            # write to tar
            for fp in data_files:
                self._annotations_tarfile.add(name=fp, arcname=fp.name)

    def _write_doc_text_data(self, doc_text: Dict[str, Any]):
        self._doc_text_data_file.write(json.dumps(doc_text) + "\n")

    def _write_page_text_data(self, page_text: Dict[str, Any]):
        self._page_text_data_file.write(json.dumps(page_text) + "\n")

    def _write_doc_meta(self, doc_meta: Dict[str, Any]):
        self._doc_meta_file.write(json.dumps(doc_meta) + "\n")

    def _write_page_meta(self, page_meta: Dict[str, Any]):
        self._page_meta_file.write(json.dumps(page_meta) + "\n")

    def _create_annotations_tarfile(self, tar_fn) -> tarfile.TarFile:
        return tarfile.TarFile.open(
            name=Path(self.annotations_dir, tar_fn), mode="w:gz"
        )
