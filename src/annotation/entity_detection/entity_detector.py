from collections import defaultdict
import cv2
import numpy as np
from typing import List, Tuple, Dict

from src.annotation.annotation_objects import BoundingBox, Entity
from src.annotation.utils.bbox_utils import detect_contours
from src.annotation.colorization import ColorizationHandler
import settings


def _lower_bound_with_tol(h, s, v):
    tol = settings.bbox.BBOX_COLOR_TOL
    h_min = settings.colors.HUE_MIN
    s_min = settings.colors.SAT_MIN
    v_min = settings.colors.VAL_MIN
    return max(h_min, h - tol), max(s_min, s - tol), max(v_min, v - tol)


def _upper_bound_with_tol(h, s, v):
    tol = settings.bbox.BBOX_COLOR_TOL
    h_max = settings.colors.HUE_MAX
    s_max = settings.colors.SAT_MAX
    v_max = settings.colors.VAL_MAX
    return min(h_max, h + tol), min(s_max, s + tol), min(v_max, v + tol)


class EntityDetector:
    r""" Detects entities in an image by matching colors in the colorized image
    with the colors defined in settings.colors.ALL_COLORS. The detected
    entities are stored in the bounding_boxes attribute.
    """

    def __init__(
            self,
            doc_id: str,
            page_id: str,
            page_num: int,
            image_numpy: np.ndarray,
            colorization_handler: ColorizationHandler,
    ):
        self.doc_id = doc_id
        self.page_id = page_id
        self.page_num = page_num

        # load images
        self.image = image_numpy

        self.used_colors = colorization_handler.used_colors

        # mapping to identify detection handler: key = hue value of color. The
        # detection is implemented seperately for tables and table headers
        # (both detect both the main entity, and the individual cells). All
        # else is taken care of by the generic detection handler.
        hue_table = settings.colors.COLOR_TABLE[0]
        hue_table_header = settings.colors.COLOR_TABLE_HEADER[0]
        self.detection_handlers = {
            hue_table: self._detect_tables,
            hue_table_header: self._detect_table_headers,
        }

    def detect_entities(self) -> Dict[int, List[Entity]]:
        r""" Detects all entities in the source image by matching colors in the
        colorized image.

        Note: all detected bounding boxes are stored in the bounding_boxes
            attribute

        @return: Dictionary with entity_category_id as key and list of entity
            categories for detected entities as value
        """
        entities = defaultdict(list)

        # iterate over all colors, use corresponding detection handler
        def __get_handler(hsv_color_):
            return self.detection_handlers.get(
                hsv_color_[0], self._detect_generic
            )

        for handler, hsv_color in map(
                lambda hsv: (__get_handler(hsv), hsv),
                settings.colors.ALL_COLORS
        ):
            entities_from_handler = handler(hsv_color=hsv_color)
            entities.update(entities_from_handler)

        return entities

    def _detect_generic(
            self, hsv_color: Tuple[int, int, int]
    ) -> Dict[int, List[Entity]]:
        r""" Detects generic entities in the image.

        @param hsv_color: the color to detect
        @return: Dictionary with entity_category_id as key and list of entity
            objects for detected entities as value
        """
        entity_category_id = settings.colors.get_entity_category_id(hsv_color)

        entities = []
        for hsv_color in self.used_colors[str(hsv_color)]:
            # detect contours
            lowerb = _lower_bound_with_tol(*hsv_color)
            upperb = _upper_bound_with_tol(*hsv_color)
            contours, _ = detect_contours(self.image, lowerb, upperb)

            if len(contours) == 0:
                continue

            # construct bounding boxes
            entities.extend(map(
                lambda cont: Entity(
                    doc_id=self.doc_id,
                    page_id=self.page_id,
                    page_num=self.page_num,
                    entity_category=entity_category_id,
                    bbox=BoundingBox(*cv2.boundingRect(cont)),
                ), contours
            ))

        return {entity_category_id: entities}

    def _detect_tables(
            self, *args, **kwargs  # noqa
    ) -> Dict[int, List[Entity]]:
        r""" Detects tables and table cells in the image.

        @return: Dictionary with entity_category_id as key and list of entity
            objects for detected entities as value
        """
        entities = defaultdict(list)

        # detect contours for the entire table
        lowerb = _lower_bound_with_tol(
            h=settings.colors.COLOR_TABLE_HEADER[0],
            s=settings.colors.SAT_MIN,
            v=settings.colors.VAL_MIN
        )
        upperb = _upper_bound_with_tol(
            h=settings.colors.COLOR_TABLE[0],
            s=settings.colors.SAT_MAX,
            v=settings.colors.VAL_MAX
        )
        contours, hierarchy = detect_contours(self.image, lowerb, upperb)

        # there are no tables in the image if hierarchy is None
        if hierarchy is None:
            return entities

        # @Maurice TODO: double check why this logic is needed
        tables_bboxes = []
        for cont, hier in zip(contours, hierarchy[0]):
            if hier[3] != -1:
                continue
            tables_bboxes.append(BoundingBox(*cv2.boundingRect(cont)))

        # construct entities
        entity_category_id = settings.entities.ENTITY_TABLE_ID
        entities[entity_category_id].extend(map(
            lambda bbox: Entity(
                doc_id=self.doc_id,
                page_id=self.page_id,
                page_num=self.page_num,
                entity_category=entity_category_id,
                bbox=bbox,
            ), tables_bboxes
        ))

        # detect contours for table cells
        entity_category_id = settings.entities.ENTITY_TABLE_CELL_ID
        tbl_cell_colors = self.used_colors[str(settings.colors.COLOR_TABLE)]
        for hsv_color in tbl_cell_colors:
            lowerb = _lower_bound_with_tol(*hsv_color)
            upperb = _upper_bound_with_tol(*hsv_color)
            contours, _ = detect_contours(self.image, lowerb, upperb)

            if len(contours) == 0:
                continue

            # construct entities
            entities[entity_category_id].extend(map(
                lambda cnt: Entity(
                    doc_id=self.doc_id,
                    page_id=self.page_id,
                    page_num=self.page_num,
                    entity_category=entity_category_id,
                    bbox=BoundingBox(*cv2.boundingRect(cnt)),
                ), contours
            ))

        return entities

    def _detect_table_headers(
            self, *args, **kwargs  # noqa
    ) -> Dict[int, List[Entity]]:
        r""" Detects table headers and table header cells in the image.

        @return: Dictionary with entity_category_id as key and list of entity
            objects for detected entities as value
        """
        entities = defaultdict(list)

        # detect contours for the entire table
        lowerb = _lower_bound_with_tol(*settings.colors.COLOR_TABLE_HEADER)
        upperb = _upper_bound_with_tol(*settings.colors.COLOR_TABLE_HEADER)
        contours, hierarchy = detect_contours(self.image, lowerb, upperb)

        # there are no tables in the image if hierarchy is None
        if hierarchy is None:
            return entities

        # @Maurice TODO: double check this logic
        headers_bboxes = []
        for cont, hier in zip(contours, hierarchy[0]):
            if hier[3] != -1:
                continue
            headers_bboxes.append(BoundingBox(*cv2.boundingRect(cont)))

        # construct entities
        entity_category_id = settings.entities.ENTITY_TABLE_HEADER_ID
        entities[entity_category_id].extend(map(
            lambda bbox: Entity(
                doc_id=self.doc_id,
                page_id=self.page_id,
                page_num=self.page_num,
                entity_category=entity_category_id,
                bbox=bbox,
            ), headers_bboxes
        ))

        # detect contours for table header cells
        entity_category_id = settings.entities.ENTITY_TABLE_HEADER_CELL_ID
        hdr_colors = self.used_colors[str(settings.colors.COLOR_TABLE_HEADER)]
        for hsv_color in hdr_colors:
            lowerb = _lower_bound_with_tol(*hsv_color)
            upperb = _upper_bound_with_tol(*hsv_color)
            contours, _ = detect_contours(self.image, lowerb, upperb)

            if len(contours) == 0:
                continue

            # construct entities
            entities[entity_category_id].extend(map(
                lambda cnt: Entity(
                    doc_id=self.doc_id,
                    page_id=self.page_id,
                    page_num=self.page_num,
                    entity_category=entity_category_id,
                    bbox=BoundingBox(*cv2.boundingRect(cnt)),
                ), contours
            ))

        return entities
