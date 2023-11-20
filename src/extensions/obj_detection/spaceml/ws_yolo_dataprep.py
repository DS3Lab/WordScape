import sys
from pathlib import Path

module_path = str(Path.cwd())
if module_path not in sys.path:
    sys.path.append(module_path)

print(module_path)
print(sys.path)

from src.extensions.obj_detection.data_prep.wordscape_yolo_formatter import (
    WSYOLOFormatter,
)
from src.extensions.obj_detection.data_prep.wordscape_yolo_config_handler import *
import settings
import argparse
import json
import multiprocessing as mp
import os


def main():
    r"""
    A script to generate experiment datasets for using WordScape data with YOLO object detection.
    Arguments are a path to the experiment config (which contains the path to the raw data),
    and optionally an output path to override the default output path.
    """

    # read args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--experiment_config",
        "-ec",
        type=str,
        default="/home/valde/GitHub/WordScape/ext_configs/obj_detection/ws_yolo/baseline_quality.json",
        help="path to experiment config to use",
    )
    arg_parser.add_argument(
        "--output_path",
        "-op",
        type=str,
        default=None,
        help="optional override of output path",
    )
    arg_parser.add_argument(
        "--num_proc",
        "-np",
        type=int,
        default=1,
        help="number of processes to spawn per elem_min entity type (helpful to speed up rare entities)",
    )
    args = arg_parser.parse_args()

    # parse config
    with open(args.experiment_config) as exp_conf:
        exp_conf_obj = json.loads(exp_conf.read())
    train_settings, val_settings = parse_config(exp_conf_obj)

    # queues to count accepted docs for train / val
    train_q = mp.Queue()
    val_q = mp.Queue()

    # for each train_setting and val_setting (based on config parsing, multiple configs possible if minimum elem numbers are used)
    # create a process, and check total amount of examples accepted per element that has a min amount detailed
    processes = []
    for setting_index in range(len(train_settings)):
        for _ in range(args.num_proc):
            # spawning multiple for same entity is ok because of accept_existing setting not increasing counts
            proc = WSYOLOFormatter(
                train_settings[setting_index],
                val_settings[setting_index],
                exp_conf_obj["name"],
                args.output_path,
                train_q,
                val_q,
            )
            proc.start()
            print("started dataset process, with config: ")
            print(train_settings[setting_index])
            print(train_settings[setting_index].elem_accepts)
            processes.append(proc)

    # wait for processes to finish, and get counts of accepted images
    for proc_j in processes:
        proc_j.join()
    total_train = 0
    total_val = 0
    for proc_j in processes:
        total_train += train_q.get()
        total_val += val_q.get()
    print("total train " + str(total_train))
    print("total val " + str(total_val))

    # we need to count the actual files in the folder, as there may have been overwrites
    total_train = len(
        [
            f
            for f in os.listdir(
                args.output_path + "/" + exp_conf_obj["name"] + "/train/labels"
            )
        ]
    )
    total_val = len(
        [
            f
            for f in os.listdir(
                args.output_path + "/" + exp_conf_obj["name"] + "/val/labels"
            )
        ]
    )

    # finally, create one process without elem_min rules to fill up to desired images
    # without consideration of elem_mins
    exp_conf_obj_final = exp_conf_obj
    exp_conf_obj_final["train_settings"]["elem_mins"] = {}
    exp_conf_obj_final["val_settings"]["elem_mins"] = {}
    exp_conf_obj_final["train_settings"]["max_img"] = max(
        exp_conf_obj_final["train_settings"]["max_img"] - total_train, 0
    )
    exp_conf_obj_final["val_settings"]["max_img"] = max(
        exp_conf_obj_final["val_settings"]["max_img"] - total_val, 0
    )
    finisher_train_settings, finisher_val_settings = parse_config(exp_conf_obj_final)

    # also use this last process to create the dataset config
    print("running finisher process, with config")
    print(exp_conf_obj_final)
    finisher_proc = WSYOLOFormatter(
        finisher_train_settings[0],
        finisher_val_settings[0],
        exp_conf_obj_final["name"],
        args.output_path,
        train_q,
        val_q,
        is_final=True,
        accept_existing=False,
    )
    finisher_proc.start()
    finisher_proc.join()


if __name__ == "__main__":
    main()
