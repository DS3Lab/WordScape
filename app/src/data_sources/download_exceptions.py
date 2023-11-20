"""
Classes for custom exceptions that may be thrown whilst downloading documents.
"""
import settings
from typing import Tuple, Union


class InvalidContentType(Exception):
    def __init__(self, content_type):
        """
        The HTTP content type header is not acceptable.
        """
        self.content_type = content_type

    def __repr__(self):
        return "InvalidContentType({})".format(self.content_type)


class FileSizeExceeded(Exception):
    def __init__(self, filesize):
        """
        Attemtped to download a document of too large filesize.
        """
        self.filesize = filesize

    def __repr__(self):
        return "FileSizeExceeded({})".format(self.filesize)


class OleCheckFailed(Exception):
    def __init__(self, error):
        """
        A safety check on a .docx or .doc files OLE properties failed, so the document is not safe to download.
        (See Microsoft OLE documentation for safety of OLE properties, and maldoc_check.py for implementation)
        """
        self.error = error

    def __repr__(self):
        return "OleCheckFailed({})".format(self.error)
    
class HTTPError(Exception):
    def __init__(self, status_code=None):
        """
        A benign HTTP error, signified by a status code
        """
        self.status_code = status_code

    def __repr__(self):
        return "HTTPError={}".format(self.status_code)
    
"""
Functions to check validity of downloads and requests
"""

def valid_content_type(
        content_type: str
) -> Tuple[
    Union[str, None], Union[InvalidContentType, None]
]:
    """check if content type is valid; this functions returns True if either
    the content type is unknown or if the content type is known and is found to
    be valid.

    @content_type: str content type
    return: bool, InvalidContentType exception or None
    """
    if content_type is None:
        # unknown content type
        return content_type, None

    # sanitize content type string
    content_type = content_type.lower().replace('-', '')

    if settings.download.VALID_CT_REGEX.match(content_type) is None:
        return content_type, InvalidContentType(content_type=content_type)

    return content_type, None


def valid_content_length(
        content_length: Union[str, None]
) -> Tuple[
    Union[int, None], Union[FileSizeExceeded, None]
]:
    """check if content length is valid; this functions returns True if either
    the file size is known and below the maximally allowed file size, or if the
    file size is unknown.

    @content_length: str content length

    return: bool, FileSizeExceeded exception or None
    """
    try:
        content_length = int(content_length)
    except (TypeError, ValueError):
        return content_length, None

    # check size of content
    if content_length > settings.download.MAX_FILESIZE:
        return content_length, FileSizeExceeded(filesize=content_length)

    return content_length, None