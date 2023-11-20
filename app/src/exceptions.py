from typing import Set

__all__ = [
    "InconsistentPageCountError",
    "InconsistentAspectRatiosError",
    "UnsupportedDocumentLayoutError",
    "ConversionFailedException",
    "SofficeStartFailed",
    "UnknownPageCountException",
    "PageCountExceededException",
    "ZipBombException",
    "NoZipFileException",
    "CompressedFileSizeExceededException",
    "UncompressedFileSizeExceededException",
    "ImageDecompressionBombError",
    "TextTooShortException"
]


class InconsistentPageCountError(Exception):
    r"""Raised when the number of pages in the PDF file is not consistent with
    the number of pages in the annotated pdf.

    Note: If this error is raised, then it might indicate that the colorization
        step has interfered with the layout of the document!
    """

    def __init__(self, expected: Set, actual: Set):
        self.expected = expected
        self.actual = actual
        super().__init__(f"Expected {expected} pages, but got {actual} pages.")

    def __repr__(self):
        return f"InconsistentPageCountError(" \
               f"expected={self.expected}, actual={self.actual}" \
               f")"


class InconsistentAspectRatiosError(Exception):
    r"""Raised when the aspect ratios of the pages in the PDF file are not
    consistent with the aspect ratios of the pages in the rendered page images.
    """

    def __init__(self, ar_pdf, ar_img):
        self.ar_pdf = ar_pdf
        self.ar_img = ar_img
        super().__init__(f"Expected inconsistent aspect ratios:"
                         f"got {ar_pdf} from pdf"
                         f"and {ar_img} from renderings.")

    def __repr__(self):
        return f"InconsistentAspectRatiosError(" \
               f"ar_pdf={self.ar_pdf}, ar_img={self.ar_img}" \
               f")"


class SofficeStartFailed(Exception):
    r"""Raised when the soffice process fails to start."""
    pass


class UnsupportedDocumentLayoutError(Exception):
    r"""Raised when the layout of the document is not supported, such as
    too many document columns, i.e. more than 3"""

    def __init__(self, msg: str):
        self.msg = msg

    def __repr__(self):
        return f"UnsupportedDocumentLayoutError(msg={self.msg})"


class ConversionFailedException(Exception):
    r"""Raised when the conversion of a doc/docx file to a pdf file fails."""
    pass


class UnknownPageCountException(Exception):
    r"""Raised when the page count of a document cannot be determined."""
    pass


class PageCountExceededException(Exception):
    r"""Raised when the page count of a document exceeds the maximum allowed
    number of pages."""
    pass


class ZipBombException(Exception):
    r"""Raised when a zip bomb is detected."""
    pass


class NoZipFileException(Exception):
    r"""Raised when a file is not a zip file."""
    pass


class CompressedFileSizeExceededException(Exception):
    r"""Raised when a file size exceeds the maximum allowed file size."""
    pass


class UncompressedFileSizeExceededException(Exception):
    r"""Raised when an uncompressed file size exceeds the maximum allowed
    file size."""
    pass


class ImageDecompressionBombError(Exception):
    r"""Raised when an image decompression bomb is detected."""
    pass


class TextTooShortException(Exception):
    r"""Raised when the text of a document is too short."""
    pass
