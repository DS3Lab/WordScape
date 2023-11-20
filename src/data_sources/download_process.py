from io import BytesIO
import pandas as pd
import os
import tarfile
import logging
import uuid
import time
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from joblib import Parallel, delayed
import threading
import settings
from src.data_sources.maldoc_check import MalDocCheck
from src.data_sources.http_handlers import run_sess, header_handler, \
    body_handler
from src.data_sources.download_exceptions import FileSizeExceeded
import hashlib
from orm.models import SourcesRecordDB
import multiprocessing as mp
from typing import List, Tuple, Union


class DownloadProcess(mp.Process):
    def __init__(self, input_queue: mp.Queue, cc_dump_id: str, dl_timeout: int,
                 dl_retries: int, dl_redirects: int, dl_backoff: int,
                 num_threads: int, write_dir: str):
        """
        Launch one process which receives URL batches in a queue, then
        downloads them while writing downloaded files to tars and metadata to
        parquet files.

        Each process is responsible for one shard_id (counting up from
        1...(num_urls / shard_size)) of a given opendoc cc_dump_id.

        @param input_queue: A multiprocessing queue which receives the URLs to
            handle
        @param cc_dump_id: Dump id this process is part of processing.
        @param dl_timeout: Timeout for requests.
        @param dl_retries: How many times the process will retry a failed
            download / request.
        @param dl_redirects: Amount of allowed redirects in request.
        @param dl_backoff: Backoff factor when retrying requests.
        @param num_threads: Number of threads to use (default 10)
        @param write_dir: Directory to write all output to
        """
        super(DownloadProcess, self).__init__()

        # unique process id
        self.worker_id = str(uuid.uuid4())
        self.input_queue = input_queue
        self.cc_dump_id = cc_dump_id
        self.dl_timeout = dl_timeout
        self.dl_retries = dl_retries
        self.dl_redirects = dl_redirects
        self.dl_backoff = dl_backoff
        self.write_dir = write_dir

        # create directory structure
        # ! all files are written to this directory
        self.WORK_DIR = Path(write_dir)

        # set up logging information
        self.LOG_FN_PATTERN = "info_{part_id}.log"
        self.LOG_FORMAT = "[%(asctime)s]::%(name)s::%(levelname)s::%(message)s"
        self.logger_writable = self.get_logger(
            file_path=str(self.WORK_DIR / ("worker_log_" + self.worker_id))
        )

        # create initial writable files
        self.get_writable_files()
        self.num_threads = num_threads
        # lock for in-actor threading
        self.lock = threading.Lock()

        # lock for pandas concat
        self.pdLock = threading.Lock()

    def run(self):
        """
        Required by multiprocessing. This is the processes core loop.
        """
        while True:
            inputs = self.input_queue.get(block=True, timeout=None)
            if inputs is None:
                self.flush()
                self.logger_writable.info(
                    "Regularly terminated worker; queue is empty.")
                break

            try:
                self.batch_handler(inputs)
            except Exception as e:
                self.logger_writable.error("Batch handler error! " + str(
                    e) + " Missed Batch items " + str(inputs))

    # create a new tar file and parquet file once we reach a new shard
    def get_writable_files(self):
        """
        Flush current memory (files and metadata) to storage, and obtain
        filenames for next flush. Called once the max. shard size is exceeded
        (currently 100MB per shard).
        """
        self.flush()

        self.shard_id = self.worker_id + "_" + str(uuid.uuid4())
        self.TAR_FILE = f"{self.shard_id}.tar.gz"
        self.tar_writable = tarfile.TarFile.open(
            os.path.join(self.WORK_DIR, self.TAR_FILE), mode='w:gz')

        # again, hacky but easy
        cols = [c.key for c in SourcesRecordDB.__table__.columns]
        self.df = pd.DataFrame(columns=cols)
        # For now, all entries as string
        self.df = self.df.astype(str)

        self.PARQUET_FILE = f"{self.shard_id}.parquet"
        # just a filename, since pandas will dump to this
        self.parquet_writable = os.path.join(self.WORK_DIR, self.PARQUET_FILE)

        self.logger_writable.info(
            "Created .tar.gz and .parquet for shard id " + str(self.shard_id))

    def flush(self):
        """
        Flush current data (if any) from memory to storate.
        """
        # reset file size count
        self.current_shard_size = 0
        if hasattr(self, 'tar_writable'):
            self.tar_writable.close()

        # dump current db dataframe to parquet
        if hasattr(self, 'df'):
            self.df.to_parquet(self.parquet_writable)

    def get_logger(
            self, file_path: str, level=logging.INFO
    ) -> logging.Logger:
        """get worker logger
        @param file_path: path for log file
        @param level: log level
        return: logging.Logger
        """
        logger = logging.getLogger(name="worker_log_" + self.worker_id)
        log_formatter = logging.Formatter(fmt=self.LOG_FORMAT)

        # comment this to suppress console output
        # stream_handler = logging.StreamHandler()
        # stream_handler.setFormatter(log_formatter)
        # logger.addHandler(stream_handler)

        log_file_info = file_path
        file_handler_info = logging.FileHandler(log_file_info, mode='w')
        file_handler_info.setFormatter(log_formatter)
        file_handler_info.setLevel(logging.INFO)
        logger.addHandler(file_handler_info)
        logger.setLevel(logging.DEBUG)

        return logger

    def write_to_tar(self, doc_fn: str, content: bytes):
        """
        Write a word document to the current shard tarfile, and create a new
        tarfile if maximum shard size is exceeded (currently 100MB).
        @param: doc_fn, currently the url hash.
        @param: content: file bytes.
        """
        tarinfo = tarfile.TarInfo(doc_fn)
        tarinfo.size = len(content)
        tarinfo.mtime = time.time()
        self.tar_writable.addfile(tarinfo, BytesIO(content))
        self.current_shard_size += tarinfo.size

        # create new tar file if size exceeded
        # ! shard size that triggers flush controlled here
        if self.current_shard_size > 10 ** 8:
            self.get_writable_files()

    def batch_handler(self, batch: List[Tuple[str, str]]):
        """
        Download one batch of URLs with an HTTP adapter shared accross threads.

        @param batch: a batch of URLs and their hashes as tuples.
        """

        # create session
        retries = Retry(
            total=self.dl_retries,
            redirect=self.dl_redirects,
            backoff_factor=self.dl_backoff,
            respect_retry_after_header=False,
        )
        # ! don't set too many threads per worker
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=self.num_threads,
            pool_maxsize=int(self.num_threads * 1.1)
        )

        with requests.Session() as sess:
            sess.mount('http://', adapter)
            sess.mount('https://', adapter)

            _ = Parallel(n_jobs=self.num_threads, backend='threading')(
                delayed(self.download_doc)(batch_item[0], batch_item[1], sess)
                for batch_item in batch
            )

        return 1

    def record_to_df(self, record: SourcesRecordDB):
        """
        Writes a document download record to the current dataframe, which will
        later be dumped to a parquet file.

        @param record: Record to write, matching the ORM model.
        """
        # ! hacky but easy
        keep_recs = {c.key: (
            [record.__dict__[c.key]] if c.key in record.__dict__ else [None])
            for c in SourcesRecordDB.__table__.columns}
        temp_df = pd.DataFrame(keep_recs).astype(str)
        with self.pdLock:
            self.df = pd.concat([self.df, temp_df])

    def safe_close(self, response: Union[requests.Response, None]):
        """
        Safely close a response.

        @param response: a requests.Response object.
        """
        if response is not None:
            response.close()

    def download_doc(self, url: str, url_hash: str, sess: requests.Session):
        """
        Download a docx from a given url, check it's safety,
        Write it into tarfile and append db info to parquet (if safe).

        @param url: The url of the docx file to download. The worker receives
            this parameter from the head.
        @param url_hash: Hash of the url
        @param sess: Shared HTTP Session
        """

        # ! one source of truth: DB records
        record = SourcesRecordDB()
        record.url = url
        record.url_hash = url_hash
        record.crawl_id = self.cc_dump_id
        record.shard_id = self.shard_id

        try:
            self.logger_writable.info(
                "downloading doc " + str(url) + " in shard " + str(
                    self.shard_id))

            # <----------------- request header ----------------->
            # http session head check
            response, exception, timestamp = run_sess(
                sess_method=sess.head, timeout=self.dl_timeout,
                allow_redirects=True,
                url=url
            )

            # handle header (creates or catches all fatal exceptions)
            response, header_metadata, exception = header_handler(response,
                                                                  exception)

            # ! handle DB data
            record.timestamp = timestamp
            record.status_code = getattr(response, "status_code", None)
            record.exception = repr(exception)

            for k, v in header_metadata.items():
                setattr(record, str(k).replace('-', '_'), v)

            # check exceptions
            if exception is not None:
                self.safe_close(response)
                self.logger_writable.error(
                    "HTTP HEAD request exception: " + repr(exception))
                self.record_to_df(record)
                return 0

            # <----------------- run get request ----------------->
            # get doc
            response, exception, timestamp = run_sess(
                sess_method=sess.get, timeout=self.dl_timeout,
                allow_redirects=True,
                url=url
            )

            # handle body
            response, body_metadata, exception = body_handler(response,
                                                              exception)

            # ! handle DB data
            record.timestamp = timestamp
            record.status_code = getattr(response, "status_code", None)
            record.exception = repr(exception)

            for k, v in body_metadata.items():
                setattr(record, str(k).replace("-", "_"), v)

            # check exceptions
            if response is None:
                self.logger_writable.error("HTTP GET no response")
                self.record_to_df(record)
                return 0

            # maldoc checks
            if response.content is not None and record.exception == 'None':
                maldoc = MalDocCheck(data=response.content)
                try:
                    indicators = maldoc.run()
                except Exception as e:
                    self.safe_close(response)
                    self.logger_writable.error(
                        "maldoc.run() failed with error: " + str(e))
                    self.record_to_df(record)
                    return 0

                olet_pass, reason = maldoc.validate_indicators(indicators)

                # ! handle DB data
                record.olet_pass = olet_pass
                for ind in indicators:
                    if (
                            ind.name in settings.download.OLET_DB_MAPPING
                            and
                            ind.value
                    ):
                        setattr(record,
                                settings.download.OLET_DB_MAPPING[ind.name],
                                ind.value)

                if not olet_pass:
                    self.safe_close(response)
                    self.logger_writable.error(
                        "maldoc not passed, reason: " + str(reason))
                    self.record_to_df(record)
                    return 0

            # ! extra filesize check (cannot rely on header information alone)
            content_len = len(response.content)
            if content_len > settings.download.MAX_FILESIZE:
                self.safe_close(response)
                self.logger_writable.error(
                    "max filesize exceeded, " + str(content_len)
                )
                record.exception = repr(FileSizeExceeded(filesize=content_len))
                self.record_to_df(record)
                return 0

            # write content to current tar file
            if response.content is not None and record.exception == 'None':
                doc_ext = os.path.splitext(record.url)[1]
                doc_fn = settings.download.DOC_FN_PATTERN.format(
                    url_hash=record.url_hash, ext=doc_ext)
                record.filename = doc_fn
                setattr(record, "filename", doc_fn)

                # bytehash --> for post-processing deduplication
                record.bytehash = hashlib.sha256(response.content).hexdigest()

                self.record_to_df(record)
                with self.lock:
                    self.write_to_tar(doc_fn=doc_fn, content=response.content)
                self.logger_writable.info("Success!")

            self.safe_close(response)
            return 1
        except Exception as e:
            e_str = "Non-document error " + str(e)
            record.exception = e_str
            self.logger_writable.error(e_str)
            self.record_to_df(record)
            return 0
