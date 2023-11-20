r"""
Module to get metadata that can be acquired when viewing the XML of a word
document
"""

from typing import List
from docx.document import Document


class OXMLMetadata:
    r"""
    Class for metadata not directly originating from annotation, but intrinsic
    to one document.
    """
    languages_autocorrect: List[str]
    template_name: str

    # !!! IMPORTANT INFO (also has category, subject, title, status)
    # https://python-docx.readthedocs.io/en/latest/api/document.html#coreproperties-objects
    core_category: str
    core_comments: str
    core_content_status: str
    core_created: str
    core_identifier: str
    core_keywords: str
    core_last_printed: str
    core_modified: str
    core_subject: str
    core_title: str
    core_version: str


def get_langs(doc: Document) -> List[str]:
    # get w:lang tags
    lang_tags = doc.element.body.xpath("//w:lang")
    lang_list = []
    for tag in lang_tags:
        for k, v in tag.items():
            lang_list.append(v)
    return list(set(lang_list))


def get_oxml_metadata(doc: Document) -> OXMLMetadata:
    data = OXMLMetadata()
    data.languages_autocorrect = get_langs(doc)

    core = doc.core_properties
    data.core_category = core.category
    data.core_comments = core.comments
    data.core_content_status = core.content_status
    data.core_created = core.created
    data.core_identifier = core.identifier
    data.core_keywords = core.keywords
    data.core_last_printed = core.last_printed
    data.core_modified = core.modified
    data.core_subject = core.subject
    data.core_title = core.title
    data.core_version = core.version

    return data
