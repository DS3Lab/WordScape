from docx.document import Document
from docx.oxml import CT_Tbl, CT_P
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.table import Table
import pathlib
import pdfplumber
from typing import Dict, List, Tuple, Union

from src.annotation.annotation_objects import Word, BoundingBox
from src.annotation.utils.identifiers import get_page_id

__all__ = ["extract_text_from_docx", "extract_text_pdf_plumber"]


def extract_text_pdf_plumber(
        pdf_fp: Union[str, pathlib.Path], doc_id: str
) -> Tuple[Dict[str, List[Word]], Dict[str, Tuple[int, int]]]:
    r"""Extract text from a pdf using pdfplumber.

    @param pdf_fp: path to pdf
    @param doc_id: document id

    @return: tuple of dictionary with page_id as key and list of Word instances
        as value, dictionary with page_id as key and tuple of page width and
        page height as value.
    """

    def _convert_pdfplumber_to_bbox(
            x0: float, x1: float, top: float, bottom: float, **kwargs
    ) -> BoundingBox:
        r""" converts word coordinates extracted by pdfplumber to bounding box

        @param x0: distance from left edge of page to left side of word
        @param x1: distance from left edge of page to right side of word
        @param top: distance from top edge of page to top side of word
        @param bottom: distance from top edge of page to bottom side of word

        @return: bounding box in (x, y, width, height) format
        """
        return BoundingBox(x=x0, y=top, width=x1 - x0, height=bottom - top)

    doc_words_per_page = {}
    page_dimensions = {}

    with pdfplumber.open(pdf_fp) as pdf:
        for page in pdf.pages:
            # get page id
            page_id = get_page_id(doc_id, page.page_number)

            # Returns a version of the page with duplicate chars removed (i.e,
            # those sharing the same text, fontname, size, and positioning
            # within tolerance x/y as other characters. See the following issue
            # for details: https://github.com/jsvine/pdfplumber/issues/71
            page = page.dedupe_chars(tolerance=1)

            # store page dimensions
            page_dimensions[page_id] = (page.width, page.height)

            # extract all words from page
            words_on_page = page.extract_words(
                split_at_punctuation=False, use_text_flow=True
            )

            # create word object for page; note that we set the annotation_id
            # and entity_id to None, since we do not have this information at
            # this stage. This information will be obtained during the post-
            # processing step of the entities/bounding boxes
            doc_words_per_page[page_id] = [
                Word(
                    doc_id=doc_id,
                    entity_ids=[],
                    entity_categories=[],
                    page_num=page.page_number,
                    bbox=_convert_pdfplumber_to_bbox(**word),
                    text=word["text"],
                    upright=word["upright"],
                    direction=word["direction"]
                ) for word in words_on_page
            ]

    return doc_words_per_page, page_dimensions


def extract_text_from_docx(doc: Document) -> str:
    r""" Extract text from a docx file. This function extracts text from
    paragraphs and tables. The tables are serialized by concatenating the
    text of each cell with a tab character. The rows are serialized by
    concatenating the text of each row with a newline character.

    @param doc: docx document

    @return: text extracted from docx document
    """

    def _serializer(_doc):
        for element in _doc.element.body:
            elem_serialized = _serialize(element, _doc)
            if len(elem_serialized) > 0:
                yield elem_serialized

    return "\n".join(s for s in _serializer(doc))


def _serialize(element: OxmlElement, doc: Document):
    r""" Serialize a docx element.

    @param element: docx element
    @param doc: docx document

    @return: serialized docx element
    """
    if isinstance(element, CT_P):
        return Paragraph(element, doc).text
    elif isinstance(element, CT_Tbl):
        return _serialize_table(table=Table(element, doc))
    else:
        return ""


def _serialize_table(table: Table) -> str:
    r""" Serialize a table by concatenating the text of each cell with a tab
    character and rows with a newline character.

    @param table: docx table

    @return: serialized table
    """
    try:
        return "\n".join(
            "\t".join(cell.text for cell in row.cells)
            for row in table.rows
        )
    except IndexError:
        return ""
