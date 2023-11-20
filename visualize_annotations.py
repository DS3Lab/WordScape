import argparse
import cv2
import json
import math
import numpy as np
import pathlib
import ray
from typing import List, Dict, Tuple

import settings
from src.annotation.annotation_objects import BoundingBox, Entity
from src.annotation.utils import hsv_to_bgr

parser = argparse.ArgumentParser()
parser.add_argument("--annotations_dir", default=None, type=str)
parser.add_argument("--subset_size", default=-1, type=int)
parser.add_argument("--entity_ids", nargs="+", default=None, type=int,
                    help="List of entity ids to visualize (default: all).")
args = parser.parse_args()


def draw_bounding_boxes(src_fp, save_as, entities: Dict[int, List[Entity]]):
    img = cv2.imread(src_fp)
    num_matches = 0

    for entity_id, entity_list in entities.items():
        if (
                args.entity_ids is not None
                and
                int(entity_id) not in args.entity_ids
        ):
            continue

        # exclude table rows and columns to avoid clutter in case we are
        # visualizing all entities
        if int(entity_id) in [
            settings.entities.ENTITY_TABLE_ROW_ID,
            settings.entities.ENTITY_TABLE_HEADER_ROW_ID,
            settings.entities.ENTITY_TABLE_COLUMN_ID
        ]:
            continue

        color_hsv = settings.colors.ENTITY_CATEGORY_ID_TO_COLOR[int(entity_id)]
        color_rgb = hsv_to_bgr(color_hsv)
        entity_name = settings.entities.ENTITY_ID_TO_NAME[int(entity_id)]
        for entity in entity_list:
            bbox = entity.bbox
            img = draw_bbox(img, bbox, color_rgb, tag=entity_name,
                            alpha=0.8)

            num_matches += 1

    if num_matches > 0:
        cv2.imwrite(save_as, img)


def draw_bbox(
        img: np.ndarray,
        bbox: BoundingBox,
        bgr_color: Tuple[int, int, int],
        tag: str = None,
        alpha: float = 0.4,
        thickness=2
) -> np.ndarray:
    r"""Draws a bounding box on an image.

    @param img: image
    @param bbox: bounding box
    @param bgr_color: color of the bounding box
    @param tag: tag to be displayed in the bounding box
    @param alpha: transparency of the bounding box
    @param thickness: thickness of the bounding box lines

    @return: image with bounding box
    """
    # get bounding box coordinates
    top_left = (bbox.x - 2, bbox.y - 2)
    bottom_right = (bbox.x + bbox.width + 2, bbox.y + bbox.height + 2)

    # draw bounding box
    img = cv2.rectangle(
        img, pt1=top_left, pt2=bottom_right, color=bgr_color,
        thickness=thickness
    )

    # draw tag
    if tag is not None:
        (w_tag, h_tag), _ = cv2.getTextSize(
            tag, fontFace=cv2.FONT_HERSHEY_SIMPLEX, fontScale=0.4, thickness=1
        )

        pt1 = (top_left[0], top_left[1] - h_tag - 2)
        pt2 = (top_left[0] + w_tag + 2, top_left[1])
        org = (top_left[0] + 2, top_left[1] - 2)

        img = cv2.rectangle(img, pt1, pt2, bgr_color, -1)
        cv2.putText(img, text=tag, org=org,
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=0.4, color=(0, 0, 0),
                    thickness=1)

    if math.isclose(alpha, 1.0):
        return img

    # Create a mask of the bounding box
    x_start = max(0, int(bbox.x))
    x_end = int(bbox.x + bbox.width)
    y_start = max(0, int(bbox.y))
    y_end = int(bbox.y + bbox.height)

    sub_img = img[y_start:y_end, x_start:x_end]
    rect = np.ones_like(sub_img) * np.array(bgr_color, dtype=np.uint8)
    res = cv2.addWeighted(sub_img, alpha, rect, 1 - alpha, 1.0)

    try:
        img[y_start:y_end, x_start:x_end] = res
    except TypeError:
        pass

    return img


def page_iterator(annotations_dir: pathlib.Path, subset_size: int):
    for i, fp in enumerate(annotations_dir.rglob(pattern="*.json")):
        if not str(fp.name).startswith("entities"):
            continue

        img_fn = fp.with_suffix(".jpg").name.replace("entities_", "")
        img_fp = fp.parent / img_fn

        if i >= subset_size >= 0:
            break

        with open(fp, "r") as f:
            entities = json.load(f)["entities"]

        entities = {
            cat_id: [Entity(
                doc_id=e["doc_id"],
                page_id=e["page_id"],
                page_num=e["page_num"],
                entity_category=e["entity_category"],
                bbox=BoundingBox(**e["bbox"])
            ) for e in entity_list]
            for cat_id, entity_list in entities.items()
        }

        yield entities, img_fp


@ray.remote
def visualize_page(
        entities: Dict[int, List[Entity]],
        page_img_fp: pathlib.Path,
        target_dir: pathlib.Path
):
    debug_save_as = pathlib.Path(
        target_dir, page_img_fp.name
    )
    draw_bounding_boxes(
        src_fp=str(page_img_fp),
        save_as=str(debug_save_as),
        entities=entities,
    )
    print("processed page", page_img_fp.name)


def main():
    # setup dirs
    annotations_dir = pathlib.Path(args.annotations_dir)
    target_dir = annotations_dir.parent / pathlib.Path(
        annotations_dir.name + "_visualized")
    target_dir.mkdir(exist_ok=True)

    # send to workers
    ray.get([
        visualize_page.remote(page_annotation, page_img_fp, target_dir)
        for page_annotation, page_img_fp in page_iterator(
            annotations_dir=pathlib.Path(args.annotations_dir),
            subset_size=args.subset_size
        )
    ])


if __name__ == '__main__':
    main()
