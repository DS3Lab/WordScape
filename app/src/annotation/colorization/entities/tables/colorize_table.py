from docx.table import Table

import settings
from src.annotation.colorization import ColorizationHandler
from src.annotation.colorization.entities.tables import \
    TableColorizationHandler


def colorize_table(
        table: Table,
        colorization_handler: ColorizationHandler = None,
        base_color_table=settings.colors.COLOR_TABLE,
        base_color_table_header=settings.colors.COLOR_TABLE_HEADER,
        sat_val_step=settings.colors.SAT_VAL_STEP,
):
    ct_tbl_ref_style = getattr(table.style, "_element", None)

    # record table in the colorization decisions
    colorization_handler.update_colorization_decisions(
        text=None,
        decision_source=settings.annotation.ANNOTATION_BUILTIN,
        entity_decision=settings.entities.ENTITY_TABLE_ID
    )

    # initialize table colorization handler
    tbl_col_handler = TableColorizationHandler(
        ct_tbl=table._tbl, ct_tbl_ref_style=ct_tbl_ref_style,
        colorization_handler=colorization_handler,
        base_color_table=base_color_table,
        base_color_header=base_color_table_header,
        sat_val_step=sat_val_step
    )

    # colorize table
    tbl_col_handler.colorize_table()
