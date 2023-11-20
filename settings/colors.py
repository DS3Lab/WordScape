"""
This module contains all basic settings related to entity colors.
"""
import ast

import settings.entities as entities

# colors are in hue saturation value (HSV) format, and we adopt opencv's
# convention: hue is in [0, 179], saturation and value are in [0, 255]
# !caution: any values outside of these ranges will lead to unexpected
# !behavior
GRANULARITY = 7

COLOR_WHITESPACE = (0, 0, 0)
COLOR_DOCUMENT_TITLE = (7, 255, 255)
COLOR_SECTION_HEADING_1 = (14, 255, 255)
COLOR_SECTION_HEADING_2 = (14, 235, 255)
COLOR_SECTION_HEADING_3 = (14, 215, 255)
COLOR_SECTION_HEADING_4 = (14, 195, 255)
COLOR_SECTION_HEADING_5 = (14, 175, 255)
COLOR_SECTION_HEADING_6 = (14, 155, 255)
COLOR_SECTION_HEADING_7 = (14, 135, 255)
COLOR_SECTION_HEADING_8 = (14, 115, 255)
COLOR_SECTION_HEADING_9 = (14, 95, 255)
COLOR_TEXT = (21, 255, 255)
COLOR_LIST = (28, 255, 255)
COLOR_HEADER = (35, 255, 255)
COLOR_FOOTER = (42, 255, 255)
# ! important: the header color must be followed by the table color!
COLOR_TABLE_HEADER = (49, 255, 255)
COLOR_TABLE = (56, 255, 255)
COLOR_TOC = (77, 255, 255)
COLOR_QUOTE = (84, 255, 255)
COLOR_EQUATION = (91, 255, 255)
COLOR_FIGURES = (98, 255, 255)
COLOR_TABLE_CAPTIONS = (105, 255, 255)
COLOR_FOOTNOTE = (117, 255, 255)
COLOR_ANNOTATION = (122, 255, 255)
COLOR_BIBLIOGRAPHY = (130, 255, 255)
COLOR_FORM_FIELD = (160, 255, 255)
COLOR_FORM_TAG = (167, 255, 255)

# map color --> entity string representation
# note use of str() as list is not hashable
COLOR_TO_ENTITY_CATEGORY_NAME = {
    str(COLOR_DOCUMENT_TITLE): entities.ENTITY_TITLE_NAME,
    str(COLOR_SECTION_HEADING_1): entities.ENTITY_HEADING_1_NAME,
    str(COLOR_SECTION_HEADING_2): entities.ENTITY_HEADING_2_NAME,
    str(COLOR_SECTION_HEADING_3): entities.ENTITY_HEADING_3_NAME,
    str(COLOR_SECTION_HEADING_4): entities.ENTITY_HEADING_4_NAME,
    str(COLOR_SECTION_HEADING_5): entities.ENTITY_HEADING_5_NAME,
    str(COLOR_SECTION_HEADING_6): entities.ENTITY_HEADING_6_NAME,
    str(COLOR_SECTION_HEADING_7): entities.ENTITY_HEADING_7_NAME,
    str(COLOR_SECTION_HEADING_8): entities.ENTITY_HEADING_8_NAME,
    str(COLOR_SECTION_HEADING_9): entities.ENTITY_HEADING_9_NAME,
    str(COLOR_TEXT): entities.ENTITY_TEXT_NAME,
    str(COLOR_LIST): entities.ENTITY_LIST_NAME,
    str(COLOR_HEADER): entities.ENTITY_HEADER_NAME,
    str(COLOR_FOOTER): entities.ENTITY_FOOTER_NAME,
    str(COLOR_TABLE_HEADER): entities.ENTITY_TABLE_HEADER_NAME,
    str(COLOR_TABLE): entities.ENTITY_TABLE_NAME,
    str(COLOR_TOC): entities.ENTITY_TOC_NAME,
    str(COLOR_BIBLIOGRAPHY): entities.ENTITY_BIBLIOGRAPHY_NAME,
    str(COLOR_QUOTE): entities.ENTITY_QUOTE_NAME,
    str(COLOR_EQUATION): entities.ENTITY_EQUATION_NAME,
    str(COLOR_FIGURES): entities.ENTITY_FIGURE_NAME,
    str(COLOR_TABLE_CAPTIONS): entities.ENTITY_TABLE_CAPTION_NAME,
    str(COLOR_FOOTNOTE): entities.ENTITY_FOOTNOTE_NAME,
    str(COLOR_ANNOTATION): entities.ENTITY_ANNOTATION_NAME,
    str(COLOR_FORM_FIELD): entities.ENTITY_FORM_FIELD_NAME,
    str(COLOR_FORM_TAG): entities.ENTITY_FORM_TAG_NAME,
}

COLOR_TO_ENTITY_CATEGORY_ID = {
    str(COLOR_DOCUMENT_TITLE): entities.ENTITY_TITLE_ID,
    str(COLOR_SECTION_HEADING_1): entities.ENTITY_HEADING_1_ID,
    str(COLOR_SECTION_HEADING_2): entities.ENTITY_HEADING_2_ID,
    str(COLOR_SECTION_HEADING_3): entities.ENTITY_HEADING_3_ID,
    str(COLOR_SECTION_HEADING_4): entities.ENTITY_HEADING_4_ID,
    str(COLOR_SECTION_HEADING_5): entities.ENTITY_HEADING_5_ID,
    str(COLOR_SECTION_HEADING_6): entities.ENTITY_HEADING_6_ID,
    str(COLOR_SECTION_HEADING_7): entities.ENTITY_HEADING_7_ID,
    str(COLOR_SECTION_HEADING_8): entities.ENTITY_HEADING_8_ID,
    str(COLOR_SECTION_HEADING_9): entities.ENTITY_HEADING_9_ID,
    str(COLOR_TEXT): entities.ENTITY_TEXT_ID,
    str(COLOR_LIST): entities.ENTITY_LIST_ID,
    str(COLOR_HEADER): entities.ENTITY_HEADER_ID,
    str(COLOR_FOOTER): entities.ENTITY_FOOTER_ID,
    str(COLOR_TABLE_HEADER): entities.ENTITY_TABLE_HEADER_ID,
    str(COLOR_TABLE): entities.ENTITY_TABLE_ID,
    str(COLOR_TOC): entities.ENTITY_TOC_ID,
    str(COLOR_BIBLIOGRAPHY): entities.ENTITY_BIBLIOGRAPHY_ID,
    str(COLOR_QUOTE): entities.ENTITY_QUOTE_ID,
    str(COLOR_EQUATION): entities.ENTITY_EQUATION_ID,
    str(COLOR_FIGURES): entities.ENTITY_FIGURE_ID,
    str(COLOR_TABLE_CAPTIONS): entities.ENTITY_TABLE_CAPTION_ID,
    str(COLOR_FOOTNOTE): entities.ENTITY_FOOTNOTE_ID,
    str(COLOR_ANNOTATION): entities.ENTITY_ANNOTATION_ID,
    str(COLOR_FORM_FIELD): entities.ENTITY_FORM_FIELD_ID,
    str(COLOR_FORM_TAG): entities.ENTITY_FORM_TAG_ID,
}

ENTITY_NAME_TO_COLOR = {
    v: ast.literal_eval(k) for k, v in COLOR_TO_ENTITY_CATEGORY_NAME.items()
}
ENTITY_NAME_TO_COLOR[entities.ENTITY_TABLE_CELL_NAME] = COLOR_TABLE
ENTITY_NAME_TO_COLOR[entities.ENTITY_TABLE_ROW_NAME] = COLOR_TABLE
ENTITY_NAME_TO_COLOR[entities.ENTITY_TABLE_COLUMN_NAME] = COLOR_TABLE
ENTITY_NAME_TO_COLOR[
    entities.ENTITY_TABLE_HEADER_CELL_NAME
] = COLOR_TABLE_HEADER
ENTITY_NAME_TO_COLOR[
    entities.ENTITY_TABLE_HEADER_ROW_NAME
] = COLOR_TABLE_HEADER

ENTITY_CATEGORY_ID_TO_COLOR = {
    v: ast.literal_eval(k) for k, v in COLOR_TO_ENTITY_CATEGORY_ID.items()
}
ENTITY_CATEGORY_ID_TO_COLOR[entities.ENTITY_TABLE_CELL_ID] = COLOR_TABLE
ENTITY_CATEGORY_ID_TO_COLOR[entities.ENTITY_TABLE_ROW_ID] = COLOR_TABLE
ENTITY_CATEGORY_ID_TO_COLOR[entities.ENTITY_TABLE_COLUMN_ID] = COLOR_TABLE
ENTITY_CATEGORY_ID_TO_COLOR[
    entities.ENTITY_TABLE_HEADER_CELL_ID
] = COLOR_TABLE_HEADER
ENTITY_CATEGORY_ID_TO_COLOR[
    entities.ENTITY_TABLE_HEADER_ROW_ID
] = COLOR_TABLE_HEADER


def get_entity_name(color) -> str:
    return COLOR_TO_ENTITY_CATEGORY_NAME.get(str(color))


def get_entity_category_id(color) -> int:
    return COLOR_TO_ENTITY_CATEGORY_ID.get(str(color))


# put all colors in a list
ALL_COLORS = [
    eval(color_var) for color_var in dir()
    if color_var.startswith("COLOR_") and isinstance(eval(color_var), tuple)
]

# and sort with increasing hue
ALL_COLORS.sort(key=lambda color: color[0])
ALL_COLORS.remove(COLOR_WHITESPACE)

# put heading colors in a list
COLORS_SECTION_HEADINGS = [
    COLOR_SECTION_HEADING_1,
    COLOR_SECTION_HEADING_2,
    COLOR_SECTION_HEADING_3,
    COLOR_SECTION_HEADING_4,
    COLOR_SECTION_HEADING_5,
    COLOR_SECTION_HEADING_6,
    COLOR_SECTION_HEADING_7,
    COLOR_SECTION_HEADING_8,
    COLOR_SECTION_HEADING_9,
]

# minimum saturation and value for colors
SAT_MIN = 50
SAT_MAX = 255
VAL_MIN = 50
VAL_MAX = 255
HUE_MIN = 0
HUE_MAX = 179
SAT_VAL_STEP = 2
NONTABLE_SAT_MIN = 200
NONTABLE_VAL_MIN = 200

ENTITIES_HUES_WITHOUT_CYCLING = [
    COLOR_DOCUMENT_TITLE[0],
    COLOR_SECTION_HEADING_1[0],
    COLOR_SECTION_HEADING_2[0],
    COLOR_SECTION_HEADING_3[0],
    COLOR_SECTION_HEADING_4[0],
    COLOR_SECTION_HEADING_5[0],
    COLOR_SECTION_HEADING_6[0],
    COLOR_SECTION_HEADING_7[0],
    COLOR_SECTION_HEADING_8[0],
    COLOR_SECTION_HEADING_9[0],
    COLOR_TEXT[0]
]

# run some checks
assert all(
    map(
        lambda x: (
                (HUE_MIN <= x[0] <= HUE_MAX) &
                (SAT_MIN <= x[1] <= SAT_MAX) &
                (VAL_MIN <= x[2] <= VAL_MAX)
        ), ALL_COLORS
    )
), "Some colors are not in the correct range! make sure all colors defined" \
   " in settings.colors are in hue saturation value (HSV) format. Note that" \
   " we adopt opencv's convention: hue is in [0, 179], saturation and value" \
   " are in [0, 255]."

assert COLOR_TABLE[0] - COLOR_TABLE_HEADER[0] == GRANULARITY, \
    "The table hue value must be {} units away from the" \
    " table header hue value!".format(GRANULARITY)
