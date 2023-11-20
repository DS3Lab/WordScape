# need to handle:
# filtering of WordScape examples to be included in dataset
# balance of WordScape examples to be included in dataset

# save imgs, bboxes (OF WORDS!), bboxes (OF ENTITIES!) in such a way that
# these can later be loaded by AutoProcessor.from_pretrained("microsoft/layoutlmv3-base", apply_ocr=False)
# e.g should be saved interpretable as a huggingface hub dataset.
# see https://colab.research.google.com/github/NielsRogge/Transformers-Tutorials/blob/master/LayoutLMv3/Fine_tune_LayoutLMv3_on_FUNSD_(HuggingFace_Trainer).ipynb#scrollTo=YHkC26CQelBH
# (this is a LayoutLMv3Processor), also need token labels (correspond to entity containing word token)

# TODO should also be readable by a custom processor, that deals with the additional embedding for entitty bbox case,
# as opposed to the additional loss for entity bbox detection / word to entity matching only case

# TODO augraphy

from io import BytesIO
import json
from pathlib import Path
import shutil
from typing import Dict, List, Tuple, Union
import settings
from dataclasses import dataclass

# from augraphy import *
import cv2
import tarfile
import json
import multiprocessing as mp
import random
from src.extensions.pretrain.layoutlmv3.data_prep.wordscape_layoutlmv3_config_handler import (
    WSLayoutLMSettings,
)
from src.extensions.pretrain.layoutlmv3.data_prep.wordscape_layoutlmv3_datasetbuilder import (
    WSLayoutLMDataPoint,
)
import numpy as np
from PIL import Image
from datasets import Dataset, ClassLabel, Sequence


class WSLayoutLMFormatter(mp.Process):
    def __init__(
        self,
        data_settings: WSLayoutLMSettings,
        experiment_name: str,
        out_path_optional: str,
        out_q: mp.Queue = None,
        is_final: bool = False,
        accept_existing=True,
    ):
        r"""
        A class which formats and creates LayoutLM datasets from the WordScape dataset.
        Also tracks dataset creation (TODO versioning.)
        """
        super(WSLayoutLMFormatter, self).__init__()

        self.data_settings = data_settings
        self.experiment_name = experiment_name
        self.root_out = settings.filesystem.EXPERIMENT_DIR
        if out_path_optional:
            self.root_out = Path(out_path_optional)
        self.out_q = out_q
        self.is_final = is_final
        self.accept_existing = accept_existing

    def layoutlm_format_num(self, num: float) -> int:
        r"""Format a float as required by LayoutLM"""
        return int(num)

    def build_labels(self, layoutlm_settings: WSLayoutLMSettings):
        r"""
        A function to build LayoutLM-format labels from LayoutLM settings.
        Returns label names, and a mapping of each WordScape element type ID to a class.
        See huggingface Sequence with feature=ClassLabel
        """

        # track elem codes that should preserve vanilla behavior
        master_elem_codes = settings.entities.LABEL_NUMS
        # filter out those we wish to drop
        master_elem_codes = list(
            filter(lambda x: not x in layoutlm_settings.elem_drops, master_elem_codes)
        )
        # filter out those who will be merged
        if layoutlm_settings.elem_mergings:
            master_elem_codes = list(
                filter(
                    lambda x: not x
                    in layoutlm_settings.elem_mergings["mapping"].keys(),
                    master_elem_codes,
                )
            )

        # assign labels while considering element mergings
        elem_labels = []
        for elem_code in master_elem_codes:
            if layoutlm_settings.elem_mergings:
                if elem_code in layoutlm_settings.elem_mergings["masters"].keys():
                    elem_labels.append(
                        layoutlm_settings.elem_mergings["masters"][elem_code]
                    )
                else:
                    elem_labels.append(settings.entities.ENTITY_ID_TO_NAME[elem_code])
            else:
                elem_labels.append(settings.entities.ENTITY_ID_TO_NAME[elem_code])

        # create mapping from direct WordScape entity IDs to classes
        # this mapping will also be missing any dropped entity IDs
        entity_id_to_class = {}
        # needed for tracking while we build final map
        class_count = 0
        master_entity_ids_to_class = {}

        # first, map vanilla and master entity types to classes
        for elem_code in master_elem_codes:
            entity_id_to_class[elem_code] = class_count
            if layoutlm_settings.elem_mergings:
                if elem_code in layoutlm_settings.elem_mergings["masters"].keys():
                    master_entity_ids_to_class[elem_code] = class_count
            class_count += 1

        # now, map any merged entity types to the class of their master
        # TODO ensure that no dropped entity types can also be merged --> avoid potential experiment mistakes
        if layoutlm_settings.elem_mergings:
            for elem_code in layoutlm_settings.elem_mergings["mapping"].keys():
                entity_id_to_class[elem_code] = master_entity_ids_to_class[
                    layoutlm_settings.elem_mergings["mapping"][elem_code]
                ]

        return elem_labels, entity_id_to_class

    def create_dataset(
        self, layoutlm_settings: WSLayoutLMSettings, out_q: mp.Queue
    ) -> int:
        r"""
        A function to create a training or validation dataset from LayoutLM settings.
        Enqueues number of accepted images.
        """

        # TODO: other data augmentations (blurring, rotation, etc.)
        # TODO: consideration of autocorrect for lang filter, or just use fasttext?

        # TODO: elem weights (dont care about text blocks)?
        # TODO: filtering out docs with too many text blocks? min. number of elems?

        # TODO: do we need to check if another process has already created the image in question?
        # currently we just overwrite, which should be fine

        # augraphy defaults for now
        # TODO
        # aug_pipeline = default_augraphy_pipeline()

        ############################## set up paths and vars ##############################
        out_path = self.root_out / self.experiment_name
        out_path_images = out_path / "images"
        # out_path_labels = out_path / "labels"
        out_path_images.mkdir(parents=True, exist_ok=True)
        # out_path_labels.mkdir(parents=True, exist_ok=True)
        # tracking of accepted images
        accepted_img = 0

        ############################## build labels ##############################
        _, entity_id_to_class = self.build_labels(layoutlm_settings)

        ############################## process metadata JSONs ##############################
        # TODO: expect unzipped files for now; tarfile library way too slow
        # file_list = sorted(filter(lambda x: str(x).endswith('.json') and ('/entities' in x), ((layoutlm_settings.raw_path / settings.filesystem.WS_MULTIMODAL).iterdir())))
        # file_list = (layoutlm_settings.raw_path / settings.filesystem.WS_MULTIMODAL).iterdir()
        # file_list = list(filter(lambda x: str(x).endswith('.json') and ('/entities' in str(x)), file_list))
        # file_list = sorted(file_list)
        print("creating huggingface dataset")

        tar_list = list(
            filter(
                lambda x: str(x).endswith(".tar"),
                (
                    layoutlm_settings.raw_path / settings.filesystem.WS_MULTIMODAL
                ).iterdir(),
            )
        )
        tar_list = random.sample(tar_list, len(tar_list))
        for tar_name in tar_list:
            # get the relevant jsonl metadatas, to check for things like quality score
            meta_fname = "doc_meta_" + (tar_name.stem.replace("docs_", "")) + ".jsonl"
            with open(
                layoutlm_settings.raw_path / settings.filesystem.WS_META / meta_fname
            ) as meta_open:
                json_list = list(meta_open)

            doc_metas = {}
            for json_str in json_list:
                res = json.loads(json_str)
                doc_metas[res["url_hash"]] = res

            with tarfile.open(tar_name) as tar_open:
                file_list = []
                try:
                    file_list = sorted(
                        filter(
                            lambda x: str(x).endswith(".json")
                            and str(x).startswith("entities"),
                            tar_open.getnames(),
                        )
                    )
                except:
                    # this could be a bad tar archive --> just go to the next one
                    continue
                for file_name in file_list:
                    try:
                        file_stem = file_name.replace("entities_", "").replace(
                            ".json", ""
                        )

                        # ! one datapoint in the HF dataset
                        datapoint = {
                            "id": file_stem,
                            "tokens": [],
                            "word_bboxes": [],
                            "entity_bboxes": [],
                            "entity_labels": [],
                        }

                        # stop if we have created enough images
                        if (layoutlm_settings.max_img >= 0) and (
                            accepted_img >= layoutlm_settings.max_img
                        ):
                            # enqueue that we have got the needed number of images
                            # out_q.put(accepted_img)
                            return

                        # read the JSON metadata
                        with tar_open.extractfile(file_name) as fopen:
                            wordscape_meta = json.loads(fopen.read())
                        # read the words
                        with tar_open.extractfile(
                            file_name.replace("entities_doc_", "words_doc_")
                        ) as fopen:
                            wordscape_words = json.loads(fopen.read())
                        # fetch the document-level metadata that applies to this page
                        doc_meta = doc_metas[wordscape_meta["metadata"]["url_hash"]]

                        ############################## first check any filters ##############################
                        filters_passed = True
                        doc_quality = doc_meta["annotation_quality_score"]
                        if layoutlm_settings.quality_threshold > doc_quality:
                            filters_passed = False

                        # allowed langs
                        if len(layoutlm_settings.language_codes) > 0:
                            lang_test_passed = False
                            for allowed_lang in layoutlm_settings.language_codes:
                                if (
                                    wordscape_meta["metadata"]["top_lang"]
                                    == "__label__" + allowed_lang
                                ):
                                    if (
                                        layoutlm_settings.language_code_threshold > 0
                                    ) and (
                                        layoutlm_settings.language_code_threshold
                                        > wordscape_meta["metadata"]["top_lang_score"]
                                    ):
                                        lang_test_passed = False
                                    else:
                                        lang_test_passed = True
                                        break
                            if lang_test_passed == False:
                                filters_passed = False

                        # contains at least one element from elem_accepts (considering mergings!)
                        elem_accept_passed = False
                        for entity_type in wordscape_meta["entities"].keys():
                            type_merged = int(entity_type)
                            if (
                                int(entity_type)
                                in layoutlm_settings.elem_mergings["mapping"].keys()
                            ):
                                type_merged = layoutlm_settings.elem_mergings[
                                    "mapping"
                                ][int(entity_type)]

                            if type_merged in layoutlm_settings.elem_accepts:
                                # need to also check that there actually are listed elements
                                if len(wordscape_meta["entities"][entity_type]) > 0:
                                    elem_accept_passed = True
                                    break
                        if elem_accept_passed == False:
                            filters_passed = False

                        # filters passed
                        if not filters_passed:
                            continue

                        ############################## transform JSON bounding boxes ##############################

                        # len_tracker = 0
                        for entity_type in wordscape_meta["entities"]:
                            # len_tracker += len(wordscape_meta["entities"][str(entity_type)])
                            # get the class for this entity type, if any
                            if not int(entity_type) in entity_id_to_class.keys():
                                continue
                            entity_class = entity_id_to_class[int(entity_type)]

                            # process each indidivually occurring entity bounding box
                            for entity_occ in wordscape_meta["entities"][
                                str(entity_type)
                            ]:
                                x_topleft = entity_occ["bbox"]["x"]
                                y_topleft = entity_occ["bbox"]["y"]
                                w = entity_occ["bbox"]["width"]
                                h = entity_occ["bbox"]["height"]
                                x_bottomright = x_topleft + w
                                y_bottomright = y_topleft + h

                                entity_bbox = [
                                    self.layoutlm_format_num(x_topleft),
                                    self.layoutlm_format_num(y_topleft),
                                    self.layoutlm_format_num(x_bottomright),
                                    self.layoutlm_format_num(y_bottomright),
                                ]
                                datapoint["entity_bboxes"].append(entity_bbox)
                                datapoint["entity_labels"].append(entity_class)

                        # now go through all word bboxes
                        for word_data in wordscape_words["words"]:
                            text = word_data["text"]
                            # process bbox
                            x_topleft = word_data["bbox"]["x"]
                            y_topleft = word_data["bbox"]["y"]
                            w = word_data["bbox"]["width"]
                            h = word_data["bbox"]["height"]
                            x_bottomright = x_topleft + w
                            y_bottomright = y_topleft + h
                            word_bbox = [
                                self.layoutlm_format_num(x_topleft),
                                self.layoutlm_format_num(y_topleft),
                                self.layoutlm_format_num(x_bottomright),
                                self.layoutlm_format_num(y_bottomright),
                            ]
                            datapoint["tokens"].append(text)
                            datapoint["word_bboxes"].append(word_bbox)
                        # TODO consider entity categories?

                        ############################## process page image ##############################
                        img_file_name = file_stem + ".jpg"
                        with tar_open.extractfile(img_file_name) as img_file_open:
                            # img_np = np.asarray(bytearray(img_file_open.read()))
                            img_pil = Image.open(BytesIO(img_file_open.read()))
                            # print(img_np)
                            img_pil.save(out_path_images / img_file_name)
                            datapoint["image"] = {
                                "path": str(out_path_images / img_file_name),
                                "bytes": img_file_open.read(),
                            }

                        # TODO shared augraphy handler

                        # ! add datapoint to dataset
                        datapoint_formatted = WSLayoutLMDataPoint(
                            id=datapoint["id"],
                            tokens=datapoint["tokens"],
                            word_bboxes=datapoint["word_bboxes"],
                            entity_bboxes=datapoint["entity_bboxes"],
                            entity_labels=datapoint["entity_labels"],
                            image=datapoint["image"],
                        )
                        # print(datapoint_formatted)
                        out_q.put(datapoint_formatted)

                        # check if label already exists --> may not need to overwrite
                        # TODO
                        already_exists = True
                        # already_exists = out_path_onelabel.exists()
                        if not already_exists:
                            ############################## process page image ##############################
                            # ! expectation for JSON to always possess corresponding .jpg
                            img_file_name = file_stem + ".jpg"
                            img_file_writepath = out_path_images / img_file_name
                            with tar_open.extractfile(img_file_name) as img_file_open:
                                if layoutlm_settings.scanify:
                                    # TODO just augraphy defaults for now
                                    # TODO we need to take augraphy transforms into account, and adjust bounding boxes accordingly!
                                    # TODO InvalidParameterError: The 'center_box' parameter of make_blobs must be an instance of 'tuple'. Got [0, 68] instead.
                                    img_f = cv2.imread(
                                        str(
                                            layoutlm_settings.raw_path
                                            / settings.filesystem.WS_MULTIMODAL
                                            / img_file_name
                                        )
                                    )
                                    # TODO shared augraphy handler
                                    # aug = aug_pipeline.augment(img_f)
                                    # aug_img = aug["output"]
                                    aug_img = img_f
                                    cv2.imwrite(
                                        str(out_path_images / img_file_name), aug_img
                                    )
                                else:
                                    with open(img_file_writepath, "wb") as img_write:
                                        img_write.write(img_file_open.read())

                        # check if we are allowed to increase accepted (min amount vs. required exact amount)
                        # if self.accept_existing or (not already_exists):
                        # TODO deal with accept_existing in HF dataset context
                        if True:
                            accepted_img += 1
                    except Exception as e:
                        print("Error occured!")
                        print(e)
                        continue

    def run(self):
        r"""
        Create dataset, depending on LayoutLM settings
        passed during init.

        Returns number of accepted images for training and validation datasets.
        """

        self.create_dataset(self.data_settings, self.out_q)
        # after finishing, put stop signal in queue
        self.out_q.put(None)
