import pathlib
from typing import Union
from docx.document import Document as DocxDocument

from src.annotation.colorization import (
    ColorizationHandler,
    ParagraphHeuristic,
    colorize_builtin_form_elements,
    colorize_builtin_toc_elements,
    colorize_figures,
    colorize_header_and_footer,
    colorize_paragraph,
    colorize_text_boxes,
    colorize_table
)
from src.annotation.config import AnnotationConfig
from src.annotation.utils.color_utils import sanitize_figure_settings

import settings.colors as color_settings


def colorize_word_doc(
        word_doc: DocxDocument,
        colorization_handler: ColorizationHandler,
        config: AnnotationConfig,
        temp_dir: Union[pathlib.Path, None] = None,
) -> DocxDocument:
    r""" Colorize a word document, and return the colorized document

    @param word_doc: the word document to colorize
    @param colorization_handler: the colorization handler to use for
        colorization
    @param config: the annotation config to use for colorization
    @param temp_dir: directory to use for storing temporary files

    @return: the colorized word document
    """
    # some elements do not have builtin styles, or styles we do not recognize.
    # For these cases, we build heuristics as a fallback option
    paragraph_heuristics = ParagraphHeuristic(word_doc, config)

    # sanitization step: change figure settings so that no preset styles are
    # applied which could change the color of figures
    sanitize_figure_settings(document=word_doc)

    # 1) colorize headers and footers
    colorize_header_and_footer(
        word_doc, colorization_handler=colorization_handler
    )

    # 2) colorize text boxes
    colorize_text_boxes(
        word_doc, hsv_color=color_settings.COLOR_TEXT,
        colorization_handler=colorization_handler
    )

    # 3) colorize tables
    for table in word_doc.tables:
        colorize_table(table, colorization_handler=colorization_handler)

    # 4) colorize paragraph elements
    for paragraph in word_doc.paragraphs:
        colorize_paragraph(
            paragraph,
            colorization_handler=colorization_handler,
            paragraph_heuristics=paragraph_heuristics
        )

    # 5) colorize table of contents elements
    # ! this has to be done before forms, due to XML overlaps
    colorize_builtin_toc_elements(
        word_doc, colorization_handler=colorization_handler
    )

    # 6) colorize built-in form elements
    # !this has to be done after regular colorization, because form fields may
    # !overlap with other entity types, therefore being overcolored if this is
    # !done first
    colorize_builtin_form_elements(
        word_doc, colorization_handler=colorization_handler
    )

    # 6) colorize figures
    word_doc = colorize_figures(
        word_doc, temp_dir=temp_dir, colorization_handler=colorization_handler
    )

    return word_doc
