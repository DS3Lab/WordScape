from typing import Dict, List, Tuple

import settings.entities as entity_settings
import settings.annotation as annotation_settings
from src.annotation.colorization import ColorizationDecision

__all__ = [
    "calc_annotation_quality_score"
]

IGNORE_ENTITY_IDS = [
    entity_settings.ENTITY_TABLE_ROW_ID,
    entity_settings.ENTITY_TABLE_CELL_ID,
    entity_settings.ENTITY_TABLE_COLUMN_ID
]


def calc_annotation_quality_score(
        colorization_decisions: List[ColorizationDecision],
        entity_counts: Dict[int, int],
) -> Tuple[float, Dict[int, float]]:
    r""" Calculate the annotation quality score for a document

    @param colorization_decisions: the colorization decisions for a document;
        this is a list of ColorizationDecision objects with the attributes:
        - text (str): the text of the element
        - decision_source (str): the source of the decision
        - entity_decision (int): the id of the entity category
    @param entity_counts: dictionary with the number of entities for each
        entity category

    @return: the annotation quality score for the document, and the proportion
        of builtin characters for each entity
    """
    # count the number of characters for each entity
    char_counter = {
        k: {'builtin': 0, 'heuristic': 0}
        for k in entity_settings.ALL_ENTITY_IDS
    }

    for col_decision in colorization_decisions:
        category_id = col_decision.entity_decision

        if col_decision.text is None:
            # we assign text length 1 to entity categories that do not have
            # text (this only concerns tables and figures which are always
            # builtins)
            text_len = 1.0
        else:
            text_len = len(col_decision.text)

        if col_decision.decision_source in annotation_settings.BUILTIN_SOURCES:
            char_counter[category_id]['builtin'] += text_len
        else:
            char_counter[category_id]['heuristic'] += text_len

    # compute proportion of builtin characters for each entity
    builtin_props = dict.fromkeys(entity_settings.ALL_ENTITY_IDS, 0.0)

    for cat_id, char_counts in char_counter.items():
        total_chars = char_counts['builtin'] + char_counts['heuristic']

        if total_chars == 0:
            prop = 0.0
        else:
            prop = char_counts['builtin'] / total_chars

        builtin_props[cat_id] = prop

    # compute final score
    num_entities = sum(entity_counts.values())

    if num_entities == 0:
        return 0.0, builtin_props

    quality_score = 0.0
    for entity_id, count in entity_counts.items():
        if entity_id not in IGNORE_ENTITY_IDS:
            quality_score += count * builtin_props[entity_id]

    quality_score /= num_entities

    return quality_score, builtin_props
