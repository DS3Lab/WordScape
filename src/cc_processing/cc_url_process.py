from io import BufferedReader
import logging
import os
import re
from typing import List, Union
import pandas as pd
import uuid
import json

import requests

import multiprocessing as mp

from tempfile import SpooledTemporaryFile

from warcio.archiveiterator import ArchiveIterator
from warcio.recordloader import ArchiveLoadFailed, ArcWarcRecord

import settings

class CCURLProcess(mp.Process):
    def __init__(self, input_queue: mp.Queue, input_base_url: str, cc_dump: str):
        """
        Launch one process which takes warc_parts.txt files from the input queue,
        downloads and processes that warc, and then outputs any docx URLs found
        to a parquet output list.

        @param input_queue: Queue to read tasks (WAT parts) to handle
        @param input_base_url: CommonCrawl base URL
        @param cc_dump: CommonCrawl snapshot being handled
        """

        super(CCURLProcess, self).__init__()
        self.input_queue = input_queue
        self.found_urls = []
        self.data_url_pattern = re.compile('^(s3|https?|file|hdfs):(?://([^/]*))?/(.*)')
        self.doc_pattern = re.compile("(^(www|http:|https:)+[^\s]+[\w]\.(doc|docx)$)")
        self.input_base_url = input_base_url
        self.cc_dump = cc_dump
        self.local_temp_dir = settings.filesystem.TMP_DIR

        self.records_processed = 0
        self.warc_input_processed = 0
        self.warc_input_failed = 0

        self.worker_id = str(uuid.uuid4())
        self.WORK_DIR = settings.filesystem.CC_DIR / cc_dump
        # set up logging
        self.LOG_FN_PATTERN = "info_{part_id}.log"
        self.LOG_FORMAT = "[%(asctime)s]::%(name)s::%(levelname)s::%(message)s"
        self.logger_writable = self.get_logger(file_path=(self.WORK_DIR / ("worker_log_" + self.worker_id)))

        # parse HTTP headers of WARC records (derived classes may override this)
        self.warc_parse_http_header = True

    def get_logger(self, file_path: str) -> logging.Logger:
        """get worker logger
        @param file_path: path for log file
        @param level: log level
        return: logging.Logger
        """

        logger = logging.getLogger(name="cc_log_" + self.worker_id)
        log_formatter = logging.Formatter(fmt=self.LOG_FORMAT)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        logger.addHandler(stream_handler)

        log_file_info = file_path

        file_handler_info = logging.FileHandler(log_file_info, mode='w')
        file_handler_info.setFormatter(log_formatter)
        file_handler_info.setLevel(logging.INFO)
        logger.addHandler(file_handler_info)

        logger.setLevel(logging.INFO)

        return logger
    
    def fetch_warc(self, uri: str, base_uri: str=None, offset:int =-1, length:int =-1
    ) -> Union[SpooledTemporaryFile, BufferedReader, None]:
        """
        Download a warc or wat file from a given uri (uris from partition_listings)
        and return a stream that can be used by warcio to extract URLs to
        files according to the set regex

        @param uri: uri from which to download the file
        @param base_uri: base uri domain
        @param offset: offset for reading downloaded file
        @param length: if greater than 0, max file length to read

        return: temporary readable file stream
        """

        (scheme, netloc, path) = (None, None, None)
        uri_match = self.data_url_pattern.match(uri)
        if not uri_match and base_uri:
            # relative input URI (path) and base URI defined
            uri = base_uri + uri
            uri_match = self.data_url_pattern.match(uri)

        if uri_match:
            (scheme, netloc, path) = uri_match.groups()
        else:
            # keep local file paths as is
            path = uri

        stream = None

        if scheme == 's3':
            # download warcs from amazon s3
            raise NotImplementedError
        elif scheme == 'https' or scheme == 'http':
            # download warcs via http(s)
            headers = None
            if offset > -1 and length > 0:
                headers = {
                    "Range": "bytes={}-{}".format(offset, (offset + length - 1))
                }
                # Note: avoid logging many small fetches
                # self.logger_writable.debug('Fetching {} ({})'.format(uri, headers))
            else:
                self.logger_writable.info('Fetching {}'.format(uri))

            response = requests.get(uri, headers=headers)

            if response.ok:
                warctemp = SpooledTemporaryFile(
                    max_size=2_097_152, mode='w+b', dir=self.local_temp_dir
                )
                warctemp.write(response.content)
                warctemp.seek(0)
                stream = warctemp
            else:
                self.logger_writable.error(
                    'Failed to download {}: {}'.format(uri, response.status_code)
                )
        else:
            # read from file system
            self.logger_writable.info('Reading local file {}'.format(uri))
            if scheme == 'file':
                # must be an absolute path
                uri = os.path.join('/', path)
            else:
                base_dir = os.path.abspath(os.path.dirname(__file__))
                uri = os.path.join(base_dir, uri)
            try:
                stream = open(uri, 'rb')
            except IOError as exception:
                self.logger_writable.error(
                    'Failed to open {}: {}'.format(uri, exception))
                self.warc_input_failed += 1

        return stream

    def process_warcs(self, iterator: List[str]):
        """
        Process WARC/WAT/WET files, calling iterate_records(...) for each file
        
        @param iterator: uri iterator for wats / warcs
        """
        for uri in iterator:
            self.warc_input_processed += 1

            stream = self.fetch_warc(uri, self.input_base_url)
            if not stream:
                self.logger_writable.error("cannot build fetch stream for uri " + uri)
                continue

            no_parse = (not self.warc_parse_http_header)
            try:
                archive_iterator = ArchiveIterator(stream,
                                                   no_record_parse=no_parse,
                                                   arc2warc=True)
                for res in self.iterate_records(uri, archive_iterator):
                    yield res
            except ArchiveLoadFailed as exception:
                self.warc_input_failed += 1
                self.logger_writable.error(
                    'Invalid WARC: {} - {}'.format(uri, exception))
            finally:
                stream.close()

    def iterate_records(self, _warc_uri, archive_iterator: ArchiveIterator):
        """
        Iterate over all WARC records. This method can be customized
        and allows to access also values from ArchiveIterator, namely
        WARC record offset and length.

        @param _warc_uri: legacy depreceated
        @param archive_iterator: Container for warc / wat URIs
        """
        for record in archive_iterator:
            for res in self.process_record(record):
                yield res
            self.records_processed += 1

        # WARC record offset and length should be read after the record
        # has been processed, otherwise the record content is consumed
        # while offset and length are determined:
        #  warc_record_offset = archive_iterator.get_record_offset()
        #  warc_record_length = archive_iterator.get_record_length()

    def find_matching_values(self, json_string: str, pattern: re.Pattern) -> List[str]:
        """
        Recursively match values inside json_string

        @param json_string: valid json string, to be loaded into json object
        @param pattern: regex pattern to recursively match

        return: List of string matches
        """
        data = json.loads(json_string)
        matching_values = []

        def search_value(value):
            if isinstance(value, dict):
                for v in value.values():
                    search_value(v)
            elif isinstance(value, list):
                for v in value:
                    search_value(v)
            else:
                if isinstance(value, str) and re.match(pattern, value):
                    matching_values.append(value)

        search_value(data)
        return matching_values

    def process_record(self, record: ArcWarcRecord):
        """
        Process a single WARC/WAT/WET record and generate found pattern matches
        
        @param record: to be processed

        return: yields tuples of found pattern and pattern count
        """
        if record.rec_type != 'metadata':
            # skip over non-metadata, as these also contain links
            return

        data = record.content_stream().read()

        items = self.find_matching_values(data, self.doc_pattern)
        count = 0
        for item in items:
            self.logger_writable.info("record processed " + item)
            count += 1
            yield item, count
    
    def run(self):
        """
        Core process loop required by python multiprocessing.
        """

        while True:
            input = self.input_queue.get(block=True, timeout=None)
            if input is None:
                break

            try:
                # handle the list of inputs
                self.batch_handler(input)
            except Exception as e:
                self.logger_writable.error(e)

    def batch_handler(self, warcs_to_dl):
        """
        Give warcs_to_dl to process_warcs --> this gives
        url, count iterator (these are the URLs we want)
        """

        url_list = []
        for url, count in self.process_warcs(warcs_to_dl):
            url_list.append(url)

        df = pd.DataFrame({'url': url_list})
        df.to_parquet(self.WORK_DIR / (self.cc_dump.lower().replace("-", "_") + "_" + self.worker_id + "_" + str(uuid.uuid4()) + ".parquet"))

        self.logger_writable.info("Success! got URL list")