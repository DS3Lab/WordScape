from docx.document import Document as DocxDocument
from lxml import etree
from typing import Union

from src.exceptions import UnknownPageCountException


def get_page_count(doc: DocxDocument) -> Union[int, None]:
    r""" Get page count from docx file.

    @param doc: docx document

    @return: page count or None if not found
    """
    for part in doc._part.package.iter_parts():
        if part.partname.endswith("app.xml"):
            app_etree = etree.fromstring(part._blob)
            break
    else:
        raise UnknownPageCountException("app.xml not found")

    # get pages from app.xml
    for child in app_etree:
        if child.tag.endswith("Pages"):
            if child.text is None:
                break
            pages = int(child.text)
            return pages

    raise UnknownPageCountException("`Pages` tag not found")
