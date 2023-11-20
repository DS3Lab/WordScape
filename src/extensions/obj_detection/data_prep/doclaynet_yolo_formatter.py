import argparse
from pathlib import Path
import json
import cv2

def main():
    r"""A function to transform raw doclaynet data into ultralytics YOLO format."""
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--doclaynet_path", "-dp", type=str, help="path to doclaynet dataset", default="/mnt/DATA/msc-data/doclaynet/DocLayNet_core")
    arg_parser.add_argument("--out_path", "-op", type=str, help="path to save formatted dataset", default="/mnt/DATA/msc-data/yolo_doclaynet")
    args = arg_parser.parse_args()

    # create necessary folders
    doclaynet_basepath = Path(args.doclaynet_path)
    out_basepath = Path(args.out_path)

    outpath_train = out_basepath / "train"
    outpath_train.mkdir(parents=True, exist_ok=True)
    outpath_val = out_basepath / "val"
    outpath_val.mkdir(parents=True, exist_ok=True)

    # handle the three different COCO files (merge test and val into just val due to YOLO reporting)
    handle_coco_json(path_tojson=(doclaynet_basepath / "COCO" / "val.json"), outpath=outpath_val)
    handle_coco_json(path_tojson=(doclaynet_basepath / "COCO" / "test.json"), outpath=outpath_val)
    handle_coco_json(path_tojson=(doclaynet_basepath / "COCO" / "train.json"), outpath=outpath_train)
    build_yolo_desc(path_tojson=(doclaynet_basepath / "COCO" / "train.json"), outpath=out_basepath)


def yolo_format_num(num: float) -> str:
    r"""Format a float as required by YOLO"""
    return str(num)[0:10]


def handle_coco_json(path_tojson: Path, outpath: Path):
    r"""A function to handle each COCO doclaynet json (test, train and val in the base dataset)."""

    # make img and labels folder
    outpath_img = outpath / "images"
    outpath_img.mkdir(parents=True, exist_ok=True)
    outpath_labels = outpath / "labels"
    outpath_labels.mkdir(parents=True, exist_ok=True)

    # get the path to PNG folder
    orig_img_folder = path_tojson.parent.parent / "PNG"

    # read the json
    with open(path_tojson) as json_open:
        doclaynet_meta = json.load(json_open)

    # first, we must make a mapping from image files to their IDs, and also copy them to the image folder
    img_idtoinfo = {}
    for img_desc in doclaynet_meta["images"]:
        initial_obj = {"fname": img_desc["file_name"], "w_norm": img_desc["width"], "h_norm": img_desc["height"], "bboxes": []}
        img_idtoinfo[img_desc["id"]] = initial_obj
        
        # copy over the image
        img_f = cv2.imread(
            str(
                orig_img_folder
                / initial_obj["fname"]
            )
        )
        # TODO shared augraphy handler
        aug_img = img_f
        print(str(outpath_img / initial_obj["fname"]))
        cv2.imwrite(
            str(outpath_img / initial_obj["fname"]), aug_img
        )

    # go through all bounding boxes, and associate them with their images
    for bbox_raw in doclaynet_meta["annotations"]:
        # ! COCO bounding boxes are x_min, y_min, w, h
        initial_obj = {"cat": bbox_raw["category_id"], 
                       "bbox": {
                           "x": bbox_raw["bbox"][0],
                           "y": bbox_raw["bbox"][1],
                           "width": bbox_raw["bbox"][2],
                           "height": bbox_raw["bbox"][3],
                       }}
        img_idtoinfo[bbox_raw["image_id"]]["bboxes"].append(initial_obj)

    # build YOLO-format label files
    for id, img_info in img_idtoinfo.items():
        print(id)
        iw_norm = img_info["w_norm"]
        ih_norm = img_info["h_norm"]
        # tracking of line to be written to yolo-format txt
        yolo_format_txt = ""

        # len_tracker = 0
        for bbox in img_info["bboxes"]:
            # ! note that doclaynet category IDs begin with 1, while YOLO expects a count beginning with 0
            yolo_class = bbox["cat"] - 1

            # process each indidivually occurring entity bounding box
            x_topleft = bbox["bbox"]["x"]
            y_topleft = bbox["bbox"]["y"]
            w = bbox["bbox"]["width"]
            h = bbox["bbox"]["height"]

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

        # save to the labels folder
        outpath_onelabel = outpath_labels / img_info["fname"].replace('.png', '.txt')
        with open(outpath_onelabel, "w") as outf:
            outf.write(yolo_format_txt)


def get_coco_labels(path_tojson: Path):
    r"""Get the label names necessary for YOLO-format dataset descriptor. This comes from the categories section of the JSON."""
    
    with open(path_tojson) as json_open:
        doclaynet_meta = json.load(json_open)

    cat_names = []
    for cat in doclaynet_meta["categories"]:
        # already ordered in the JSON
        cat_names.append(cat["name"])

    return cat_names


def build_yolo_desc(path_tojson: Path, outpath: Path):
    labels = get_coco_labels(path_tojson)

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