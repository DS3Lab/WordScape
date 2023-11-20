"""
This module contains functions for postprocessing bounding boxes detected via
the EntityDetector class, and bounding boxes for words extracted with
pdfplumber.
"""

from typing import List, Dict, Tuple

from src.annotation.annotation_objects import Entity, Word
from src.annotation.postprocessing import filters, table

import settings


def postprocess_words(
        pages_dims_img: Dict[str, Tuple[int, int]],
        pages_dims_pdf: Dict[str, Tuple[int, int]],
        pages_words: Dict[str, List[Word]]
) -> Dict[str, List[Word]]:
    r"""Postprocess text bounding boxes. This function applies the following
    postprocessing steps to the text bounding boxes:
        - normalize bounding boxes to page dimensions matching the image
            dimensions

    @param pages_dims_img: dictionary with page_ids as keys and page image
        dimensions as value
    @param pages_dims_pdf: dictionary with page_ids as keys and page pdf
        dimensions as value
    @param pages_words: dictionary with page_ids as keys and list of words
        as value

    @return: dictionary with page_ids as keys and list of words as value
    """
    page_keys = list(pages_dims_img.keys())
    pages_words_postprocessed = {}

    for pg_key in page_keys:
        # get page dimensions and bounding boxes
        page_width_img, page_height_img = pages_dims_img[pg_key]
        page_width_pdf, page_height_pdf = pages_dims_pdf[pg_key]
        single_page_words = pages_words[pg_key]

        # process bounding boxes for each word
        single_page_words_postprocessed = []
        for word in single_page_words:
            # 1) normalize word bounding boxes to page dimensions
            word.bbox.rescale(
                width_scale=page_width_img / page_width_pdf,
                height_scale=page_height_img / page_height_pdf
            )
            single_page_words_postprocessed.append(word)

        pages_words_postprocessed[pg_key] = single_page_words_postprocessed

    return pages_words_postprocessed


def postprocess_entities(
        pages_dims_img: Dict[str, Tuple[int, int]],
        pages_entities: Dict[str, Dict[int, List[Entity]]],
) -> Dict[str, Dict[int, List[Entity]]]:
    r"""Postprocess entities. This function runs the following postprocessing
    steps:
        - deduplication: discard duplicate entities (this is based on the
            string representation of the entity class instance)
        - size filter: discard entities which are too small

    @param pages_dims_img: dictionary with page_id as keys and
        dimensions for each image/page as value, extracted from the image
        representation of the document
    @param pages_entities: dictionary with page_id as keys and
        dictionaries as value. The inner dictionaries have entity ids as keys
        and a list of entity objects for detected entities as value

    @return: dictionary with page_id as keys and dictionaries as value.
        The inner dictionaries have entity ids as keys and a list of entity
        objects for detected entities as value; the bounding boxes are
        filtered according to the postprocessing filters.
    """
    page_ids = list(pages_dims_img.keys())
    pages_entities_post = {}

    for page_id in page_ids:
        # get page dimensions and bounding boxes
        page_width_img, page_height_img = pages_dims_img[page_id]
        single_page_entities = pages_entities[page_id]

        # process bounding boxes for each entity
        single_page_entities_post = {}
        for entity_category_id, entities in single_page_entities.items():
            if len(entities) == 0:
                continue

            # 1) deduplicate bounding boxes
            entities = filters.apply_deduplication_filter(entities=entities)

            # 2) discard entities which are too small
            entities = filters.apply_size_filter(
                entities=entities,
                page_width=page_width_img,
                page_height=page_height_img,
                entity_category_id=entity_category_id
            )

            single_page_entities_post[entity_category_id] = entities

        pages_entities_post[page_id] = single_page_entities_post

    return pages_entities_post


def postprocess_entities_content_based(
        pages_entities: Dict[str, Dict[int, List[Entity]]],
        pages_words: Dict[str, List[Word]]
) -> Dict[str, Dict[int, List[Entity]]]:
    for page_id in pages_entities.keys():
        # 1) dicsard all entities that do not contain any text
        pages_entities[page_id] = filters.apply_emptiness_filter(
            entities=pages_entities[page_id],
            words=pages_words[page_id]
        )

        # 2) trim bounding boxes so that they only span actual content
        pages_entities[page_id] = filters.apply_trimming_transform(
            entities=pages_entities[page_id],
            words=pages_words[page_id]
        )

    return pages_entities


def postprocess_tables(
        pages_entities: Dict[str, Dict[int, List[Entity]]], doc_id: str
):
    r""" This function infers table rows and table columns from the detected
     table cells.
     """
    for page_id in pages_entities.keys():
        entities = pages_entities[page_id]
        page_num = int(page_id.split("_p")[-1])

        # 1) infer table rows and columns
        table_entities = entities.get(
            settings.entities.ENTITY_TABLE_ID, []
        )
        table_cell_entities = entities.get(
            settings.entities.ENTITY_TABLE_CELL_ID, []
        )

        row_entities, column_entities = table.get_row_and_column_entities(
            table_entities=table_entities,
            table_cell_entities=table_cell_entities,
            doc_id=doc_id,
            page_id=page_id,
            page_num=page_num,
            is_header=False
        )

        if settings.entities.ENTITY_TABLE_ROW_ID not in entities.keys():
            entities[settings.entities.ENTITY_TABLE_ROW_ID] = []

        if settings.entities.ENTITY_TABLE_COLUMN_ID not in entities.keys():
            entities[settings.entities.ENTITY_TABLE_COLUMN_ID] = []

        for row in row_entities:
            entities[settings.entities.ENTITY_TABLE_ROW_ID].append(row)

        for column in column_entities:
            entities[settings.entities.ENTITY_TABLE_COLUMN_ID].append(column)

        # 2) infer table header rows
        tbl_hdr_cell_entities = entities.get(
            settings.entities.ENTITY_TABLE_HEADER_CELL_ID, []
        )
        header_row_entities, _ = table.get_row_and_column_entities(
            table_entities=table_entities,
            table_cell_entities=tbl_hdr_cell_entities,
            doc_id=doc_id,
            page_id=page_id,
            page_num=page_num,
            is_header=True
        )

    return pages_entities
