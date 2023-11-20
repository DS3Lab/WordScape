import copy
from dataclasses import dataclass
from typing import Dict, List, Tuple
from pathlib import Path
import settings


@dataclass
class WSLayoutLMSettings:
    r"""
    A class describing the settings for creating a HuggingFace/LayoutLMv3-format dataset.

    @param raw_path: Path to raw data to be formatted and / or filtered for the experiment.
    @param is_validation: Wether these settings apply to validation data. Determines the path the dataset is written to.
    @param max_img: max number of images to process from the raw_path (done in alphabetical ordering).
        This many files will be in the "labels" and "images" folder, respectively.
    @param elem_drops: WordScape elements (by ID) to drop from the dataset.
        Note that this overrides elem_mergings; e.g elements being dropped will not be merged into
        any element, even if included in elem_mergings.
    @param elem_mergings: Describes WordScape element IDs to be merged into one class, and how to label the new class.
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
    @param elem_accepts: Pages must contain at least one of this element (after merging) in order to be accepted.
        Enables creation of a balanced dataset.
    @param scanify: Wether to create a scan-appearing document, using the augraphy library
    @param quality_threshold: Whether to filter documents based on WordScapes annotation quality score between 0 and 1.
        Only active if above 0.
    @param language_codes: Filter on only allowing documents containing these (fasstext / WordScape autocorrect metadata) language codes.
        Only considers most-likely lang (first in the list).
    @param language_code_threshold: Required threshold for language acceptance from fasstext (between 0 and 1). Only active if above 0.
    """

    raw_path: Path = (Path("/home/valde/GitHub/msc-thesis/data/raw/format_test_train"),)
    # out_path: Path = Path('/home/valde/GitHub/msc-thesis/data/experiments/format_test/train'),
    max_img: int = (75_000,)
    elem_drops: List[int] = ([],)
    # TODO typing info
    elem_mergings: Dict = (None,)
    elem_accepts = (settings.entities.LABEL_NUMS,)
    scanify: bool = (False,)
    quality_threshold: float = (-1.0,)
    language_codes: List[str] = ([],)
    language_code_threshold: float = -1.0

    # for some reason the standard dataclass init does not play nice with elem_mergings
    def __init__(
        self,
        raw_path,
        max_img,
        elem_drops,
        elem_mergings,
        elem_accepts,
        scanify,
        quality_threshold,
        language_codes,
        language_code_threshold,
    ):
        self.raw_path = raw_path
        self.max_img = max_img
        self.elem_drops = elem_drops
        self.elem_mergings = elem_mergings
        self.elem_accepts = elem_accepts
        self.scanify = scanify
        self.quality_threshold = quality_threshold
        self.language_codes = language_codes
        self.language_code_threshold = language_code_threshold


def json_to_config(json_obj) -> List[WSLayoutLMSettings]:
    # make elem_mergings
    elem_mergings_formatted = {}
    elem_mergings_json = json_obj["settings"]["elem_mergings"]
    if len(elem_mergings_json) == 0:
        elem_mergings_formatted = {"masters": {}, "mapping": {}}
    else:
        masters = {}
        for key in elem_mergings_json["masters"]:
            masters[int(key)] = elem_mergings_json["masters"][key]
        mapping = {}
        for key in elem_mergings_json["mapping"]:
            mapping[int(key)] = int(elem_mergings_json["mapping"][key])

        elem_mergings_formatted = {"masters": masters, "mapping": mapping}

    # check if elem_accepts are defined by the provided JSON
    elem_accepts_base = settings.entities.LABEL_NUMS
    if (
        ("elem_accepts" in json_obj["settings"].keys())
        and (json_obj["settings"]["elem_accepts"] != None)
        and (len(json_obj["settings"]["elem_accepts"]) > 0)
    ):
        elem_accepts_base = json_obj["settings"]["elem_accepts"]

    base_settings = WSLayoutLMSettings(
        raw_path=Path(json_obj["settings"]["raw_path"]),
        max_img=json_obj["settings"]["max_img"],
        elem_drops=json_obj["settings"]["elem_drops"],
        elem_mergings=elem_mergings_formatted,
        elem_accepts=elem_accepts_base,
        scanify=json_obj["settings"]["scanify"],
        quality_threshold=json_obj["settings"]["quality_threshold"],
        language_codes=json_obj["settings"]["language_codes"],
        language_code_threshold=json_obj["settings"]["language_code_threshold"],
    )

    # check if there are element minimums defined. If not, return the base settings
    if (
        ("elem_mins" in json_obj["settings"].keys())
        and (json_obj["settings"]["elem_mins"] != None)
        and (len(json_obj["settings"]["elem_mins"]) > 0)
    ):
        settings_list = []
        for elem_type in json_obj["settings"]["elem_mins"].keys():
            setting_modified = copy.deepcopy(base_settings)
            # distinction: elem_drops (dont include in dataset) vs. elems that we require to be in a doc (for filter purposes)
            setting_modified.elem_accepts = [int(elem_type)]
            setting_modified.max_img = json_obj["settings"]["elem_mins"][elem_type]
            settings_list.append(setting_modified)
        return settings_list
    else:
        return [base_settings]


def parse_config(json_obj) -> List[WSLayoutLMSettings]:
    r"""
    Parse a json config to LayoutLM settings object.
    """

    settings = json_to_config(json_obj)
    return settings
