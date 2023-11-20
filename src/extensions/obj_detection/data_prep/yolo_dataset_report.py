import argparse
import yaml
from pathlib import Path
import settings
import json


def parse_label_folder(folder_path: Path) -> dict:
    # track total results
    entity_counts = {key: 0 for key in settings.entities.LABEL_NUMS}
    # also track empty label examples
    empty_labels = 0

    for txt_file in folder_path.glob("*"):
        # read the txt file
        txt_lines = []
        with open(txt_file, "r") as txt_file_open:
            for line in txt_file_open.readlines():
                line_list = line.split()
                txt_lines.append(line_list)

        # only count unique bboxes per img
        txt_lines = [list(x) for x in set(tuple(x) for x in txt_lines)]
        # count entity appearances
        for entry in txt_lines:
            entity_counts[int(entry[0])] = entity_counts[int(entry[0])] + 1

        if len(txt_lines) == 0:
            empty_labels += 1

    entity_counts[-1] = empty_labels
    return entity_counts


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument(
        "--dataset_path",
        "-dp",
        type=str,
        default="/mnt/DATA/msc-data/yolo_wordscape_experiments/3headers_balanced_quality",
        help="path to dataset to analyze",
    )
    args = arg_parser.parse_args()

    # read labels for yolo classes from dataset.yaml
    ds_path = Path(args.dataset_path)
    with open(ds_path / "dataset.yaml", "r") as stream:
        yaml_ds = yaml.safe_load(stream)
    labels = yaml_ds["names"]

    # check train and val data
    train_counts = parse_label_folder(ds_path / "train" / "labels")
    val_counts = parse_label_folder(ds_path / "val" / "labels")

    # apply labels for report
    train_counts_formatted = {}
    val_counts_formatted = {}
    for i in range(len(labels)):
        train_counts_formatted[labels[i]] = train_counts[i]
        val_counts_formatted[labels[i]] = val_counts[i]
    train_counts_formatted["empty_labels"] = train_counts[-1]
    val_counts_formatted["empty_labels"] = val_counts[-1]

    report_dict = {
        "train_counts": train_counts_formatted,
        "val_counts": val_counts_formatted,
    }
    with open(ds_path / "report.json", "w") as report_w:
        json.dump(report_dict, report_w)


if __name__ == "__main__":
    main()
