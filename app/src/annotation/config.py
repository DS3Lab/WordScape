from dataclasses import dataclass
import pathlib
import yaml


@dataclass
class AnnotationConfig:
    # image config
    image_format: str
    image_height: int
    image_width: int
    image_dpi: int

    # decompression bomb checks
    max_decompress_ratio: float
    max_image_pixels: int

    # documents
    max_doc_bytes: int
    max_doc_pages: int

    # time limits
    annotation_timeout_secs: int
    annotation_cleanup_secs: int

    # data org
    max_bytes_in_shard: int

    # language
    top_k_languages: int

    # libreoffice
    unoserver_start_timeout: int
    unoconvert_timeout: int
    soffice_launch_timeout: int
    soffice_launch_ping_interval: float

    # entity detection
    max_heading_len: int
    form_field_min_length: int

    # entity relations
    bbox_relation_overlap_threshold: float
    bbox_relation_scale_threshold: float
    bbox_relation_closeness_threshold: float
    word_2_entity_overlap_threshold: float

    # annotation config
    min_text_chars: int


def load_config(fp: pathlib.Path) -> AnnotationConfig:
    with fp.open(mode='r') as f:
        data = yaml.safe_load(f)

    kwargs = {}
    for d in data.values():
        kwargs.update({k.lower(): v for k, v in d.items()})

    return AnnotationConfig(**kwargs)
