"""
This module contains basic directory structures for the project.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent

# resources
RESOURCES_DIR = ROOT / "resources"
FASTTEXT_CLASSIFIERS_DIR = Path(RESOURCES_DIR, "fasttext-models")

# data dirs
DATA_ROOT = ROOT / "data"
DOC_SOURCES_DIR = DATA_ROOT / "doc_sources"
CC_SEGMENT_DIR = DATA_ROOT / "crawl-data"
CC_DIR = DATA_ROOT / "cc_urls"
CLEAN_URLS_DIR = DATA_ROOT / "clean_urls"
DOWNLOAD_DIR = DATA_ROOT / "download"

# tmp dirs
TMP_DIR = DATA_ROOT / "tmp"

# fixed-location files
ALEMBIC_INI_LOC = ROOT / "alembic.ini"

# for pipeline extensions
RAW_DIR = DATA_ROOT / "raw"
EXPERIMENT_DIR = DATA_ROOT / "experiments"

# structure of wordscape annotated files
WS_MULTIMODAL = "multimodal"
WS_META = "meta"
