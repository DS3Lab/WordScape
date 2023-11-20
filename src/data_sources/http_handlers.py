import time
import settings
from typing import Tuple, Union
import requests
from src.data_sources.download_exceptions import (
    FileSizeExceeded,
    HTTPError,
    InvalidContentType,
    valid_content_length,
    valid_content_type
)


def run_sess(
        sess_method: Union[requests.get, requests.head],
        timeout: int,
        allow_redirects: bool, url: str
) -> Tuple[requests.Response, Exception, int]:
    """run session
    @param sess_method: requests.get or requests.head
    @param timeout: int timeout
    @param allow_redirects: bool allow redirects
    @param url: str url

    return: requests.Response, Exception str, Timestamp int
    """
    timestamp = int(time.time())
    exception = None

    try:
        response = sess_method(
            url, timeout=timeout, allow_redirects=allow_redirects, stream=True
        )
    except Exception as e:
        response = None
        exception = e

    return response, exception, timestamp


def header_handler(
        response: requests.Response,
        exception: Exception
) -> Tuple[
    Union[requests.Response, None],
    dict,
    Union[Exception, FileSizeExceeded, InvalidContentType, HTTPError, None]
]:
    """ handle header: check for valid content type and content length, and
    return header metadata

    @param response: requests.Response
    @param exception: Exception raised during call to requests.head

    return: requests.Response, dict, Exception
    """
    header_metadata = {}

    # in this case, the download failed during run_sess, so we return the
    # original exception raise by the call to sess.head
    if response is None:
        return response, header_metadata, exception

    # in this case, the server sent a response, but the response code is not
    # 200, so we return the HTTPError exception
    if response.status_code != 200:
        return (
            response,
            header_metadata,
            HTTPError(status_code=response.status_code)
        )

    header_metadata = {k: response.headers.get(k, None) for k in
                       settings.download.HEADER_FIELDS}

    # check for valid content length
    content_length, exception = valid_content_length(
        header_metadata['content-length']
    )
    header_metadata['content-length'] = content_length

    if exception is not None:
        return response, header_metadata, exception

    # check for valid content type
    content_type, exception = valid_content_type(
        header_metadata['content-type']
    )
    header_metadata['content-type'] = content_type

    return response, header_metadata, exception


def body_handler(
        response: requests.Response,
        exception: Exception
) -> Tuple[
    Union[requests.Response, None],
    dict,
    Union[Exception, HTTPError, FileSizeExceeded, None]
]:
    """ handle body: check if response is valid, fetch ip-address and content
    length, and return body metadata

    @param response: requests.Response
    @param exception: Exception raised during call to sess.get

    return: requests.Response, dict, Exception
    """
    body_metadata = {}

    # in this case, the download failed during run_sess, so we return the
    # original exception raise by the call to sess.get
    if response is None:
        return response, body_metadata, exception

    if response.status_code != 200:
        return (
            response,
            body_metadata,
            HTTPError(status_code=response.status_code)
        )

    # get content length
    try:
        content_length = len(response.content)
    except TypeError:
        content_length = None

    content_length, exception = valid_content_length(content_length)
    body_metadata = {
        # dummy value for ip --> not collected
        'ip_address': 0, 'content_length': content_length
    }

    return response, body_metadata, exception
