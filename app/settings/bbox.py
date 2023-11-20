"""
This module contains all basic settings related to bounding boxes.
"""
import settings.entities as entities

# tolerance for bbox color detection
BBOX_COLOR_TOL = 1

# minimum size of bounding boxes (expressed as a fraction of page width and
# page height)
DEFAULT_FRACTION_NORMAL = 1e-2
DEFAULT_FRACTION_SMALL = 1e-3
DEFAULT_FRACTION_TINY = 5e-4

BBOX_MIN_FRACTIONS = {
    entities.ENTITY_TITLE_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_1_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_2_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_3_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_4_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_5_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_6_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_7_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_8_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADING_9_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TEXT_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_LIST_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_HEADER_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_FOOTER_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TABLE_HEADER_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TABLE_HEADER_CELL_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TABLE_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TABLE_CELL_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TABLE_CAPTION_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_TOC_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_BIBLIOGRAPHY_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_QUOTE_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_EQUATION_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_FIGURE_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_FOOTNOTE_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_ANNOTATION_ID: DEFAULT_FRACTION_NORMAL,
    entities.ENTITY_FORM_FIELD_ID: DEFAULT_FRACTION_TINY,
    entities.ENTITY_FORM_TAG_ID: DEFAULT_FRACTION_TINY,
}