from docx.document import Document as _Document
from docx import Document
import io
import numpy as np
import os
import pathlib
from PIL import Image
import tempfile
import zipfile

from src.annotation.colorization import ColorizationHandler
from src.annotation.utils.color_utils import hsv_to_rgb
from src.annotation.utils.updateable_zipfile import UpdateableZipFile

import settings

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


def colorize_figures(
        word_doc: _Document,
        temp_dir: pathlib.Path,
        colorization_handler: ColorizationHandler,
) -> _Document:
    r""" Colorizes figures in word document. It does so by first creating a
    temporary word document, then extracting all images from the document,
    colorizing them, and finally overwriting the images in the temporary
    document. The temporary document is then loaded into memory, destroyed
    on disk and returned.

    @param word_doc: word document to colorize
    @param temp_dir: directory to use for storing temporary files
    @param colorization_handler: colorization handler; here, this is only used
        to keep track of annotation sources.


    @return: colorized word document instance
    """

    # create temporary file
    temp_doc_fp = tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".docx", dir=temp_dir
    )

    # save doc to temp file
    word_doc.save(path_or_stream=temp_doc_fp)

    # we raise an error if something has gone wrong and the document is not a
    # valid zip file
    if not zipfile.is_zipfile(temp_doc_fp):
        raise ValueError(f"document is not a valid zip file")

    # convert hsv to rgb
    rgb_color = tuple(hsv_to_rgb(hsv_color=settings.colors.COLOR_FIGURES))

    # extract image files, overwrite them with images color
    with UpdateableZipFile(temp_doc_fp, "a") as archive:
        for fp in archive.namelist():
            if (
                    not fp.startswith("word/media") or
                    not fp.lower().endswith(IMG_EXT)
            ):
                continue

            # extract image to temp dir
            img_bytes = archive.read(fp)

            # read and overwrite image
            try:
                img = Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                print(f"[WARNING] reading image {fp} "
                      f"failed with {e.__class__.__name__}: {e}")
                continue
            img = Image.new("RGB", img.size)
            img.putdata([rgb_color] * np.prod(img.size))

            _, ext = os.path.splitext(fp)
            ext = ext.lower().strip(".")
            ext = 'jpeg' if ext == 'jpg' else ext
            with io.BytesIO() as temp_img:
                try:
                    img.save(temp_img, format=ext)
                except IOError:
                    continue
                except Exception as e:
                    # could not write file, skip
                    print(f"unknown exception while writing image {fp};\n{e}")
                    continue

                temp_img.seek(0)
                archive.write(temp_img, fp)

            # add annotation source
            colorization_handler.update_colorization_decisions(
                text=None,
                decision_source=settings.annotation.ANNOTATION_BUILTIN,
                entity_decision=settings.entities.ENTITY_FIGURE_ID
            )

    word_doc = Document(temp_doc_fp.name)
    temp_doc_fp.close()

    return word_doc
