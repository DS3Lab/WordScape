import argparse
import json
from pathlib import Path

import cv2


def main():
    r"""A function to transform raw publaynet data into ultralytics YOLO format."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--publaynet_path", "-pp", type=str, help="path to publaynet dataset", default="/mnt/DATA/msc-data/doclaynet/DocLayNet_core")
    arg_parser.add_argument("--out_path", "-op", type=str, help="path to save formatted dataset", default="/mnt/DATA/msc-data/yolo_doclaynet")
    args = arg_parser.parse_args()

    # create necessary folders
    publaynet_basepath = Path(args.publaynet_path)
    out_basepath = Path(args.out_path)

    outpath_train = out_basepath / "train"
    outpath_train.mkdir(parents=True, exist_ok=True)
    outpath_val = out_basepath / "val"
    outpath_val.mkdir(parents=True, exist_ok=True)

    handle_publaynet_json(path_tojson=(publaynet_basepath / "train.json"), path_toimg=(publaynet_basepath / "train"), outpath=outpath_train, max_img=200000)
    handle_publaynet_json(path_tojson=(publaynet_basepath / "val.json"), path_toimg=(publaynet_basepath / "val"), outpath=outpath_val, max_img=0)
    build_yolo_desc(outpath=out_basepath)


def yolo_format_num(num: float) -> str:
    r"""Format a float as required by YOLO"""
    return str(num)[0:10]


def handle_publaynet_json(path_tojson: Path, path_toimg: Path, outpath: Path, max_img: int):
    # count total processed images
    proc_img = 0

    # make img and labels folder
    outpath_img = outpath / "images"
    outpath_img.mkdir(parents=True, exist_ok=True)
    outpath_labels = outpath / "labels"
    outpath_labels.mkdir(parents=True, exist_ok=True)


    with open(path_tojson) as json_open:
        publaynet_meta = json.load(json_open)

    # need to bring annotations into mapping for image id
    img_id_to_bboxes = {}
    for i in range(1000000):
        img_id_to_bboxes[i] = []
    for annotation in publaynet_meta["annotations"]:
        img_id_to_bboxes[int(annotation['image_id'])].append({'bbox': annotation['bbox'], 'category_id': annotation['category_id']})

    for img_desc in publaynet_meta["images"]:
        # dont process more than max_img
        if ((max_img > 0) and (proc_img >= max_img)):
            break

        # there may not be any bbox annotations
        # ! need to skip these
        annotation_object = []
        if not ("annotations" in img_desc.keys()):
            annotation_object = img_id_to_bboxes[int(img_desc['id'])]
        if ("annotations" in img_desc.keys()):
            annotation_object = img_desc['annotations']

        # get the image descriptor
        img_name = img_desc["file_name"]

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
        iw_norm = int(img_desc["width"])
        ih_norm = int(img_desc["height"])

        # build the labels txt file
        yolo_format_txt = ""

        for annotation in annotation_object:
            # get the bbox
            bbox = annotation["bbox"]
            # category id annotation
            publaynet_cat_id = int(annotation["category_id"])

            # need to start counting categories from 0 as opposed to 1 for YOLO-format
            yolo_class = publaynet_cat_id - 1

            # process each indidivually occurring entity bounding box
            x_topleft = float(bbox[0])
            y_topleft = float(bbox[1])
            w = float(bbox[2])
            h = float(bbox[3])

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
        outpath_onelabel = outpath_labels / img_name.replace('.jpg', '.txt')
        with open(outpath_onelabel, "w") as outf:
            outf.write(yolo_format_txt)

        # add to processed images
        proc_img += 1


def build_yolo_desc(outpath: Path):
    # hardcoded labels, based on paper
    labels = ["text", "title", "list", "table", "figure"]

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