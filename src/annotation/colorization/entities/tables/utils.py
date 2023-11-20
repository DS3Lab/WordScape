from dataclasses import dataclass
from typing import Union

from docx.oxml import OxmlElement, CT_Row
from docx.oxml.ns import qn
from lxml import etree

from src.annotation.colorization.entities.tables import styles

__all__ = [
    'fill_border_style',
    'fill_shd_style',
    'shade_element',
    'check_if_header_row',
    'get_cell_location',
    'convert_table_borders_to_cell_borders'
]


def shade_element(prop, color_hex, val=None):
    r""" Apply shading to an element """
    color_hex = color_hex.replace('#', '').upper()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex)
    shd.set(qn("w:color"), color_hex)
    shd.set(qn("w:val"), val or "clear")
    prop.append(shd)


def fill_border_style(
        borders: styles.TableCellBorders,
        new_borders: Union[styles.TableCellBorders, styles.TableBorders]
) -> styles.TableCellBorders:
    r"""Overwrite the border style of a cell with the style of a new border
    where attributes are not yet defined. For each border type (top, left,
    bottom, right, insideH, insideV, tl2br, tr2bl) the new border style is
    applied for attributes that are not defined in the current border style.

    @param borders: The current border style of the cell
    @param new_borders: The new border style to be applied

    @return: The border style of the cell after applying the new border style
    """
    # iterate over all borders of the cell (top, left, bottom, right,
    # insideH, insideV, tl2br, tr2bl)
    for _border in new_borders.__slots__:
        new_borders_attrs = getattr(new_borders, _border)
        borders_attrs = getattr(borders, _border)

        # iterate over all border attributes (val, sz, space, color)
        # of the current border and overwrite if it is None
        for _attr in borders_attrs.__slots__:
            if getattr(borders_attrs, _attr) is not None:
                continue
            setattr(borders_attrs, _attr, getattr(new_borders_attrs, _attr))

    return borders


def fill_shd_style(
        shd: styles.ShdAttributes, new_shd: styles.ShdAttributes
) -> styles.ShdAttributes:
    r"""Overwrite the shading style of a cell with the style of a new shading
    where attributes are not yet defined (i.e., set to None).

    @param shd: The current shading style of the cell
    @param new_shd: The new shading style to be applied

    @return: The shading style of the cell after applying the new shading style
    """
    for s in new_shd.__slots__:
        if getattr(shd, s) is not None:
            continue
        setattr(shd, s, getattr(new_shd, s))
    return shd


def check_if_header_row(row: CT_Row) -> bool:
    r""" Check if a row is a header row.

    Note: A row is a header row if the `w:tblHeader` element is present in the
        `w:trPr` element and its `w:val` attribute is either omitted or  set to
        `true` or `on` or `1`.

    @param row: The row to check

    @return: True if the row is a header row, False otherwise
    """
    if row.trPr is None:
        return False

    tr_pr_etree = etree.fromstring(row.trPr.xml)
    header_elem = tr_pr_etree.find(qn('w:tblHeader'))

    if header_elem is None:
        return False

    # if val attribute is omitted, we fallback to the default value `true`
    header_val = header_elem.attrib.get(qn("w:val"), "true")

    return str(header_val).lower() in ["true", "on", "1"]


# Cell locations
@dataclass
class CellLocation:
    TOP_RIGHT = 'top_right'
    TOP_LEFT = 'top_left'
    BOTTOM_RIGHT = 'bottom_right'
    BOTTOM_LEFT = 'bottom_left'
    TOP = 'top'
    BOTTOM = 'bottom'
    LEFT = 'left'
    RIGHT = 'right'
    CENTER = 'center'

    valid_locations = (
        TOP_RIGHT, TOP_LEFT, BOTTOM_RIGHT, BOTTOM_LEFT, TOP, BOTTOM, LEFT,
        RIGHT, CENTER
    )


def get_cell_location(
        cell_num, row_num, total_cells_in_row, total_rows_in_table
):
    if cell_num == 0 and row_num == 0:
        return CellLocation.TOP_LEFT
    elif cell_num == total_cells_in_row - 1 and row_num == 0:
        return CellLocation.TOP_RIGHT
    elif cell_num == 0 and row_num == total_rows_in_table - 1:
        return CellLocation.BOTTOM_LEFT
    elif cell_num == total_cells_in_row - 1 and row_num == total_rows_in_table - 1:
        return CellLocation.BOTTOM_RIGHT
    elif cell_num == 0:
        return CellLocation.LEFT
    elif cell_num == total_cells_in_row - 1:
        return CellLocation.RIGHT
    elif row_num == 0:
        return CellLocation.TOP
    elif row_num == total_rows_in_table - 1:
        return CellLocation.BOTTOM
    else:
        return CellLocation.CENTER


def convert_table_borders_to_cell_borders(
        cell_loc: str, tbl_borders: styles.TableBorders
) -> styles.TableBorders:
    if cell_loc == CellLocation.CENTER:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.insideV,
            bottom=tbl_borders.insideH,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.TOP:
        return styles.TableBorders(
            top=tbl_borders.top,
            left=tbl_borders.insideV,
            bottom=tbl_borders.insideH,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.BOTTOM:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.insideV,
            bottom=tbl_borders.bottom,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.LEFT:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.left,
            bottom=tbl_borders.insideH,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.RIGHT:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.insideV,
            bottom=tbl_borders.insideH,
            right=tbl_borders.right,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.TOP_LEFT:
        return styles.TableBorders(
            top=tbl_borders.top,
            left=tbl_borders.left,
            bottom=tbl_borders.insideH,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.TOP_RIGHT:
        return styles.TableBorders(
            top=tbl_borders.top,
            left=tbl_borders.insideV,
            bottom=tbl_borders.insideH,
            right=tbl_borders.right,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.BOTTOM_LEFT:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.left,
            bottom=tbl_borders.bottom,
            right=tbl_borders.insideV,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    elif cell_loc == CellLocation.BOTTOM_RIGHT:
        return styles.TableBorders(
            top=tbl_borders.insideH,
            left=tbl_borders.insideV,
            bottom=tbl_borders.bottom,
            right=tbl_borders.right,
            insideH=styles.BorderAttributes.init_zero(),
            insideV=styles.BorderAttributes.init_zero(),
        )
    else:
        raise ValueError(
            f'Invalid cell location: {CellLocation.valid_locations}'
        )
