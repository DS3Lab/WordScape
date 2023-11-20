import cv2
import math
import numpy as np
from typing import Tuple, List

from src.annotation.annotation_objects import BoundingBox


def area_of_overlap(
        bbox1: BoundingBox,
        bbox2: BoundingBox
) -> float:
    r"""calculates the area of overlap between two bounding boxes

    @param bbox1: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the first bounding box
    @param bbox2: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the second bounding box

    returns: a float indicating the area of intersection between the two
        bounding boxes
    """
    x1, y1, w1, h1 = bbox1.box
    x2, y2, w2, h2 = bbox2.box

    # determine coordinates of intersection triangle
    x_left = max(x1, x2)
    x_right = min(x1 + w1, x2 + w2)
    y_top = max(y1, y2)
    y_bottom = min(y1 + h1, y2 + h2)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    return intersection_area


def euclidean_distance(
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
) -> float:
    r"""calculates the euclidean distance between two bounding boxes

    @param bbox1: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the first bounding box
    @param bbox2: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the second bounding box

    returns: a float indicating the euclidean distance between the two
        bounding boxes
    """

    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2

    left = x1 + w1 < x2
    right = x2 + w2 < x1
    bottom = y2 + h2 < y1
    top = y1 + h1 < y2

    if top and left:
        return math.dist([x1 + w1, y1 + h1], [x2, y2])
    elif left and bottom:
        return math.dist([x1 + w1, y1], [x2, y2 + h2])
    elif bottom and right:
        return math.dist([x1, y1], [x2 + w2, y2 + h2])
    elif right and top:
        return math.dist([x1, y1 + h1], [x2 + w2, y2])
    elif left:
        return x2 - (x1 + w1)
    elif right:
        return x1 - (x2 + w2)
    elif bottom:
        return y1 - (y2 + h2)
    elif top:
        return y2 - (y1 + h1)
    else:  # rectangles intersect
        return 0.


def is_contained_in(
        bbox1: BoundingBox,
        bbox2: BoundingBox,
) -> bool:
    r"""determines whether bbox1 is contained in bbox2

    @param bbox1: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the first bounding box
    @param bbox2: tuple of floats (x, y, w, h) indicating top-left corner
        (x, y), height h, and width w of the second bounding box

    @return: True if bbox1 is contained in bbox2, False otherwise
    """
    # determine the area of the first bounding box
    _, _, w1, h1 = bbox1.box
    area_bbox1 = w1 * h1

    intersection_area = area_of_overlap(bbox1, bbox2)

    # bbox1 is contained in bbox2 if the area of intersection is equal to the
    # area of bbox 1
    return math.isclose(intersection_area, area_bbox1)


def detect_contours(
        image: np.array,
        lowerb: Tuple[int, int, int],
        upperb: Tuple[int, int, int]
) -> Tuple[List, List]:
    r""" utility function: detects contours in the image for values that fall
    in the range lowerb, upperb.

    @param image: image where contours are detected
    @param lowerb: lower bound of the range
    @param upperb: upper bound of the range

    @return: a tuple of two lists: the first list contains the contours, the
        second list contains the hierarchy
    """
    # create mask where values are in range
    mask = cv2.inRange(image, lowerb=lowerb, upperb=upperb)

    # get contours in mask
    contours, hierarchy = cv2.findContours(
        mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    return contours, hierarchy
