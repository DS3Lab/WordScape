import copy
from typing import List, Tuple
from src.extensions.obj_detection.data_prep.wordscape_yolo_formatter import YOLOSettings
from pathlib import Path
import settings


def json_to_config(json_obj, first_key: str) -> YOLOSettings:
    # make elem_mergings
    elem_mergings_formatted = {}
    elem_mergings_json = json_obj[first_key]["elem_mergings"]
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
        ("elem_accepts" in json_obj[first_key].keys())
        and (json_obj[first_key]["elem_accepts"] != None)
        and (len(json_obj[first_key]["elem_accepts"]) > 0)
    ):
        elem_accepts_base = json_obj[first_key]["elem_accepts"]

    base_settings = YOLOSettings(
        raw_path=Path(json_obj[first_key]["raw_path"]),
        is_validation=json_obj[first_key]["is_validation"],
        max_img=json_obj[first_key]["max_img"],
        elem_drops=json_obj[first_key]["elem_drops"],
        elem_mergings=elem_mergings_formatted,
        elem_accepts=elem_accepts_base,
        scanify=json_obj[first_key]["scanify"],
        quality_threshold=json_obj[first_key]["quality_threshold"],
        language_codes=json_obj[first_key]["language_codes"],
        language_code_threshold=json_obj[first_key]["language_code_threshold"],
    )

    # check if there are element minimums defined. If not, return the base settings
    if (
        ("elem_mins" in json_obj[first_key].keys())
        and (json_obj[first_key]["elem_mins"] != None)
        and (len(json_obj[first_key]["elem_mins"]) > 0)
    ):
        settings_list = []
        for elem_type in json_obj[first_key]["elem_mins"].keys():
            setting_modified = copy.deepcopy(base_settings)
            # distinction: elem_drops (dont include in dataset) vs. elems that we require to be in a doc (for filter purposes)
            setting_modified.elem_accepts = [int(elem_type)]
            setting_modified.max_img = json_obj[first_key]["elem_mins"][elem_type]
            settings_list.append(setting_modified)
        return settings_list
    else:
        return [base_settings]


def parse_config(json_obj) -> Tuple[List[YOLOSettings], List[YOLOSettings]]:
    r"""
    Parse a json config to two YOLOSettings objects for train and validation dataset.
    """

    train_settings = json_to_config(json_obj, "train_settings")
    val_settings = json_to_config(json_obj, "val_settings")

    return train_settings, val_settings
