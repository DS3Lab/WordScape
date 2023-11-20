import argparse
import json
from pathlib import Path

import cv2


def main():
    r"""A function to transform raw pubtabnet data into ultralytics YOLO format."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--pubtabnet_path", "-pp", type=str, help="path to pubtabnet dataset", default="/mnt/DATA/msc-data/PubTabNet/pubtabnet")
    arg_parser.add_argument("--out_path", "-op", type=str, help="path to save formatted dataset", default="/mnt/DATA/msc-data/PubTabNet/yolo_pubtabnet")
    args = arg_parser.parse_args()

    # create necessary folders
    pubtabnet_basepath = Path(args.pubtabnet_path)
    out_basepath = Path(args.out_path)

    outpath_train = out_basepath / "train"
    outpath_train.mkdir(parents=True, exist_ok=True)
    outpath_val = out_basepath / "val"
    outpath_val.mkdir(parents=True, exist_ok=True)

    handle_pubtabnet_json(path_tojson=(pubtabnet_basepath / "PubTabNet_2.0.0.jsonl"), path_toimg=(pubtabnet_basepath / "train"), outpath=outpath_train, max_img=200000, is_val=False)
    handle_pubtabnet_json(path_tojson=(pubtabnet_basepath / "PubTabNet_2.0.0.jsonl"), path_toimg=(pubtabnet_basepath / "val"), outpath=outpath_val, max_img=0, is_val=True)
    build_yolo_desc(outpath=out_basepath)


def yolo_format_num(num: float) -> str:
    r"""Format a float as required by YOLO"""
    return str(num)[0:10]


def handle_pubtabnet_json(path_tojson: Path, path_toimg: Path, outpath: Path, max_img: int, is_val: bool):
    # count total processed images
    proc_img = 0

    # make img and labels folder
    outpath_img = outpath / "images"
    outpath_img.mkdir(parents=True, exist_ok=True)
    outpath_labels = outpath / "labels"
    outpath_labels.mkdir(parents=True, exist_ok=True)


    # with open(path_tojson) as json_open:
    #     pubtabnet_meta = json.load(json_open)

    # need to bring annotations into mapping for image id
    img_filename_to_bboxes = {}
    # read the jsonl into array of dicts
    jsonl_data = []
    with open(path_tojson) as jsonl_open:
        for line in jsonl_open:
            try:
                jsonl_data.append(json.loads(line))
            except Exception as e:
                print(e)
                continue

    targetsplit = "train"
    if is_val:
        targetsplit = "val"

    for annotation in jsonl_data:
        if (annotation['split'] == targetsplit):
            bbox_container = []
            for item in annotation["html"]["cells"]:
                # ! only cell category exists in dataset
                if ("bbox" in item.keys()):
                    bbox_container.append({'bbox': item['bbox'], 'category_id': 0})
            img_filename_to_bboxes[annotation['filename']] = bbox_container

    for img_name in img_filename_to_bboxes.keys():
        # dont process more than max_img
        if ((max_img > 0) and (proc_img >= max_img)):
            break

        # check if image exists in the folder
        img_path = path_toimg / img_name
        if not img_path.is_file():
            continue

        # read and copy the file to output
        img_f = cv2.imread(
            str(
                img_path
            )
        )
        # TODO shared augraphy handler
        aug_img = img_f
        cv2.imwrite(
            str(outpath_img / img_name), aug_img
        )

        # get w and h of the image
        hh, ww, _ = img_f.shape
        iw_norm = ww
        ih_norm = hh

        # build the labels txt file
        yolo_format_txt = ""

        for annotation in img_filename_to_bboxes[img_name]:
            # get the bbox
            bbox = annotation["bbox"]
            # category id annotation
            cat_id = int(annotation["category_id"])

            # need to start counting categories from 0 as opposed to 1 for YOLO-format
            yolo_class = cat_id

            # process each indidivually occurring entity bounding box
            x_topleft = float(bbox[0])
            y_topleft = float(bbox[1])
            x_bottomright = float(bbox[2])
            y_bottomright = float(bbox[3])
            w = (x_bottomright - x_topleft)
            h = (y_bottomright - y_topleft)

            x_mid = x_topleft + w / 2
            y_mid = y_topleft + h / 2

            # yolo format normalization
            x_norm = x_mid / iw_norm
            y_norm = y_mid / ih_norm
            w_norm = w / iw_norm
            h_norm = h / ih_norm

            yolo_format_txt += (
                str(yolo_class)
                + " "
                + yolo_format_num(x_norm)
                + " "
                + yolo_format_num(y_norm)
                + " "
                + yolo_format_num(w_norm)
                + " "
                + yolo_format_num(h_norm)
            ) + "\n"

        # write the yolo label info
        outpath_onelabel = outpath_labels / img_name.replace('.jpg', '.txt').replace('.png', '.txt')
        with open(outpath_onelabel, "w") as outf:
            outf.write(yolo_format_txt)

        # add to processed images
        proc_img += 1


def build_yolo_desc(outpath: Path):
    # hardcoded labels, based on paper
    labels = ["table_cell"]

    out_yaml = outpath / "dataset.yaml"
    with open(out_yaml, "w") as out_yaml_w:
        out_yaml_w.write(
            "train: " + str(outpath / "train") + "\n"
        )
        out_yaml_w.write(
            "val: " + str(outpath / "val") + "\n"
        )
        out_yaml_w.write("nc: " + str(len(labels)) + "\n")
        out_yaml_w.write("names: " + str(labels) + "\n")


if __name__ == "__main__":
    main()