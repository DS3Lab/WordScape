import cv2
import numpy as np
from docx.document import Document as DocxDocument
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from typing import Tuple


def rgb_to_hex(rgb_color: Tuple[int, int, int]) -> str:
    r"""convert rgb colors to hex

    @param rgb_color: a tuple of 3 values (r, g, b)

    @return: a hex string
    """
    rgb_color = tuple(int(c) % 256 for c in np.squeeze(rgb_color))

    if len(rgb_color) != 3:
        raise ValueError(
            "rgb color must consist of 3 positive numbers! "
            "got {}".format(len(rgb_color))
        )

    return "#%02x%02x%02x" % rgb_color


def hsv_to_rgb(hsv_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    r"""convert hsv colors to rgb

    @param hsv_color: a tuple of 3 values (h, s, v)

    @return: a tuple of 3 values (r, g, b)
    """
    hsv_color_uint8 = np.uint8(hsv_color)

    # TODO: remove this ambiguity: in the future only a tuple of 3 values is
    #  accepted
    if len(hsv_color_uint8.shape) == 1:
        hsv_color_uint8 = np.expand_dims(hsv_color_uint8, axis=[0, 1])
    elif len(hsv_color_uint8.shape) == 2:
        hsv_color_uint8 = np.expand_dims(hsv_color_uint8, axis=0)
    else:
        raise ValueError(
            "! Warning: hsv color has shape {}; this function "
            "excpects hsv_color to be a tuple of 3 values".format(
                hsv_color_uint8.shape)
        )

    return tuple(
        cv2.cvtColor(hsv_color_uint8, cv2.COLOR_HSV2RGB)
        .squeeze()
        .astype(int)
        .tolist()
    )


def hsv_to_bgr(hsv_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    r"""convert hsv colors to bgr

    @param hsv_color: a tuple of 3 values (h, s, v)

    @return: a tuple of 3 values (r, g, b)
    """
    hsv_color_uint8 = np.uint8(hsv_color)

    # TODO: remove this ambiguity: in the future only a tuple of 3 values is
    #  accepted
    if len(hsv_color_uint8.shape) == 1:
        hsv_color_uint8 = np.expand_dims(hsv_color_uint8, axis=[0, 1])
    elif len(hsv_color_uint8.shape) == 2:
        hsv_color_uint8 = np.expand_dims(hsv_color_uint8, axis=0)
    else:
        raise ValueError(
            "! Warning: hsv color has shape {}; this function "
            "excpects hsv_color to be a tuple of 3 values".format(
                hsv_color_uint8.shape)
        )

    return tuple(
        cv2.cvtColor(hsv_color_uint8, cv2.COLOR_HSV2BGR)
        .squeeze()
        .astype(int)
        .tolist()
    )


def sanitize_figure_settings(document: DocxDocument):
    r"""
    Removing all child entries of the `a:blip xml` element
    ensures that all figures are loaded as-is with no rendering mods,
    enabling our figure-detection method to work

    @param document: the document to sanitize
    """
    fig_blip_elements = document.element.body.xpath(".//pic:blipFill//a:blip")
    # delete the child elements of this
    for blip_wrapper in fig_blip_elements:
        for img_mod_child in blip_wrapper.getchildren():
            blip_wrapper.remove(img_mod_child)


def shade_element(prop, color_hex):
    r""" Apply shading to an element """
    color_hex = color_hex.replace('#', '').upper()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex)
    prop.append(shd)


def check_if_par_is_numbered(par: Paragraph) -> bool:
    r"""
    Check if a par is numbered, which we assume to indicate a list.

    @param par: the paragraph to check

    @return: True if the paragraph is numbered, False otherwise
    """

    # a list style (even within a normal paragraph!) means numbering has
    # occured.
    par_xml_numbering = par._p.xpath(".//w:pPr//w:numPr")

    if len(par_xml_numbering) > 0:
        return True

    return False
