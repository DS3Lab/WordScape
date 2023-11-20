import dataclasses

from typing import TypeVar

AttributesBaseType = TypeVar("AttributesBaseType", bound="AttributesBase")


@dataclasses.dataclass
class AttributesBase:
    r""" Base class for all attributes classes. """

    def __post_init__(self):
        # check that all values are in valid ranges
        for field in dataclasses.fields(self):
            val_range = getattr(self, f"__{field.name}_vals__")
            val = getattr(self, field.name)

            if val_range is None or val is None:
                continue

            assert field.type(getattr(self, field.name)) in val_range, \
                f"Invalid value for {field.name}: {getattr(self, field.name)}"

        # check that color attributed is a valid hex value (without leading #)
        color = getattr(self, "color", None)
        if color is not None:
            assert len(color) == 6 or color == "auto", \
                f"Invalid color value: {color}"

    @classmethod
    def init_zero(cls):
        return cls(**{k: None for k in cls.__slots__})


@dataclasses.dataclass
class BorderAttributes(AttributesBase):
    r""" Attributes of a table or cell border; note that rows cannot define a
     border.

    Reference for table row border attributes:
        http://officeopenxml.com/WPtableBorders.php

    Reference for table cell border attributes:
        http://officeopenxml.com/WPtableCellProperties-Borders.php

    """

    # Color of the border. Values are given as hex values (in  RRGGBB format).
    # No #, unlike hex values in HTML/CSS.
    color: str
    __color_vals__ = None

    # Specifies the spacing offset. Values are specified in points (1/72nd of
    # an inch).
    space: int
    __space_vals__ = None

    # Specifies the width of the border. Table borders are line borders (see
    # the val attribute below), and so the width is specified in eighths of a
    # point, with a minimum value of two (1/4 of a point) and a maximum value
    # of 96 (twelve points).
    sz: int
    __sz_vals__ = range(0, 97)

    # Specifies the style of the border. Table borders can be only line
    # borders.
    val: str
    __val_vals__ = [
        "single", "dashDotStroked", "dashed", "dashSmallGap", "dotDash",
        "dotDotDash", "dotted", "double", "doubleWave", "inset", "nil", "none",
        "outset", "thick", "thickThinLargeGap", "thickThinMediumGap",
        "thickThinSmallGap", "thinThickLargeGap", "thinThickMediumGap",
        "thinThickSmallGap", "thinThickThinLargeGap", "thinThickThinMediumGap",
        "thinThickThinSmallGap", "threeDEmboss", "threeDEngrave", "triple",
        "wave"
    ]

    # Specifies whether the border should be modified to create the appearance
    # of a shadow. For right and bottom borders, this is done by duplicating
    # the border below and right of the normal location. For the right and top
    # borders, this is done by moving the border down and to the right of the
    # original location. Permitted values are true and false.
    shadow: str
    __shadow_vals__ = [None, "true", "false"]

    __slots__ = ("color", "space", "sz", "val", "shadow")


@dataclasses.dataclass
class ShdAttributes(AttributesBase):
    r""" Attributes of table or cell shading

    Reference for table row shd attributes:
        http://officeopenxml.com/WPtableShading.php

    Reference for table cell shd attributes:
        http://officeopenxml.com/WPtableCellProperties-Shading.php

    """

    # Specifies the color to be used for any foreground pattern specified with
    # the4 val attribute. Values are given as hex values (in RRGGBB format). No
    # is included, unlike hex values in HTML/CSS. E.g., fill="FFFF00". A value
    # of auto is possible, enabling the consuming software to determine the
    # value.
    color: str
    __color_vals__ = None

    # Specifies the pattern to be used to lay the pattern color over the
    # background color. For example, w:val="pct10" indicates that the border
    # style is a 10 percent foreground fill mask.
    val: str
    __val_vals__ = [
        "clear", "diagCross", "diagStripe", "horzCross", "horzStripe", "nil",
        "pct10", "pct12", "pct15", "pct20", "pct25", "pct30", "pct35", "pct37",
        "pct40", "pct45", "pct5", "pct50", "pct55", "pct60", "pct62", "pct65",
        "pct70", "pct75", "pct80", "pct85", "pct87", "pct90", "pct95", "solid",
        "reverseDiagStripe", "thinDiagCross", "thinDiagStripe",
        "thinHorzCross", "thinHorzStripe", "thinReverseDiagStripe",
        "thinVertStripe", "vertStripe",
    ]

    # Specifies the color to be used for the background. Values are given as
    # hex values (i.e., in RRGGBB format). No # in included, unlike hex values
    # in HTML/CSS. E.g., fill="FFFF00". A value of auto is possible, enabling
    # the consuming software to determine the value. A value of auto is
    # possible, enabling the consuming software to determine the value.
    fill: str
    __fill_vals__ = None

    __slots__ = ("color", "val", "fill")


@dataclasses.dataclass
class TableLookAttributes(AttributesBase):
    r""" Attributes of table look which defines how conditional formatting is
    applied to a table.

    Note: Tables can be conditionally formatted based on such things as whether
        the content is in the first row, last row, first column, or last
        column, or whether the rows or columns are to be banded (i.e.,
        formatting based on how the previous row or column was formatted). Such
        conditional formatting for tables is defined in the referenced style
        for the table.

    Reference: http://officeopenxml.com/WPtblLook.php

    """
    # Specifies that the first row conditional formatting should be applied.
    firstRow: str
    __firstRow_vals__ = [None, "true", "false", "0", "1"]

    # Specifies that the first column conditional formatting should be applied.
    firstColumn: str
    __firstColumn_vals__ = [None, "true", "false", "0", "1"]

    # Specifies that the last row conditional formatting should be applied.
    lastRow: str
    __lastRow_vals__ = [None, "true", "false", "0", "1"]

    # Specifies that the last column conditional formatting should be applied.
    lastColumn: str
    __lastColumn_vals__ = [None, "true", "false", "0", "1"]

    # Specifies that the horizontal banding conditional formatting should not
    # be applied.
    noHBand: str
    __noHBand_vals__ = [None, "true", "false", "0", "1"]

    # Specifies that the vertical banding conditional formatting should not be
    # applied.
    noVBand: str
    __noVBand_vals__ = [None, "true", "false", "0", "1"]

    # standard 2003 compatibility
    val: str
    __val_vals__ = None

    __slots__ = ("firstRow", "firstColumn", "lastRow", "lastColumn", "noHBand",
                 "noVBand", "val")

    positive_attrs = ("firstRow", "firstColumn", "lastRow", "lastColumn")
    negative_attrs = ("noHBand", "noVBand")

    def __post_init__(self):
        # determine if conditional styling is used
        self.use_conditional_styling = any(
            getattr(self, attr) in ["true", "1"]
            for attr in self.positive_attrs
        ) or any(
            getattr(self, attr) in ["false", "0"]
            for attr in self.negative_attrs
        )


@dataclasses.dataclass
class TableStyleColBandSize(AttributesBase):
    r""" Attributes of table style column band size which defines how many
    subsequent columns are to be formatted the same way.
    
    Note: This element is applicable to a <tblPr> within a table style. Table
        styles can have conditional formatting which enables columns and/or 
        rows to be "banded" by applying different formatting to alternating 
        columns or rows. This element can be used to group columns so that 
        alternating groups of columns are formatted the same way rather than 
        every other column. For example, by setting the value of the val 
        attribute to 3, the first three columns will be formatted the same, and
        the second group of three will be formatted the same, and each group of
        three thereafter will alternate their formatting.
        
    Reference: http://officeopenxml.com/WPtableProperties.php
    
    """
    val: int
    __val_vals__ = None

    __slots__ = ("val",)


@dataclasses.dataclass
class TableStyleRowBandSize(AttributesBase):
    r""" Attributes of table style row band size which defines how many
    subsequent rows are to be formatted the same way.

    Note: This element is applicable to a <tblPr> within a table style. Table
        styles can have conditional formatting which enables columns and/or
        rows to be "banded" by applying different formatting to alternating
        columns or rows. This element can be used to group rows so that
        alternating groups of rows are formatted the same way rather than
        every other row. For example, by setting the value of the val
        attribute to 3, the first three rows will be formatted the same, and
        the second group of three will be formatted the same, and each group of
        three thereafter will alternate their formatting.

    Reference: http://officeopenxml.com/WPtableProperties.php
    """
    val: int
    __val_vals__ = None

    __slots__ = ("val",)


@dataclasses.dataclass
class CnfStyle(AttributesBase):
    r""" Attributes of conditional formatting style which defines how
    conditional formatting is applied to a table element; note that this can be
    applied to a paragraph in a table, a row, or a cell.

    Reference: https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.conditionalformatstyle?view=openxml-2.8.1

    """
    val: str
    __val_vals__ = None

    firstRow: str
    __firstRow_vals__ = [None, "true", "false", "0", "1"]

    lastRow: str
    __lastRow_vals__ = [None, "true", "false", "0", "1"]

    firstColumn: str
    __firstColumn_vals__ = [None, "true", "false", "0", "1"]

    lastColumn: str
    __lastColumn_vals__ = [None, "true", "false", "0", "1"]

    oddVBand: str
    __oddVBand_vals__ = [None, "true", "false", "0", "1"]

    evenVBand: str
    __evenVBand_vals__ = [None, "true", "false", "0", "1"]

    oddHBand: str
    __oddHBand_vals__ = [None, "true", "false", "0", "1"]

    evenHBand: str
    __evenHBand_vals__ = [None, "true", "false", "0", "1"]

    firstRowFirstColumn: str
    __firstRowFirstColumn_vals__ = [None, "true", "false", "0", "1"]

    firstRowLastColumn: str
    __firstRowLastColumn_vals__ = [None, "true", "false", "0", "1"]

    lastRowFirstColumn: str
    __lastRowFirstColumn_vals__ = [None, "true", "false", "0", "1"]

    lastRowLastColumn: str
    __lastRowLastColumn_vals__ = [None, "true", "false", "0", "1"]

    __slots__ = ("val", "firstRow", "lastRow", "firstColumn", "lastColumn",
                 "oddVBand", "evenVBand", "oddHBand", "evenHBand",
                 "firstRowFirstColumn", "firstRowLastColumn",
                 "lastRowFirstColumn", "lastRowLastColumn")

    def __post_init__(self):
        self.parse_val()

    def parse_val(self):
        if self.val is None:
            return

        assert isinstance(self.val, str)
        assert len(self.val) == len(self.__slots__) - 1

        for v, field in zip(self.val, self.__slots__[1:]):
            if getattr(self, field) is None:
                setattr(self, field, v)


@dataclasses.dataclass
class TableBorders:
    top: BorderAttributes
    left: BorderAttributes
    bottom: BorderAttributes
    right: BorderAttributes
    insideH: BorderAttributes
    insideV: BorderAttributes

    __slots__ = ("top", "left", "bottom", "right", "insideH", "insideV")

    @classmethod
    def init_zero(cls):
        return cls(**{k: BorderAttributes.init_zero() for k in cls.__slots__})


@dataclasses.dataclass
class TableCellBorders:
    top: BorderAttributes
    left: BorderAttributes
    bottom: BorderAttributes
    right: BorderAttributes
    insideH: BorderAttributes
    insideV: BorderAttributes
    tl2br: BorderAttributes
    tr2bl: BorderAttributes

    __slots__ = ("top", "left", "bottom", "right", "insideH", "insideV",
                 "tl2br", "tr2bl")

    @classmethod
    def init_zero(cls):
        return cls(**{k: BorderAttributes.init_zero() for k in cls.__slots__})


@dataclasses.dataclass
class TableProperty:
    tbl_borders: TableBorders
    tbl_shd: ShdAttributes

    @classmethod
    def init_zero(cls):
        return cls(
            tbl_borders=TableBorders.init_zero(),
            tbl_shd=ShdAttributes.init_zero()
        )


@dataclasses.dataclass
class TableCellProperty:
    tc_borders: TableCellBorders
    tc_shd: ShdAttributes

    @classmethod
    def init_zero(cls):
        return cls(
            tc_borders=TableCellBorders.init_zero(),
            tc_shd=ShdAttributes.init_zero()
        )


@dataclasses.dataclass
class TableStyleProperty:
    type: str
    table_property: TableProperty
    table_cell_property: TableCellProperty

    @classmethod
    def init_zero(cls, _type: str):
        return cls(
            type=_type,
            table_property=TableProperty.init_zero(),
            table_cell_property=TableCellProperty.init_zero()
        )


@dataclasses.dataclass
class ConditionalStyles:
    # The formatting applies to the first row
    firstRow: TableStyleProperty

    # The formatting applies to the last row
    lastRow: TableStyleProperty

    # The formatting applies to the first column
    firstCol: TableStyleProperty

    # The formatting applies to the last column
    lastCol: TableStyleProperty

    # The formatting applies to odd numbered groupings of columns
    band1Vert: TableStyleProperty

    # The formatting applies to even numbered groupings of columns
    band2Vert: TableStyleProperty

    # The formatting applies to odd numbered groupings of rows
    band1Horz: TableStyleProperty

    # The formatting applies to even numbered groupings of rows
    band2Horz: TableStyleProperty

    # The formatting applies to the top right cell
    neCell: TableStyleProperty

    # The formatting applies to the top left cell
    nwCell: TableStyleProperty

    # The formatting applies to the bottom right cell
    seCell: TableStyleProperty

    # The formatting applies to the bottom left cell
    swCell: TableStyleProperty

    __slots__ = ("firstRow", "lastRow", "firstCol", "lastCol", "band1Vert",
                 "band2Vert", "band1Horz", "band2Horz", "neCell", "nwCell",
                 "seCell", "swCell")

    @classmethod
    def init_zero(cls):
        return cls(**{
            k: TableStyleProperty.init_zero(_type=k) for k in cls.__slots__
        })
