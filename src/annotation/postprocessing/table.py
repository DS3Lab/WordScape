import math
from typing import List, Tuple

from src.annotation.utils.bbox_utils import is_contained_in
from src.annotation.annotation_objects import BoundingBox, Entity
import settings

CELL_CLOSENESS_TOLERANCE = 5

__all__ = ["get_row_and_column_entities"]


def get_row_and_column_entities(
        table_entities: List[Entity],
        table_cell_entities: List[Entity],
        doc_id: str,
        page_id: str,
        page_num: int,
        is_header: bool = False,
) -> Tuple[List[Entity], List[Entity]]:
    """function determines the rows of the tables contained in the bounding
    boxes from `tables_bboxes`.

    Each bbox is a rectangle given by a tuple (x, y, w, h) corresponding to the
    coordinates of the upper-right corner (x, y), its width w and its height h.

    !note: all bounding  boxes are assumed to be on the same page.

    @tables_bboxes: list of bboxes around tables.
    @tables_cells_bboxes: list of bboxes around cells in the tables.
    """
    if len(table_entities) == 0 or len(table_cell_entities) == 0:
        return list(), list()

    # assign cell bboxes to table bboxes
    tables = list()

    for table in table_entities:
        table_cells_bboxes = list()
        for cell in table_cell_entities:
            if is_contained_in(cell.bbox, table.bbox):
                table_cells_bboxes.append(cell.bbox)
        tables.append(table_cells_bboxes)

    # sort cell bboxes in each table bbox as rows
    row_entities = list()
    column_entities = list()

    for table_cells in filter(lambda t: len(t) > 0, tables):
        # 1) group cells into rows
        row_bboxes = _get_table_rows_from_cells(table_cells)
        if is_header:
            row_cat = settings.entities.ENTITY_TABLE_HEADER_ROW_ID
        else:
            row_cat = settings.entities.ENTITY_TABLE_ROW_ID

        for row_bbx in row_bboxes:
            row_entities.append(
                Entity(
                    bbox=row_bbx,
                    doc_id=doc_id,
                    page_id=page_id,
                    page_num=page_num,
                    entity_category=row_cat,
                )
            )

        if is_header:
            # we dont need to infer columns for header rows
            continue

        # 2) group cells into columns
        col_bboxes = _get_table_columns_from_cells(table_cells)
        for col_bbx in col_bboxes:
            column_entities.append(
                Entity(
                    bbox=col_bbx,
                    doc_id=doc_id,
                    page_id=page_id,
                    page_num=page_num,
                    entity_category=settings.entities.
                    ENTITY_TABLE_COLUMN_ID,
                )
            )

    return row_entities, column_entities


def _get_table_rows_from_cells(cells: List[BoundingBox]) -> List[BoundingBox]:
    if len(cells) == 0:
        return list()

    # 1) group cells into raw rows
    rows_grouped = _group_rows_raw(cells)

    # 2) extend rows to include merged cells
    rows_extended = _extend_rows(rows_grouped, cells)

    return rows_extended


def _get_table_columns_from_cells(
        cells: List[BoundingBox]
) -> List[BoundingBox]:
    if len(cells) == 0:
        return list()

    # 1) group cells into raw columns
    columns_grouped = _group_columns_raw(cells)

    # 2) extend columns to include merged cells
    columns_extended = _extend_columns(columns_grouped, cells)

    return columns_extended


def _extend_rows(
        rows: List[List[BoundingBox]], cells: List[BoundingBox]
) -> List[BoundingBox]:
    r""" This function adds merged cells to each row, which cover the row in
    height. """

    extended_rows = list()
    tol = CELL_CLOSENESS_TOLERANCE / 2

    for row in rows:
        y = max(row, key=lambda c: c.y).y
        h = min(row, key=lambda c: c.height).height

        row_cells_covering = list(filter(
            lambda c: c.y <= y + tol and c.y + c.height >= y + h - tol, cells
        ))

        end_cell = max(row_cells_covering, key=lambda c: c.x + c.width)
        start_cell = min(row_cells_covering, key=lambda c: c.x)
        x = start_cell.x
        w = end_cell.x + end_cell.width - x

        extended_rows.append(BoundingBox(x=x, y=y, width=w, height=h))

    return extended_rows


def _extend_columns(
        columns: List[List[BoundingBox]], cells: List[BoundingBox]
) -> List[BoundingBox]:
    extended_columns = list()

    tol = CELL_CLOSENESS_TOLERANCE / 2

    for col in columns:
        x = max(col, key=lambda c: c.x).x
        w = min(col, key=lambda c: c.width).width

        col_cells_covering = list(filter(
            lambda c: c.x <= x + tol and c.x + c.width >= x + w - tol, cells
        ))

        end_cell = max(col_cells_covering, key=lambda c: c.y + c.height)
        start_cell = min(col_cells_covering, key=lambda c: c.y)
        y = start_cell.y
        h = end_cell.y + end_cell.height - y

        extended_columns.append(BoundingBox(x=x, y=y, width=w, height=h))

    return extended_columns


def _group_rows_raw(cells: List[BoundingBox]):
    if len(cells) == 0:
        return list()

    # extract unique y values
    unique_y = set(c.y for c in cells)

    # group unique y values into rows with tolerance for close values
    rows = list()
    for y in unique_y:
        rows.append(list(filter(
            lambda c: math.isclose(c.y, y, abs_tol=CELL_CLOSENESS_TOLERANCE),
            cells
        )))

    return rows


def _group_columns_raw(cells: List[BoundingBox]):
    if len(cells) == 0:
        return list()

    # extract unique x values
    unique_x = set(c.x for c in cells)

    # group unique x values into columns with tolerance for close values
    columns = list()
    for x in unique_x:
        columns.append(list(filter(
            lambda c: math.isclose(c.x, x, abs_tol=CELL_CLOSENESS_TOLERANCE),
            cells
        )))

    return columns
