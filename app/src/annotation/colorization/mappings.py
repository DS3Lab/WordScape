r"""
In order to nicely support headers, the heuristic mapping uses ints as values:
1 through 9 for known headers
-1 for unknown
special values for various builtins / other special properties

Here is also provided a mapping from builtins to constants that
work with the run-level mapping strategy.
"""

import settings

HEURISTIC_LEVEL_BODY = -10
HEURISTIC_LEVEL_TITLE = -20
HEURISTIC_LEVEL_LIST = -30

HEURISTIC_FONT_UNKNOWN = -1.0

CONSIDER_RUN_COLORING_FOR = [settings.colors.COLOR_TEXT]

# if style starts with one of the following names, it
# should map to that color
MAP_BUILTIN_TO_ENTITY_COLOR = {
    # BODY
    "body": settings.colors.COLOR_TEXT,
    "normal": settings.colors.COLOR_TEXT,
    "plain text": settings.colors.COLOR_TEXT,
    "no spacing": settings.colors.COLOR_TEXT,
    "default": settings.colors.COLOR_TEXT,

    # TITLE
    "title": settings.colors.COLOR_DOCUMENT_TITLE,

    # HEADINGS
    "heading 1": settings.colors.COLOR_SECTION_HEADING_1,
    "heading 2": settings.colors.COLOR_SECTION_HEADING_2,
    "heading 3": settings.colors.COLOR_SECTION_HEADING_3,
    "heading 4": settings.colors.COLOR_SECTION_HEADING_4,
    "heading 5": settings.colors.COLOR_SECTION_HEADING_5,
    "heading 6": settings.colors.COLOR_SECTION_HEADING_6,
    "heading 7": settings.colors.COLOR_SECTION_HEADING_7,
    "heading 8": settings.colors.COLOR_SECTION_HEADING_8,
    "heading 9": settings.colors.COLOR_SECTION_HEADING_9,

    # HEADERS AND FOOTERS
    "header": settings.colors.COLOR_HEADER,
    "footer": settings.colors.COLOR_FOOTER,

    # LIST
    "list": settings.colors.COLOR_LIST,

    # TOC
    "toc": settings.colors.COLOR_TOC,

    # BIBLIOGRAPHY
    "bibliography": settings.colors.COLOR_BIBLIOGRAPHY,

    # QUOTE
    "quote": settings.colors.COLOR_QUOTE,
    "intense quote": settings.colors.COLOR_QUOTE,

    # CAPTIONS
    "caption": settings.colors.COLOR_TABLE_CAPTIONS,

    # FOOTNOTES
    "footnote": settings.colors.COLOR_FOOTNOTE,

    # ANNOTATION
    "annotation": settings.colors.COLOR_ANNOTATION,
}
