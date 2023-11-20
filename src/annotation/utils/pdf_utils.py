import pathlib

import cv2
import numpy as np
import os
from pdf2image import pdfinfo_from_path, convert_from_path
from typing import Union, Tuple, Dict

from src.annotation.utils.identifiers import get_page_id

PDF2IMG_BLOCKSIZE = 4

__all__ = [
    "get_page_count_from_pdf",
    "pdf_to_page_images_iterator",
    "extract_page_images_and_dimensions_from_pdf"
]


def get_page_count_from_pdf(pdf_fp: pathlib.Path) -> int:
    r"""Get number of pages from pdf file.

    @param pdf_fp: path to pdf file

    @return: number of pages
    """
    pdf_info = pdfinfo_from_path(pdf_fp, userpw=None, poppler_path=None)
    return int(pdf_info["Pages"])


def pdf_to_page_images_iterator(
        pdf_fp: str,
        fmt: str,
        dpi: int,
        size: Tuple[Union[int, None], Union[int, None]],
        output_folder: Union[str, None]
):
    r"""Iterate over pages of a pdf file. The function creates pages in batches
    of `block_size` pages. This is to avoid memory issues when converting
    large pdf files.

    @param pdf_fp: path to pdf file
    @param fmt: output format; this should be a lossless format when the
        function is used for entity detection.
    @param dpi: resolution of the output image(s)
    @param size: size of the output image(s), uses the Pillow (width, height)
        standard. If one of width or height is set to None, the image
        aspect ratio is preserved.
    @param output_folder: path to output folder

    @return: iterator over pages
    """
    pdf_info = pdfinfo_from_path(pdf_fp, userpw=None, poppler_path=None)
    num_pages = pdf_info["Pages"]
    for page in range(1, num_pages + 1, PDF2IMG_BLOCKSIZE):
        # ! important: output format needs to use lossless compression when
        # ! converting the colorized pdf to images. Otherwise, the entity
        # ! detection will be inaccurate.
        yield convert_from_path(
            pdf_path=pdf_fp,
            size=size,
            dpi=dpi,
            first_page=page,
            thread_count=4,
            last_page=min(page + PDF2IMG_BLOCKSIZE - 1, num_pages), fmt=fmt,
            output_folder=output_folder
        )


def extract_page_images_and_dimensions_from_pdf(
        doc_id: str,
        pdf_fp: Union[str, pathlib.Path],
        target_dir: Union[str, pathlib.Path],
        fmt: str,
        dpi: int,
        size: Tuple[Union[int, None], Union[int, None]]
) -> Tuple[Dict[str, str], Dict[str, Tuple[int, int]]]:
    r"""Extract page images and dimensions from a pdf file.

    Note: Currently, this function saves individual page images to the
        target_dir directory. This will be removed in the  future as want to
        write the images directly from memory into tar archives.

    @param doc_id: document id
    @param pdf_fp: path to pdf file
    @param target_dir: path to target directory
    @param fmt: output format; this should be a lossless format when the
        function is used for entity detection.
    @param dpi: resolution of the output image(s)
    @param size: size of the output image(s), uses the Pillow (width, height)
        standard. If one of width or height is set to None, the image
        aspect ratio is preserved.

    @return: dict with page_id as keys and paths to extracted images as
        value, dict with page_id as keys and dimensions for each
        image/page as value
    """
    image_paths = {}
    image_dimensions = {}
    page_number = 1  # page number starts at 1

    # extract pages from pdf as images
    for pages_block in pdf_to_page_images_iterator(
            pdf_fp=pdf_fp,
            fmt=fmt,
            dpi=dpi,
            size=size,
            output_folder=None
    ):
        for page_img in pages_block:
            # get page id
            page_id = get_page_id(doc_id, page_number)

            # convert to cv2 format with HSV color space
            page_img = np.array(page_img).astype(np.uint8)
            page_img = cv2.cvtColor(page_img, code=cv2.COLOR_RGB2BGR)

            # extract dimensions
            height, width, _ = page_img.shape
            image_dimensions[page_id] = (width, height)

            fp = os.path.join(
                target_dir, f"{page_id}.{fmt}"
            )
            image_paths[page_id] = fp
            cv2.imwrite(fp, page_img)

            page_number += 1

    return image_paths, image_dimensions
