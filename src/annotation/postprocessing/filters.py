from collections import defaultdict
from typing import List, Dict

import settings
from src.annotation.annotation_objects import Entity, Word, BoundingBox

__all__ = [
    "apply_size_filter",
    "apply_deduplication_filter",
    "apply_emptiness_filter",
    "apply_trimming_transform"
]

# these entity categories are allowed to be empty
ALLOWED_EMPTY_ENTITY_CATEGORY_IDS = [
    settings.entities.ENTITY_TABLE_ID,
    settings.entities.ENTITY_TABLE_ROW_ID,
    settings.entities.ENTITY_TABLE_COLUMN_ID,
    settings.entities.ENTITY_TABLE_HEADER_ROW_ID,
    settings.entities.ENTITY_TABLE_CELL_ID,
    settings.entities.ENTITY_TABLE_HEADER_ID,
    settings.entities.ENTITY_TABLE_HEADER_CELL_ID,
    settings.entities.ENTITY_FIGURE_ID,
    settings.entities.ENTITY_FORM_FIELD_ID
]

# these entity categories are excluded from trimming
EXCLUDE_ENTITIES_FROM_TRIMMING = [
    settings.entities.ENTITY_TABLE_ID,
    settings.entities.ENTITY_TABLE_CELL_ID,
    settings.entities.ENTITY_TABLE_ROW_ID,
    settings.entities.ENTITY_TABLE_COLUMN_ID,
    settings.entities.ENTITY_TABLE_HEADER_ID,
    settings.entities.ENTITY_TABLE_HEADER_CELL_ID,
    settings.entities.ENTITY_TABLE_HEADER_ROW_ID,
    settings.entities.ENTITY_FIGURE_ID,
    settings.entities.ENTITY_FORM_FIELD_ID
]


def apply_size_filter(
        entities: List[Entity],
        page_width: int,
        page_height: int,
        entity_category_id: int,
) -> List[Entity]:
    r""" Discards all bounding boxes that are smaller than the given minimum
    size.

    @param entities: list of entity objects
    @param page_width: width of the page
    @param page_height: height of the page
    @param entity_category_id: id of the entity category

    @returns: list of entitiy objects whose bounding boxes are larger than the
        corresponding minimum sizes
    """
    # determine minimal size of bounding boxes
    frac = settings.bbox.BBOX_MIN_FRACTIONS[entity_category_id]
    min_width = int(frac * page_width)
    min_height = int(frac * page_height)

    # min_size = int(frac * page_width * page_height)

    def _check_bbox_size(entity: Entity):
        """ determines whether the bounding box is large enough """
        _, _, w, h = entity.bbox.box
        return w >= min_width and h >= min_height

    return list(filter(_check_bbox_size, entities))


def apply_deduplication_filter(entities: List[Entity]) -> List[Entity]:
    r"""Discards all entities whose bounding boxes that are duplicates of other
    bounding boxes. Two bounding boxes are considered duplicates if they have
    the same hash which is based on the string representation of the bounding
    box class instance.

    @param entities: list of entity objects

    @returns: list of bounding boxes that are not duplicates
    """
    deduplicated_bounding_boxes = dict()

    for entity in entities:
        if entity.id not in deduplicated_bounding_boxes:
            deduplicated_bounding_boxes[entity.id] = entity

    return list(deduplicated_bounding_boxes.values())


def apply_emptiness_filter(
        entities: Dict[int, List[Entity]],
        words: List[Word]
) -> Dict[int, List[Entity]]:
    r"""Discards all entities that do not contain any words and that are not
    allowed to be empty (see ALLOWED_EMPTY_ENTITY_CATEGORY_IDS).

    @param entities: list of entity objects
    @param words: list of word objects representing words on the page

    @returns: list of entity objects that contain at least one word or that are
        allowed to be empty.
    """
    # collect ids of entities which contain at least one word
    entity_ids_with_words = set()
    for word in words:
        if word.entity_ids is not None:
            entity_ids_with_words.update(word.entity_ids)

    # remove all entities that do not contain any words
    for entity_category_id in entities.keys():
        if entity_category_id in ALLOWED_EMPTY_ENTITY_CATEGORY_IDS:
            continue

        entities[entity_category_id] = list(filter(
            lambda entity: entity.id in entity_ids_with_words,
            entities[entity_category_id]
        ))

    return entities


def apply_trimming_transform(
        entities: Dict[int, List[Entity]],
        words: List[Word]
) -> Dict[int, List[Entity]]:
    r"""Trims the bounding boxes of all entities to the smallest bounding box
    that contains all words of the entity.

    @param entities: list of entity objects to be trimmed
    @param words: list of word objects representing words on the page

    @returns: list of entity objects whose bounding boxes have been trimmed
    """
    # collect word bounding boxes for each entity id
    bounding_boxes_per_entity_id = defaultdict(list)
    for word in words:
        for entity_id in word.entity_ids:
            bounding_boxes_per_entity_id[entity_id].append(word.bbox)

    for entity_category_id, entities_lst in entities.items():
        if entity_category_id in EXCLUDE_ENTITIES_FROM_TRIMMING:
            continue

        entities[entity_category_id] = list(map(
            lambda entity: _trim_entity(
                entity, bounding_boxes_per_entity_id[entity.id]
            ),
            entities_lst
        ))

    return entities


def _trim_entity(
        entity: Entity, words_bounding_boxes: List[BoundingBox]
) -> Entity:
    r"""Trims the bounding box of the given entity to the smallest bounding box
    that contains all words of the entity.

    @param entity: entity object to be trimmed
    @param words_bounding_boxes: list of bounding boxes of words belonging to
        the entity

    @returns: entity object whose bounding box has been trimmed
    """
    # get upper left corner of smallest bounding box containing all words
    x = int(
        min(_x for _x, _, _, _ in map(lambda b: b.box, words_bounding_boxes))
    )
    y = int(
        min(_y for _, _y, _, _ in map(lambda b: b.box, words_bounding_boxes))
    )

    # get width and height of smallest bounding box containing all words
    w = int(max(
        _x + _w for _x, _, _w, _ in map(lambda b: b.box, words_bounding_boxes)
    ) - x)

    h = int(max(
        _y + _h for _, _y, _, _h in map(lambda b: b.box, words_bounding_boxes)
    ) - y)

    # update bounding box of entity
    entity.bbox = BoundingBox(x, y, w, h)

    return entity
