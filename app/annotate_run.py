import argparse
from datetime import datetime as dt
import dill
import joblib
import json
import logging
from logging.handlers import QueueHandler
import multiprocessing as mp
import numpy as np
import os
import pathlib
from pathlib import Path
import shutil
import time
import uuid

from src.annotation.annotator_process import AnnotatorProcess
from src.annotation.annotator_process import STATUS_SUCCESS
from src.annotation.config import load_config

# replace pickle with dill
mp.set_start_method("fork")
mp.set_executable("python")
mp.process._PICKLE_SUPPORT = dill

LOG_FMT = '[%(asctime)s]::%(processName)-21s::%(levelname)-2s::%(message)s'


def get_timestamp() -> str:
    return dt.now().isoformat()


DATA_DIR = "/Users/maurice/phd/code/openDoc/data-backup-030723/doc_sources/CC-MAIN-2023-14"
OUT_DIR = f"data/annotated/CC-MAIN-2023-14/{time.time():.0f}"

# soffice
DEFAULT_SOFFICE_LOC = "/opt/homebrew/bin/soffice"


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str,
                        help="directory containing the data to be annotated",
                        default=DATA_DIR)
    parser.add_argument("--output_dir", type=str,
                        help="directory to store the annotated data",
                        default=OUT_DIR)
    parser.add_argument("--input_files", type=str,
                        help="path to a file containing a list of tar files "
                             "with the data to be annotated",
                        default=None)
    parser.add_argument("--crawl_id", default="cc_main_2022_49", type=str,
                        help="crawl id of the data to be annotated. Used for "
                             "bookkeeping.")
    parser.add_argument("--max_docs", default=1024, type=int)
    parser.add_argument("--soffice_executable", default=DEFAULT_SOFFICE_LOC,
                        help="install location of soffice")
    parser.add_argument("--config", help="path to config file",
                        default="configs/default_config.yaml")
    parser.add_argument("--job_id", help="job id", default=None)
    args = parser.parse_args()
    return args


class RateTracker:
    def __init__(self, n=200):
        self._start_time_tracker = []
        self._pages_tracker = []
        self._n = n

    def update(self, pages, start_time):
        if len(self._start_time_tracker) >= self._n:
            self._start_time_tracker.pop(0)
            self._pages_tracker.pop(0)

        self._start_time_tracker.append(start_time)
        self._pages_tracker.append(pages)

    def get_rate(self, current_time: float):
        if len(self._start_time_tracker) == 0:
            return 0

        if current_time - self._start_time_tracker[0] < 1e-6:
            return 0

        start_time = self._start_time_tracker[0]
        pages = sum(self._pages_tracker)
        return pages / (current_time - start_time)


class AnnotationMonitor(mp.Process):
    def __init__(
            self,
            results_queue: mp.Queue,
            logging_queue: mp.Queue,
            target_dir: pathlib.Path,
            job_id: str
    ):
        super(AnnotationMonitor, self).__init__()
        self._target_dir = target_dir
        self._results_queue = results_queue
        self._logging_queue = logging_queue
        self._job_id = job_id

    def run(self):
        # setup logging
        logger = logging.getLogger(name=self._job_id)
        logger.setLevel(logging.DEBUG)

        num_docs = 0
        toal_num_pages = 0
        num_success = 0
        logger.info(f"Start monitoring...")

        rate_tracker = RateTracker(n=200)

        try:
            while True:

                start_time = time.time()

                results = self._results_queue.get(
                    block=True, timeout=None
                )

                if results is None:
                    break

                ann_id = results["annotator_id"]
                status = results["status"]
                err_msg = results["err_msg"]
                doc_fn = results["doc_fn"]
                num_pages = results["num_pages"]

                rate_tracker.update(num_pages, start_time)

                num_docs += 1
                toal_num_pages += num_pages
                num_success += int(status == STATUS_SUCCESS)

                fail_prop = 1 - num_success / num_docs
                pages_per_second = rate_tracker.get_rate(time.time())

                logger.info(f"({ann_id})[status={status}]"
                            + f"[docs={num_success}"
                              f" (fail_rate={fail_prop * 100 :.2f}%)]"
                            + f"[pages={toal_num_pages}]"
                            + f"[{pages_per_second:.2f} pages/s]"
                            + f" doc={doc_fn};"
                            + (f" err={err_msg}" if err_msg else ""))

        except KeyboardInterrupt:
            logger.error(f"KeybordInterrupt. Shutting down AnnotationMonitor.")
            return

        logger.info(f"AnnotationMonitor done.")


def main_logger_process(
        logging_queue: mp.Queue, logfile: pathlib.Path, job_id: str
):
    # create a logger
    logger = logging.getLogger(job_id)
    handler = logging.FileHandler(logfile)
    formatter = logging.Formatter(LOG_FMT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    while True:
        message = logging_queue.get(block=True, timeout=None)

        if message is None:
            break
        # log the message
        logger.handle(message)


def build_dir_structure(out_dir: pathlib.Path):
    multimodal_dir = out_dir / "multimodal"
    meta_dir = out_dir / "meta"
    text_dir = out_dir / "text"
    failed_dir = out_dir / "failed"
    logs_dir = out_dir / "logs"

    multimodal_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    return out_dir, multimodal_dir, meta_dir, text_dir, failed_dir, logs_dir


def main():
    start_time = dt.now()

    # parse input args
    args = get_args()

    # get environment variables
    num_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", joblib.cpu_count()))

    # get job id
    job_id = str(uuid.uuid4()) if args.job_id is None else args.job_id

    if args.input_files is not None:
        with open(args.input_files, "r") as f:
            source_tars = [pathlib.Path(tfp.strip()) for tfp in f.readlines()]
    else:
        source_tars = list(pathlib.Path(args.data_dir).glob("*.tar.gz"))

    # build directory structure for annotations and metadata
    (
        res_dir, multimodal_dir, meta_dir, text_dir, failed_dir, logs_dir
    ) = build_dir_structure(
        out_dir=pathlib.Path(args.output_dir)
    )

    # save config to tgt_root
    shutil.copy(args.config, res_dir / "config.yaml")

    # save args to tgt_root
    with open(res_dir / "args.json", "w") as f:
        json.dump(vars(args), f, indent=4)

    num_worker_processes = min(len(source_tars), max(num_cpus - 2, 1))
    config = load_config(fp=Path(args.config))
    queue_buffer_size = 32 * num_worker_processes

    # setup logging
    log_file = logs_dir / f"{job_id}.log"
    logging_queue = mp.Queue(maxsize=queue_buffer_size)
    logger_p = mp.Process(
        target=main_logger_process, args=(logging_queue, log_file, job_id)
    )
    logger_p.start()

    # create logger
    logger = logging.getLogger(name=job_id)
    logger.addHandler(QueueHandler(logging_queue))
    logger.setLevel(logging.DEBUG)

    # log some info
    logger.info(f"source_tars: {source_tars}")
    logger.info(f"args: {vars(args)}")
    logger.info(f"results_dir: {res_dir}")
    logger.info(f"annotations_dir: {multimodal_dir}")
    logger.info(f"meta_dir: {meta_dir}")
    logger.info(f"text_dir: {text_dir}")
    logger.info(f"failed_dir: {failed_dir}")
    logger.info(f"num_annotators: {num_worker_processes}")

    # setup manager and queues
    results_queue = mp.Queue(maxsize=queue_buffer_size)

    # process that monitors results
    monitor_process = AnnotationMonitor(
        results_queue, logging_queue=logging_queue, target_dir=res_dir,
        job_id=job_id
    )
    monitor_process.start()

    max_docs_per_process = int(args.max_docs) // len(source_tars)
    logger.info(f"max_docs_per_process: {max_docs_per_process}")

    # partition tars into chunks (one chunk per worker process)
    source_tars_chunks = np.array_split(source_tars, num_worker_processes)

    annotator_processes = []

    for i, worker_tars in enumerate(map(list, source_tars_chunks)):
        annotator = AnnotatorProcess(
            annotator_id=f"annotator_{job_id}_{i:04d}",
            soffice_executable=args.soffice_executable,
            annotations_dir=multimodal_dir,
            meta_dir=meta_dir,
            text_dir=text_dir,
            failed_dir=failed_dir,
            crawl_id=args.crawl_id,
            config=config,
            input_tars=worker_tars,
            output_queue=results_queue,
            max_docs=max_docs_per_process,
            logger_name=job_id
        )
        annotator_processes.append(annotator)

    for annotator in annotator_processes:
        annotator.start()

    # wait for annotators to finish
    for annotator in annotator_processes:
        annotator.join()
        logger.info(f"{annotator.annotator_id} done.")

    # signal monitor to stop
    results_queue.put(None)

    # wait for monitor to finish
    monitor_process.join()

    logger.info(f"annotation done.")
    logger.info(f"total time: {dt.now() - start_time}")

    # signal logger to stop
    logging_queue.put_nowait(None)

    # wait for logger to finish
    logger_p.join()


if __name__ == '__main__':
    main()
