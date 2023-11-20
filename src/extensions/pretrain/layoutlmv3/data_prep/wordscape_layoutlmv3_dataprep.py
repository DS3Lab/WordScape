import sys
from pathlib import Path

module_path = str(Path.cwd().parents[0].parents[0].parents[0])
if module_path not in sys.path:
    sys.path.append(module_path)

from src.extensions.pretrain.layoutlmv3.data_prep.wordscape_layoutlmv3_config_handler import *
from src.extensions.pretrain.layoutlmv3.data_prep.wordscape_layoutlmv3_formatter import (
    WSLayoutLMFormatter,
)
from src.extensions.pretrain.layoutlmv3.data_prep.wordscape_layoutlmv3_datasetbuilder import (
    WSLayoutLMDataCollectorProcess,
)
import settings
import argparse
import json
import multiprocessing as mp
import os


def main():
    r"""
    A script to generate experiment datasets for using WordScape data with LayoutLM.
    Arguments are a path to the experiment config (which contains the path to the raw data),
    and optionally an output path to override the default output path.
    """

    # read args
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--experiment_config",
        "-ec",
        type=str,
        default="/home/valde/GitHub/WordScape/ext_configs/pretrain/layoutlm/1header_balanced_quality_test.json",
        help="path to experiment config to use",
    )
    arg_parser.add_argument(
        "--output_path",
        "-op",
        type=str,
        default=None,
        help="output path",
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
    data_settings = parse_config(exp_conf_obj)

    # queue to send data to collector process
    data_q = mp.Queue()
    # queue for collector process to track its progress
    count_q = mp.Queue()

    # for each train_setting and val_setting (based on config parsing, multiple configs possible if minimum elem numbers are used)
    # create a process, and check total amount of examples accepted per element that has a min amount detailed
    processes = []
    for setting_index in range(len(data_settings)):
        for _ in range(args.num_proc):
            # spawning multiple for same entity is ok because of accept_existing setting not increasing counts
            proc = WSLayoutLMFormatter(
                data_settings[setting_index],
                exp_conf_obj["name"],
                args.output_path,
                data_q,
            )
            # need labels for collector_proc
            if setting_index == 0:
                labels, _ = proc.build_labels(data_settings[setting_index])
            proc.start()
            print("started dataset process, with config: ")
            print(data_settings[setting_index])
            print(data_settings[setting_index].elem_accepts)
            processes.append(proc)

    # process to collect datapoints into a huggingface dataset
    # +1 process to wait for finisher process
    collector_proc = WSLayoutLMDataCollectorProcess(
        entity_label_names=labels,
        in_q=data_q,
        proc_to_wait=(len(processes) + 1),
        out_q=count_q,
        out_path=(Path(args.output_path) / exp_conf_obj["name"]),
    )
    collector_proc.start()

    # wait for processes to finish, and get counts of accepted images
    for proc_j in processes:
        proc_j.join()
    # signal collector to give us accepted datapoints so far
    total_data = collector_proc.get_count()
    print("total data " + str(total_data))

    # finally, create one process without elem_min rules to fill up to desired images
    # without consideration of elem_mins
    exp_conf_obj_final = exp_conf_obj
    exp_conf_obj_final["settings"]["elem_mins"] = {}
    exp_conf_obj_final["settings"]["max_img"] = max(
        exp_conf_obj_final["settings"]["max_img"] - total_data, 0
    )
    finisher_settings = parse_config(exp_conf_obj_final)

    # also use this last process to create the dataset config
    print("running finisher process, with config")
    print(exp_conf_obj_final)
    finisher_proc = WSLayoutLMFormatter(
        finisher_settings[0],
        exp_conf_obj_final["name"],
        args.output_path,
        data_q,
        is_final=True,
        accept_existing=False,
    )
    finisher_proc.start()
    finisher_proc.join()

    # finally, finish the collector process
    collector_proc.join()


if __name__ == "__main__":
    main()
