from io import BytesIO
import zipfile
from pathlib import Path
from PIL import Image
from PIL import UnidentifiedImageError

from src.exceptions import *

__all__ = [
    "get_uncompressed_file_size",
    "detect_image_decompression_bombs",
    "zip_bomb_check"
]

# Limit images to around 32MB for a 24-bit (3 bpp) image
MAX_IMAGE_PIXELS = int(1024 * 1024 * 1024 // 32 // 3)

IMG_EXT = (
    '.bmp',
    '.gif',
    '.jpeg',
    '.jpg',
    '.png',
    '.tiff',
    '.ico',
    '.pcx',
    '.ppm',
    '.pgm',
    '.pbm',
    '.pnm',
    '.webp',
    '.hdr',
    '.dds',
    '.im',
    '.eps',
    '.svg'
)


def _compression_ratio(zip_file: zipfile.ZipFile):
    uncompressed_size = sum(zp.file_size for zp in zip_file.infolist())
    compressed_size = sum(zp.compress_size for zp in zip_file.infolist())

    if compressed_size == 0:
        return 0

    return uncompressed_size / compressed_size


def get_uncompressed_file_size(doc_bytes: bytes, doc_fn: Path):
    # check if file is a valid zip file
    with BytesIO(doc_bytes) as f:
        if not zipfile.is_zipfile(f):
            raise NoZipFileException(f"{doc_fn} is not a valid zip file")

        # calculate uncompressed size
        with zipfile.ZipFile(f) as zf:
            uncompressed_size = sum(zp.file_size for zp in zf.infolist())

        return uncompressed_size


def detect_image_decompression_bombs(doc_bytes: bytes, doc_fn: Path):
    with BytesIO(doc_bytes) as f:
        if not zipfile.is_zipfile(f):
            raise NoZipFileException(f"{doc_fn} is not a valid zip file")

        # check if one of the images is a decompression bomb
        with zipfile.ZipFile(f) as zf:
            # check images in zip file
            for fp in zf.namelist():
                if not fp.lower().endswith(IMG_EXT):
                    continue

                img_bytes_compressed = zf.read(fp)

                try:
                    Image.open(BytesIO(img_bytes_compressed))
                except Image.DecompressionBombError as e:
                    raise ImageDecompressionBombError(
                        f"{doc_fn} -- Image decompression bomb detected: "
                        "image pixels exceed max image pixels; "
                        f"error:\n\t{e}"
                    )
                except Exception as e:
                    print(f"[WARNING] reading image {fp} "
                          f"failed with {e.__class__.__name__}: {e}")
                    continue


def zip_bomb_check(
        doc_bytes: bytes, threshold: float = 100,
        max_image_pixels=MAX_IMAGE_PIXELS
):
    Image.MAX_IMAGE_PIXELS = max_image_pixels

    with BytesIO(doc_bytes) as f:
        if not zipfile.is_zipfile(f):
            raise NoZipFileException(f"document is not a valid zip file")

        with zipfile.ZipFile(f, "r") as zip_file:
            cr = _compression_ratio(zip_file)

            if cr > threshold:
                raise ZipBombException(f"zip bomb detected: compression ratio"
                                       f" {cr} exceeds threshold {threshold}")

            # check images in zip file
            for fp in zip_file.namelist():
                if (
                        not fp.startswith("word/media") or
                        not fp.lower().endswith(IMG_EXT)
                ):
                    continue

                img_bytes_compressed = zip_file.read(fp)

                try:
                    Image.open(BytesIO(img_bytes_compressed))
                except Image.DecompressionBombError as e:
                    raise ImageDecompressionBombError(
                        "Image decompression bomb detected: "
                        "image pixels exceed max image pixels; "
                        f"error:\n\t{e}"
                    )
                except UnidentifiedImageError as e:
                    raise UnidentifiedImageError(e)
                except Exception as e:
                    print(f"[WARNING] reading image {fp} "
                          f"failed with {e.__class__.__name__}: {e}")
                    continue
