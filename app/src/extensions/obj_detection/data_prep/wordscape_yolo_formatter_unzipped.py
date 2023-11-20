import json
from pathlib import Path
import shutil
from typing import Dict, List, Tuple
import settings
from dataclasses import dataclass
from augraphy import *
import cv2


@dataclass
class YOLOSettings:
    r"""
    A class describing the settings for creating a YOLO-format dataset.

    @param raw_path: Path to raw data to be formatted and / or filtered for the experiment.
    @param is_validation: Wether these settings apply to validation data. Determines the path the dataset is written to.
    @param max_img: max number of images to process from the raw_path (done in alphabetical ordering).
        This many files will be in the "labels" and "images" folder, respectively.
    @param elem_drops: WordScape elements (by ID) to drop from the dataset.
        Note that this overrides elem_mergings; e.g elements being dropped will not be merged into
        any element, even if included in elem_mergings.
    @param elem_mergings: Describes WordScape element IDs to be merged into one YOLO class, and how to label the new YOLO class.
        For example, to merge 9 heading levels into three levels:
        {
            "masters": {
                ENTITY_HEADING_1_ID: "heading_123",
                ENTITY_HEADING_4_ID: "heading_456",
                ENTITY_HEADING_7_ID: "heading_789",
            },
            "mapping": {
                ENTITY_HEADING_2_ID: ENTITY_HEADING_1_ID,
                ENTITY_HEADING_3_ID: ENTITY_HEADING_1_ID,
                ENTITY_HEADING_5_ID: ENTITY_HEADING_4_ID,
                ENTITY_HEADING_6_ID: ENTITY_HEADING_4_ID,
                ENTITY_HEADING_8_ID: ENTITY_HEADING_7_ID,
                ENTITY_HEADING_9_ID: ENTITY_HEADING_7_ID,
            },
        }
    @param scanify: Wether to create a scan-appearing document, using the augraphy library
    @param quality_threshold: Whether to filter documents based on WordScapes annotation quality score between 0 and 1.
        Only active if above 0.
    @param language_codes: Filter on only allowing documents containing these (fasstext / WordScape autocorrect metadata) language codes.
        Only considers most-likely lang (first in the list).
    @param language_code_threshold: Required threshold for language acceptance from fasstext (between 0 and 1). Only active if above 0.
    """

    raw_path: Path = (Path("/home/valde/GitHub/msc-thesis/data/raw/format_test_train"),)
    # out_path: Path = Path('/home/valde/GitHub/msc-thesis/data/experiments/format_test/train'),
    is_validation: bool = (False,)
    max_img: int = (75_000,)
    elem_drops: List[int] = ([],)
    # TODO typing info
    elem_mergings: Dict = (None,)
    scanify: bool = (False,)
    quality_threshold: float = (-1.0,)
    language_codes: List[str] = ([],)
    language_code_threshold: float = -1.0

    # for some reason the standard dataclass init does not play nice with elem_mergings
    def __init__(
        self,
        raw_path,
        is_validation,
        max_img,
        elem_drops,
        elem_mergings,
        scanify,
        quality_threshold,
        language_codes,
        language_code_threshold,
    ):
        self.raw_path = raw_path
        self.is_validation = is_validation
        self.max_img = max_img
        self.elem_drops = elem_drops
        self.elem_mergings = elem_mergings
        self.scanify = scanify
        self.quality_threshold = quality_threshold
        self.language_codes = language_codes
        self.language_code_threshold = language_code_threshold


class WSYOLOFormatter:
    def __init__(
        self,
        train_settings: YOLOSettings,
        val_settings: YOLOSettings,
        experiment_name: str,
    ):
        r"""
        A class which formats and creates YOLO datasets from the WordScape dataset.
        Also tracks dataset creation (TODO versioning.)
        """

        self.train_settings = train_settings
        self.val_settings = val_settings
        self.experiment_name = experiment_name

    def yolo_format_num(self, num: float) -> str:
        r"""Format a float as required by YOLO"""
        return str(num)[0:10]

    def build_labels(
        self, yolo_settings: YOLOSettings
    ) -> Tuple[List[str], dict[int, int]]:
        r"""
        A function to build YOLO-format labels from YOLO settings.
        Returns label names, and a mapping of each WordScape element type ID to a YOLO class.
        """

        # track elem codes that should preserve vanilla behavior
        master_elem_codes = settings.entities.LABEL_NUMS
        # filter out those we wish to drop
        master_elem_codes = list(
            filter(lambda x: not x in yolo_settings.elem_drops, master_elem_codes)
        )
        # filter out those who will be merged
        if yolo_settings.elem_mergings:
            master_elem_codes = list(
                filter(
                    lambda x: not x in yolo_settings.elem_mergings["mapping"].keys(),
                    master_elem_codes,
                )
            )

        # assign labels while considering element mergings
        elem_labels = []
        for elem_code in master_elem_codes:
            if yolo_settings.elem_mergings:
                if elem_code in yolo_settings.elem_mergings["masters"].keys():
                    elem_labels.append(
                        yolo_settings.elem_mergings["masters"][elem_code]
                    )
                else:
                    elem_labels.append(settings.entities.ENTITY_ID_TO_NAME[elem_code])
            else:
                elem_labels.append(settings.entities.ENTITY_ID_TO_NAME[elem_code])

        # create mapping from direct WordScape entity IDs to YOLO classes
        # this mapping will also be missing any dropped entity IDs
        entity_id_to_yolo_class = {}
        # needed for tracking while we build final map
        yolo_class_count = 0
        master_entity_ids_to_yolo_class = {}

        # first, map vanilla and master entity types to yolo classes
        for elem_code in master_elem_codes:
            entity_id_to_yolo_class[elem_code] = yolo_class_count
            if yolo_settings.elem_mergings:
                if elem_code in yolo_settings.elem_mergings["masters"].keys():
                    master_entity_ids_to_yolo_class[elem_code] = yolo_class_count
            yolo_class_count += 1

        # now, map any merged entity types to the yolo class of their master
        # TODO ensure that no dropped entity types can also be merged --> avoid potential experiment mistakes
        if yolo_settings.elem_mergings:
            for elem_code in yolo_settings.elem_mergings["mapping"].keys():
                entity_id_to_yolo_class[elem_code] = master_entity_ids_to_yolo_class[
                    yolo_settings.elem_mergings["mapping"][elem_code]
                ]

        return elem_labels, entity_id_to_yolo_class

    def create_dataset(self, yolo_settings: YOLOSettings):
        r"""
        A function to create a training or validation dataset from YOLO settings.
        """

        # TODO: other data augmentations (blurring, rotation, etc.)
        # TODO: consideration of autocorrect for lang filter, or just use fasttext?

        # TODO: elem weights (dont care about text blocks)?
        # TODO: filtering out docs with too many text blocks? min. number of elems?

        # augraphy defaults for now
        aug_pipeline = default_augraphy_pipeline()

        ############################## set up paths and vars ##############################
        out_path = settings.filesystem.EXPERIMENT_DIR / self.experiment_name / "train"
        if yolo_settings.is_validation:
            out_path = settings.filesystem.EXPERIMENT_DIR / self.experiment_name / "val"
        out_path_images = out_path / "images"
        out_path_labels = out_path / "labels"
        out_path_images.mkdir(parents=True, exist_ok=True)
        out_path_labels.mkdir(parents=True, exist_ok=True)
        # tracking of accepted images
        accepted_img = 0

        ############################## build labels ##############################
        _, entity_id_to_yolo_class = self.build_labels(yolo_settings)

        ############################## process metadata JSONs ##############################
        # TODO: expect unzipped files for now; tarfile library way too slow
        # file_list = sorted(filter(lambda x: str(x).endswith('.json') and ('/entities' in x), ((yolo_settings.raw_path / settings.filesystem.WS_MULTIMODAL).iterdir())))
        file_list = (
            yolo_settings.raw_path / settings.filesystem.WS_MULTIMODAL
        ).iterdir()
        file_list = list(
            filter(
                lambda x: str(x).endswith(".json") and ("/entities" in str(x)),
                file_list,
            )
        )
        file_list = sorted(file_list)
        for file in file_list:
            file_stem = file.stem.removeprefix("entities_")

            # stop if we have created enough images
            if (yolo_settings.max_img > 0) and (accepted_img >= yolo_settings.max_img):
                break

            # read the JSON metadata
            with open(file) as fopen:
                wordscape_meta = json.loads(fopen.read())

            ############################## first check any filters ##############################
            filters_passed = True
            # TODO quality filter (once we get new data)
            if yolo_settings.quality_threshold > 0:
                pass

            # allowed langs
            if len(yolo_settings.language_codes) > 0:
                lang_test_passed = False
                for allowed_lang in yolo_settings.language_codes:
                    if (
                        wordscape_meta["metadata"]["langs"][0][0]
                        == "__label__" + allowed_lang
                    ):
                        if (yolo_settings.language_code_threshold > 0) and (
                            yolo_settings.language_code_threshold
                            > wordscape_meta["metadata"]["langs"][1][0]
                        ):
                            lang_test_passed = False
                        else:
                            lang_test_passed = True
                if lang_test_passed == False:
                    filters_passed = False

            # filters passed
            if not filters_passed:
                continue

            ############################## transform JSON bounding boxes ##############################
            # get width and height for normalisation
            iw_norm = wordscape_meta["metadata"]["page_width"]
            ih_norm = wordscape_meta["metadata"]["page_height"]
            # tracking of line to be written to yolo-format txt
            yolo_format_txt = ""

            for entity_type in wordscape_meta["entities"]:
                # get the YOLO class for this entity type, if any
                if not int(entity_type) in entity_id_to_yolo_class.keys():
                    continue
                yolo_class = entity_id_to_yolo_class[int(entity_type)]

                # process each indidivually occurring entity bounding box
                for entity_occ in wordscape_meta["entities"][str(entity_type)]:
                    x_topleft = entity_occ["bbox"]["x"]
                    y_topleft = entity_occ["bbox"]["y"]
                    w = entity_occ["bbox"]["width"]
                    h = entity_occ["bbox"]["height"]

                    x_mid = x_topleft + w / 2
                    y_mid = y_topleft + h / 2

                    # yolo format normalization
                    # TODO: is this ok for datasets with varying img sizes?
                    x_norm = x_mid / iw_norm
                    y_norm = y_mid / ih_norm
                    w_norm = w / iw_norm
                    h_norm = h / ih_norm

                    yolo_format_txt += (
                        str(yolo_class)
                        + " "
                        + self.yolo_format_num(x_norm)
                        + " "
                        + self.yolo_format_num(y_norm)
                        + " "
                        + self.yolo_format_num(w_norm)
                        + " "
                        + self.yolo_format_num(h_norm)
                    ) + "\n"

            # write out YOLO format txt label file
            out_path_onelabel = out_path_labels / (file_stem + ".txt")
            with open(out_path_onelabel, "w") as outf:
                outf.write(yolo_format_txt)

            ############################## process page image ##############################
            # ! expectation for JSON to always possess corresponding .jpg
            img_file_name = file_stem + ".jpg"
            if yolo_settings.scanify:
                # TODO just augraphy defaults for now
                # TODO we need to take augraphy transforms into account, and adjust bounding boxes accordingly!
                # TODO InvalidParameterError: The 'center_box' parameter of make_blobs must be an instance of 'tuple'. Got [0, 68] instead.
                img_f = cv2.imread(
                    str(
                        yolo_settings.raw_path
                        / settings.filesystem.WS_MULTIMODAL
                        / img_file_name
                    )
                )
                aug = aug_pipeline.augment(img_f)
                aug_img = aug["output"]
                cv2.imwrite(str(out_path_images / img_file_name), aug_img)
            else:
                shutil.copy(
                    yolo_settings.raw_path
                    / settings.filesystem.WS_MULTIMODAL
                    / img_file_name,
                    out_path_images / img_file_name,
                )

    def create_yolo_descriptor(self):
        r"""
        Create YOLO dataset descriptor, containing path information.
        """

        # ! note that mergings and drops have to be identical in train / val sets!
        # take care of this while generating experiments.
        labels, _ = self.build_labels(self.train_settings)

        out_yaml = (
            settings.filesystem.EXPERIMENT_DIR / self.experiment_name / "dataset.yaml"
        )
        with open(out_yaml, "w") as out_yaml_w:
            out_yaml_w.write(
                "train: "
                + str(
                    settings.filesystem.EXPERIMENT_DIR / self.experiment_name / "train"
                )
                + "\n"
            )
            out_yaml_w.write(
                "val: "
                + str(settings.filesystem.EXPERIMENT_DIR / self.experiment_name / "val")
                + "\n"
            )
            out_yaml_w.write("nc: " + str(len(labels)) + "\n")
            out_yaml_w.write("names: " + str(labels) + "\n")

    def run(self):
        r"""
        Create training and validation datasets, as well as YOLO dataset descriptor, depending on YOLO settings
        passed during init.
        """

        self.create_dataset(self.train_settings)
        self.create_dataset(self.val_settings)
        self.create_yolo_descriptor()
