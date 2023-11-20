import cv2
import numpy as np
import os
from typing import List, Dict, Tuple, Union
import pathlib

from src.annotation.annotation_objects import Entity
from src.annotation.colorization import ColorizationHandler
from src.annotation.entity_detection import EntityDetector
from src.annotation.utils.identifiers import get_page_id
from src.annotation.utils.pdf_utils import pdf_to_page_images_iterator


def detect_entities_in_document(
        doc_id: str,
        temp_pdf_fp: Union[str, pathlib.Path],
        colorization_handler: ColorizationHandler,
        debug_dir: Union[str, pathlib.Path] = None,
        word_doc_fp: Union[str, pathlib.Path] = None,
        dpi: int = 100,
        size: Tuple[Union[int, None], Union[int, None]] = (None, None)
) -> Dict[str, Dict[int, List[Entity]]]:
    r"""Detect entities in a document.

    @param doc_id: id of the document
    @param temp_pdf_fp: path to pdf file
    @param colorization_handler: colorization handler containts the colors used
        for colorization
    @param debug_dir: path to save colorized image pages for debugging
    @param word_doc_fp: path to word document; this is only used for debugging
    @param dpi: resolution of the output image(s)
    @param size: size of the output image(s), uses the Pillow (width, height)
        standard. If one of width or height is set to None, the image
        aspect ratio is preserved.

    @return: Dict with page number as key and as value a dictionary with
        entity_category_id as key and list of entity objects for detected
        entities as value
    """
    pages_entities = {}
    page_number = 1  # page number starts at 1

    # extract pages from pdf as images
    # ! important: output format needs to use lossless compression when
    # ! converting the colorized pdf to images. Otherwise, the entity
    # ! detection will be inaccurate. ALWAYS USE fmt="png"!
    for pages_block in pdf_to_page_images_iterator(
            pdf_fp=temp_pdf_fp,
            fmt="png",
            size=size,
            dpi=dpi,
            output_folder=None
    ):
        for page in pages_block:
            # convert to cv2 format with HSV color space
            page = np.array(page).astype(np.uint8)
            page_cv2 = cv2.cvtColor(page, cv2.COLOR_RGB2HSV)

            if debug_dir is not None:
                fn_root = os.path.splitext(os.path.split(word_doc_fp)[-1])[0]
                debug_save_as = os.path.join(
                    debug_dir, f"colorized_{fn_root}_p{page_number}.png"
                )
                cv2.imwrite(
                    debug_save_as, cv2.cvtColor(page, cv2.COLOR_RGB2BGR)
                )

            # detect entities in page: this function returns a dictionary with
            # entity_category as key and list of bounding boxes for detected
            # entities as value
            page_id = get_page_id(doc_id, page_number)
            entities = _detect_entities_on_page(
                doc_id=doc_id,
                page_id=page_id,
                page_num=page_number,
                page_image=page_cv2,
                colorization_handler=colorization_handler
            )
            pages_entities[page_id] = entities
            page_number += 1

    return pages_entities


def _detect_entities_on_page(
        doc_id: str,
        page_id: str,
        page_num: int,
        page_image: np.ndarray,
        colorization_handler: ColorizationHandler
) -> Dict[int, List[Entity]]:
    r"""Detect entities in a page.

    @param page_image: page to detect entities in; ! this needs to be a cv2
        image in HSV color space
    @param colorization_handler: colorization handler containts the colors used
        for colorization

    @return: Dictionary with entity_category_id as key and list of entity
        objects for detected entities as value
    """
    entity_detector = EntityDetector(
        doc_id=doc_id, page_id=page_id, page_num=page_num,
        image_numpy=page_image, colorization_handler=colorization_handler
    )
    return entity_detector.detect_entities()
