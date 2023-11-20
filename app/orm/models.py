from typing import List
from sqlalchemy import (
    String, DateTime, Column, ARRAY, Integer, JSON, Float
)
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class SourcesRecordDB(Base):
    """ dataclass for storing a single record for the sources relation """
    __tablename__ = "sources_record"

    url: str = Column(String(10000), nullable=False)
    url_hash: str = Column(String(1000), primary_key=True)
    crawl_id: str = Column(String(1000), nullable=False)
    shard_id: str = Column(String(1000), nullable=False)
    filename: str = Column(String(10000), nullable=True)
    bytehash: str = Column(String(10000), nullable=True)

    # http header fields
    status_code: str = Column(String(200), nullable=True)
    content_type: str = Column(String(1000), nullable=True)
    content_length: str = Column(String(1000), nullable=True)
    content_encoding: str = Column(String(1000), nullable=True)
    content_language: List[str] = Column(ARRAY(String), nullable=True)
    last_modified: datetime = Column(DateTime, nullable=True)
    source_filename: str = Column(String(10000), nullable=True)

    # oletools fields
    olet_ftype: str = Column(String(200), nullable=True)
    olet_container: str = Column(String(200), nullable=True)
    olet_appname: str = Column(String(200), nullable=True)
    olet_codepage: str = Column(String(200), nullable=True)
    olet_encrypted: str = Column(String(200), nullable=True)
    olet_vba: str = Column(String(400), nullable=True)
    olet_xlm: str = Column(String(400), nullable=True)
    olet_ext_rels: str = Column(String(200), nullable=True)
    olet_ObjectPool: str = Column(String(200), nullable=True)
    olet_flash: str = Column(String(200), nullable=True)
    olet_python_codec: str = Column(String(200), nullable=True)
    olet_pass: bool = Column(String(200), nullable=True)

    timestamp: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    exception: str = Column(String(1000), nullable=True)


class DocMetadataRecordDB(Base):
    __tablename__ = "doc_metadata_record"

    # same as in sources record DB
    # doc_id: str = Column(String(10000), primary_key=True)
    url_hash: str = Column(String(1000), nullable=False)
    crawl_id: str = Column(String(1000), nullable=False)
    sources_shard_id: str = Column(String(1000), nullable=False)
    annotated_shard_id: str = Column(String(1000), nullable=False)

    num_pages: int = Column(Integer, nullable=False)
    sources_filename: str = Column(String(10000), nullable=False)

    # ! added later through join
    url: str = Column(String(10000), nullable=False, primary_key=True)
    filename: str = Column(String(10000), nullable=True)

    # text metrics
    word_count: int = Column(Integer, nullable=False)
    char_count: int = Column(Integer, nullable=False)
    alph_chars_count: int = Column(Integer, nullable=False)
    numeric_chars_count: int = Column(Integer, nullable=False)
    alphnum_chars_count: int = Column(Integer, nullable=False)
    alnum_prop: float = Column(Float, nullable=False)
    alph_to_num_ratio: float = Column(Float, nullable=False)
    languages_fasttext: dict = Column(JSON, nullable=True)
    languages_autocorrect: List[str] = Column(ARRAY(String), nullable=True)
    top_lang: str = Column(String(1000), nullable=True)
    top_lang_score: float = Column(Float, nullable=True)

    # annotation metadata
    num_title: int = Column(Integer, nullable=False)
    num_heading_1: int = Column(Integer, nullable=False)
    num_heading_2: int = Column(Integer, nullable=False)
    num_heading_3: int = Column(Integer, nullable=False)
    num_heading_4: int = Column(Integer, nullable=False)
    num_heading_5: int = Column(Integer, nullable=False)
    num_heading_6: int = Column(Integer, nullable=False)
    num_heading_7: int = Column(Integer, nullable=False)
    num_heading_8: int = Column(Integer, nullable=False)
    num_heading_9: int = Column(Integer, nullable=False)
    num_text: int = Column(Integer, nullable=False)
    num_list: int = Column(Integer, nullable=False)
    num_header: int = Column(Integer, nullable=False)
    num_footer: int = Column(Integer, nullable=False)
    num_table_header: int = Column(Integer, nullable=False)
    num_table_header_cell: int = Column(Integer, nullable=False)
    num_table: int = Column(Integer, nullable=False)
    num_table_cell: int = Column(Integer, nullable=False)
    num_toc: int = Column(Integer, nullable=False)
    num_bibliography: int = Column(Integer, nullable=False)
    num_quote: int = Column(Integer, nullable=False)
    num_equation: int = Column(Integer, nullable=False)
    num_figure: int = Column(Integer, nullable=False)
    num_table_caption: int = Column(Integer, nullable=False)
    num_footnote: int = Column(Integer, nullable=False)
    num_annotation: int = Column(Integer, nullable=False)
    num_form_field: int = Column(Integer, nullable=False)
    num_form_tag: int = Column(Integer, nullable=False)
    num_table_row: int = Column(Integer, nullable=False)
    num_table_column: int = Column(Integer, nullable=False)
    num_table_header_row: int = Column(Integer, nullable=False)

    # quality metrics
    annotation_quality_score: str = Column(String(1000), nullable=False)
    builtin_proportion_per_entity: dict = Column(JSON, nullable=False)
    annotation_sources: dict = Column(JSON, nullable=False)
    template_name: str = Column(String(1000), nullable=True)

    # python-docx core props
    core_category: str = Column(String(1000), nullable=True)
    core_comments: str = Column(String(1000), nullable=True)
    core_content_status: str = Column(String(1000), nullable=True)
    core_created: datetime = Column(DateTime, nullable=True)
    core_identifier: str = Column(String(1000), nullable=True)
    core_keywords: str = Column(String(1000), nullable=True)
    core_last_printed: datetime = Column(DateTime, nullable=True)
    core_modified: datetime = Column(DateTime, nullable=True)
    core_subject: str = Column(String(1000), nullable=True)
    core_title: str = Column(String(1000), nullable=True)
    core_version: str = Column(String(1000), nullable=True)


class PageMetadataRecordDB(Base):
    __tablename__ = "page_metadata_record"

    # same as in sources record DB
    page_id: str = Column(String(10000), primary_key=True)
    url: str = Column(String(10000), nullable=False, primary_key=True)
    url_hash: str = Column(String(1000), nullable=False)
    crawl_id: str = Column(String(1000), nullable=False)
    sources_shard_id: str = Column(String(1000), nullable=False)
    annotated_shard_id: str = Column(String(1000), nullable=False)

    filename: str = Column(String(10000), nullable=False)

    # text features
    pdf_word_count: int = Column(Integer, nullable=False)
    languages_fasttext: dict = Column(JSON, nullable=True)
    top_lang: str = Column(String(1000), nullable=True)
    top_lang_score: float = Column(Float, nullable=True)

    # geometry
    page_height: float = Column(Float, nullable=False)
    page_width: float = Column(Float, nullable=False)
    page_number: int = Column(Integer, nullable=False)

    # annotation metadata
    num_title: int = Column(Integer, nullable=False)
    num_heading_1: int = Column(Integer, nullable=False)
    num_heading_2: int = Column(Integer, nullable=False)
    num_heading_3: int = Column(Integer, nullable=False)
    num_heading_4: int = Column(Integer, nullable=False)
    num_heading_5: int = Column(Integer, nullable=False)
    num_heading_6: int = Column(Integer, nullable=False)
    num_heading_7: int = Column(Integer, nullable=False)
    num_heading_8: int = Column(Integer, nullable=False)
    num_heading_9: int = Column(Integer, nullable=False)
    num_text: int = Column(Integer, nullable=False)
    num_list: int = Column(Integer, nullable=False)
    num_header: int = Column(Integer, nullable=False)
    num_footer: int = Column(Integer, nullable=False)
    num_table_header: int = Column(Integer, nullable=False)
    num_table_header_cell: int = Column(Integer, nullable=False)
    num_table: int = Column(Integer, nullable=False)
    num_table_cell: int = Column(Integer, nullable=False)
    num_toc: int = Column(Integer, nullable=False)
    num_bibliography: int = Column(Integer, nullable=False)
    num_quote: int = Column(Integer, nullable=False)
    num_equation: int = Column(Integer, nullable=False)
    num_figure: int = Column(Integer, nullable=False)
    num_table_caption: int = Column(Integer, nullable=False)
    num_footnote: int = Column(Integer, nullable=False)
    num_annotation: int = Column(Integer, nullable=False)
    num_form_field: int = Column(Integer, nullable=False)
    num_form_tag: int = Column(Integer, nullable=False)
    num_table_row: int = Column(Integer, nullable=False)
    num_table_column: int = Column(Integer, nullable=False)
    num_table_header_row: int = Column(Integer, nullable=False)
