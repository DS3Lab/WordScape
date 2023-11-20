import regex

# constants
MAX_FILESIZE = 90 * 1024 * 1024  # 90 MB

# string patterns
DOC_FN_PATTERN = "doc_{url_hash}{ext}"
TAR_PATTERN = "docs_{part_id}-shard_{shard_num:05d}.tar.gz"
META_DATA_FN_PATTERN = "meta_{part_id}.parquet"
LOG_FN_PATTERN = "info_{part_id}.log"
LOG_FORMAT = "[%(asctime)s]::%(name)s::%(levelname)s::%(message)s"

VALID_CT_REGEX = pattern = regex.compile(
    r'(application|text)/.*(openxml|word|doc|msword|msdownload|rtf).*',
    flags=regex.IGNORECASE | regex.DOTALL
)

# header fields
HEADER_FIELDS = [
    "content-type",
    "content-length",
    "content-encoding",
    "content-language",
    "last-modified"
]

# mapping from olet library names to DB olet fields
OLET_DB_MAPPING = {
    'File format': 'olet_ftype',
    'Container format': 'olet_container',
    'Properties code page': 'olet_codepage',
    'Python codec': 'olet_python_codec',
    'Application name': 'olet_appname',
    'Author': 'olet_author',
    'Encrypted': 'olet_encrypted',
    'VBA Macros': 'olet_vba',
    'XLM Macros': 'olet_xlm',
    'External Relationships': 'olet_ext_rels',
    'ObjectPool': 'olet_ObjectPool',
    'Flash objects': 'olet_flash'
}
