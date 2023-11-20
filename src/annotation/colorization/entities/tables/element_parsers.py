import dataclasses
from typing import Dict, Type

from docx.oxml.ns import qn
from lxml import etree

from src.annotation.colorization.entities.tables import styles

__all__ = [
    'parse_borders_element',
    'parse_ref_conditional_styles',
    'parse_shd_element',
    'parse_tc_borders_element',
    'parse_tc_pr_element',
    'parse_tbl_borders_element',
    'parse_tbl_pr_element',
    'parse_tbl_look_element'
]


def parse_ref_conditional_styles(
        style_etree: etree._Element
) -> styles.ConditionalStyles:
    conditional_styles = styles.ConditionalStyles.init_zero()

    if style_etree is None:
        return conditional_styles

    for tbl_style_pr in style_etree.iterfind(qn('w:tblStylePr')) or []:
        # get region (=type) where conditional formatting is applied
        _type = tbl_style_pr.attrib.get(qn('w:type'))

        # get table cell properties
        tc_pr_elem = tbl_style_pr.find(qn('w:tcPr'))
        tc_pr_obj = parse_tc_pr_element(tc_pr_elem)

        # get table properties
        tbl_pr_elem = tbl_style_pr.find(qn('w:tblPr'))
        tbl_pr_obj = parse_tbl_pr_element(tbl_pr_elem)

        # create TableStyleProperty object
        tbl_style_pr_obj = styles.TableStyleProperty(
            type=_type, table_property=tbl_pr_obj,
            table_cell_property=tc_pr_obj
        )

        setattr(conditional_styles, _type, tbl_style_pr_obj)

    return conditional_styles


def parse_tc_pr_element(
        tc_pr: etree._Element
) -> styles.TableCellProperty:
    if tc_pr is None:
        return styles.TableCellProperty.init_zero()

    # borders
    tc_borders_elem = tc_pr.find(qn('w:tcBorders'))
    tc_borders_obj = parse_tc_borders_element(tc_borders_elem)

    # shading
    tc_shd_elem = tc_pr.find(qn('w:shd'))
    tc_shd_obj = parse_shd_element(shd_elem=tc_shd_elem)

    return styles.TableCellProperty(
        tc_borders=tc_borders_obj, tc_shd=tc_shd_obj
    )


def parse_tbl_pr_element(
        tbl_pr: etree._Element
) -> styles.TableProperty:
    if tbl_pr is None:
        return styles.TableProperty.init_zero()

    # borders
    tbl_borders_elem = tbl_pr.find(qn('w:tblBorders'))
    tbl_borders_obj = parse_tbl_borders_element(tbl_borders_elem)

    # shading
    tbl_shd_elem = tbl_pr.find(qn('w:shd'))
    tbl_shd_obj = parse_shd_element(shd_elem=tbl_shd_elem)

    return styles.TableProperty(
        tbl_borders=tbl_borders_obj, tbl_shd=tbl_shd_obj
    )


def parse_tbl_borders_element(
        tbl_borders_elem: etree._Element
) -> styles.TableBorders:
    if tbl_borders_elem is None:
        return styles.TableBorders.init_zero()

    tbl_border_attrs = parse_borders_element(tbl_borders_elem)

    return styles.TableBorders(**{
        f.name: tbl_border_attrs.get(
            f.name, styles.BorderAttributes.init_zero()
        )
        for f in dataclasses.fields(styles.TableBorders)
    })


def parse_tc_borders_element(
        tc_borders_elem: etree._Element
) -> styles.TableCellBorders:
    if tc_borders_elem is None:
        return styles.TableCellBorders.init_zero()

    tc_border_attrs = parse_borders_element(tc_borders_elem)

    return styles.TableCellBorders(**{
        f.name: tc_border_attrs.get(
            f.name, styles.BorderAttributes.init_zero()
        )
        for f in dataclasses.fields(styles.TableCellBorders)
    })


def parse_borders_element(
        borders_elem: etree._Element
) -> Dict[str, styles.BorderAttributes]:
    borders_dict = {}

    for border in borders_elem.iterchildren():
        # build border attributes
        border_attrs = styles.BorderAttributes(
            **{
                f.name: border.attrib.get(qn(f"w:{f.name}"))
                for f in dataclasses.fields(styles.BorderAttributes)
            }
        )

        border_name = etree.QName(border).localname
        borders_dict[border_name] = border_attrs

    return borders_dict


def parse_shd_element(
        shd_elem: etree._Element
) -> styles.ShdAttributes:
    return _parse_element(shd_elem, styles.ShdAttributes)


def parse_tbl_look_element(
        tbl_look_elem: etree._Element
) -> styles.TableLookAttributes:
    return _parse_element(tbl_look_elem, styles.TableLookAttributes)


def _parse_element(
        elem: etree._Element,
        style_obj: Type[styles.AttributesBaseType]
) -> styles.AttributesBaseType:
    if elem is None:
        return style_obj.init_zero()

    return style_obj(**{
        f.name: elem.attrib.get(qn(f"w:{f.name}"))
        for f in dataclasses.fields(style_obj)
    })
