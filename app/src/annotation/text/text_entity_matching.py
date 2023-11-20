import itertools
from typing import Dict, List

from src.annotation.utils.bbox_utils import area_of_overlap
from src.annotation.annotation_objects import Entity, Word, BoundingBox


def assign_entities_to_words(
        pages_entities: Dict[str, Dict[int, List[Entity]]],
        pages_words: Dict[str, List[Word]],
        threshold: float
) -> Dict[str, List[Word]]:
    r""" Assigns entities to words based on on whether the word bounding
    box is overlapping with the entity bounding box by at least the threshold.

    @param pages_entities: dictionary with page_ids as keys and dictionary of
        entities as value. The dictionary of entities is indexed by entity
        category and contains a list of entity objects.
    @param pages_words: dictionary with page_ids as keys and list of words as
        value.
    @param threshold: threshold for overlap between word and entity bounding
        boxes.

    @return: dictionary with page_ids as keys and list of words as value.
    """
    for page_id in pages_words.keys():
        words = pages_words[page_id]
        entities = pages_entities[page_id]
        for word in words:
            # find candidate entities for word
            candidate_entities = list(itertools.chain(*[
                _find_candidate_entities(
                    word=word, entities=entity_lst, threshold=threshold
                ) for entity_lst in entities.values()
            ]))

            # assign candidate entities to word
            for entity in candidate_entities:
                word.entity_ids.append(entity.id)
                word.entity_categories.append(entity.entity_category)

    return pages_words


def _find_candidate_entities(
        word: Word, entities: List[Entity], threshold: float
) -> List[Entity]:
    r"""Finds candidate entities for a word based on whether the word bounding
    box is overlapping with the entity bounding box by at least threshold.

    @param word: word object to find candidate entities for
    @param entities: list of entity objects
    @param threshold: threshold for overlap

    @return: list of candidate entities
    """
    return list(filter(
        lambda e: is_contained_in(word.bbox, e.bbox, threshold=threshold),
        entities
    ))


def is_contained_in(
        bbox1: BoundingBox, bbox2: BoundingBox, threshold: float
) -> bool:
    r""" Checks whether bbox1 is contained in bbox2 by at least the threshold.

    @param bbox1: first bounding box
    @param bbox2: second bounding box
    @param threshold: threshold for overlap

    @return: True if the two bounding boxes are overlapping by at least the
        threshold, False otherwise
    """
    if bbox1.area <= 0:
        return False

    overlap = area_of_overlap(bbox1, bbox2)
    ratio = overlap / bbox1.area

    return ratio >= threshold
