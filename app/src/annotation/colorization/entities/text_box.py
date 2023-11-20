from docx.document import Document as _Document
from docx.text.paragraph import Paragraph
from typing import Tuple

from src.annotation.colorization import ColorizationHandler

import settings


def colorize_text_boxes(
        document: _Document,
        hsv_color: Tuple[int, int, int],
        colorization_handler: ColorizationHandler
):
    r"""
    Colorize all text boxes in the document.
    Currently, the basic assumption is that any text box near to a table
    or figure should be viewed as a caption; the only default behavior
    of word which creates text-boxes is when inserting captions.

    @param document: the document to colorize
    @param hsv_color: the color to use for text boxes in hsv color space
    @param colorization_handler: global tracker for colorization information
    """
    text_box_elements = document.element.body.xpath(".//w:txbxContent//w:p")
    for par_xml in text_box_elements:
        colorization_handler.assign_par_color(
            par=Paragraph(par_xml, document),
            base_color=hsv_color,
            decision_source=settings.annotation.ANNOTATION_XML_PATTERN
        )
