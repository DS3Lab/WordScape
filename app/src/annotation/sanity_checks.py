import math
from typing import Dict, Tuple, Set

from src.exceptions import *

ASPECT_RATIO_TOL = 1e-2


def pages_aspect_ratios(
        page_dims_pdf_parser: Dict[str, Tuple[int, int]],
        page_dims_renderings: Dict[str, Tuple[int, int]]
):
    r""" checks that the aspect ratios of the pages in the PDF file are
    consistent with the aspect ratios of the pages in the rendered page images.

    @param page_dims_pdf_parser: dictionary mapping page_ids to tuples
        containing the width and height of the page
    @param page_dims_renderings: dictionary mapping page_ids to tuples
        containing the width and height of the page

    @raises InconsistentAspectRatiosError: if the aspect ratios are not
        consistent
    """
    for pg_key in page_dims_pdf_parser.keys():
        # compute aspect ratios
        aspect_ratio_pdf = \
            page_dims_pdf_parser[pg_key][0] / page_dims_pdf_parser[pg_key][1]
        aspect_ratio_renderings = \
            page_dims_renderings[pg_key][0] / page_dims_renderings[pg_key][1]

        if not math.isclose(
                aspect_ratio_renderings, aspect_ratio_pdf,
                rel_tol=ASPECT_RATIO_TOL
        ):
            raise InconsistentAspectRatiosError(
                aspect_ratio_pdf, aspect_ratio_renderings
            )


def page_counts_consistency(
        pages_from_entity_detection: Set,
        pages_from_pdf_parser: Set
):
    r""" checks that the page numberings are consistent between the entity
    detection and the pdf parser.

    @param pages_from_entity_detection: dictionary mapping page numbers to
        dictionaries mapping entity ids to lists of bounding boxes
    @param pages_from_pdf_parser: dictionary mapping page numbers to lists of
        words

    @raises InconsistentPageCountError: if the page numberings are inconsistent
    """
    if pages_from_entity_detection != pages_from_pdf_parser:
        raise InconsistentPageCountError(
            expected=pages_from_entity_detection,
            actual=pages_from_pdf_parser
        )
