import argparse
import os
import pandas as pd
from pathlib import Path
from datetime import datetime as dt
import multiprocessing as mp
import joblib
from src.data_sources.download_process import DownloadProcess

# ! shards are now worker-controlled
DEFAULT_TIMEOUT = 8
DEFAULT_RETRIES = 5
DEFAULT_REDIRECTS = 4
DEFAULT_BACKOFF_FACTOR = 0.8
DEFAULT_SUBSET_SIZE = 300000
CPU_PER_WORKER = 2


def get_args() -> argparse.Namespace:
    # parse arguments for job
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--input", "-i", help="path to input file",
                            type=str)
    arg_parser.add_argument("--write_dir", "-wd",
                            help="path to write outputs to", type=str)
    arg_parser.add_argument("--timeout", "-to", help="timeout for requests",
                            type=int,
                            default=DEFAULT_TIMEOUT)
    arg_parser.add_argument("--retries", "-r",
                            help="number of retries for requests",
                            default=DEFAULT_RETRIES, type=int)
    arg_parser.add_argument("--redirects", "-rd",
                            help="number of redirects for requests",
                            default=DEFAULT_REDIRECTS, type=int)
    arg_parser.add_argument("--backoff_factor", "-bf",
                            help="backoff factor for requests",
                            default=DEFAULT_BACKOFF_FACTOR, type=float)
    arg_parser.add_argument("--log_level", "-l", help="log level", type=str,
                            default="INFO")
    arg_parser.add_argument("--subset_size", "-ss", help="subset size",
                            type=int,
                            default=DEFAULT_SUBSET_SIZE)
    arg_parser.add_argument("--num_threads", "-nt",
                            help="number of threads per worker", type=int,
                            default=10)
    arg_parser.add_argument("--num_batch", "-nb",
                            help="number of docs per work batch", type=int,
                            default=10)
    arg_parser.add_argument("--single_url_debug", "-sud",
                            help="single url input, for debugging purposes",
                            default=None)
    args = arg_parser.parse_args()
    return args


def get_timestamp() -> str:
    return dt.now().isoformat()


def sources_iterator():
    pass


class URLBatchProvider(mp.Process):
    def __init__(self, inputs_queue: mp.Queue, source_parquets: str,
                 max_dls: int = -1, num_workers: int = 1):
        """
        Provides URL batches for worker processes to handle.

        @param inputs_queue: Queue to write to.
        @param source_parquets: Directory containing parquets from which to
            draw urls.
        @param max_dls: If greater than 0, max urls to write to queue before
            shutdown.
        @param num_workers: Number of workers reading from the queue.
        """

        super(URLBatchProvider, self).__init__()
        self.inputs_queue = inputs_queue
        self.source_parquets = source_parquets
        self.max_dls = max_dls
        self.num_workers = num_workers

    def run(self):
        """
        The core loop of the process, required by pyhton multiprocessing.
        """

        # enqueue URL batches
        args = get_args()
        if args.single_url_debug is not None:
            self.inputs_queue.put([(args.single_url_debug, "anyhash")])
        else:
            url_iterator = self._url_iterator()
            for batch in url_iterator:
                self.inputs_queue.put(batch)

        # signal workers to stop
        for _ in range(self.num_workers):
            self.inputs_queue.put(None)

    def _url_iterator(self):  # noqa
        """
        An iterator that yields url batches.
        """
        args = get_args()

        # parse the commoncrawl URLs into a dataframe
        urls_df = pd.read_parquet(args.input)
        if args.subset_size > 0:
            urls_df = urls_df.sample(n=args.subset_size)
        # shuffle
        urls_df = urls_df.sample(frac=1)
        # load URL list into memory
        url_list = [(u, h) for u, h in
                    zip(urls_df['url'].tolist(), urls_df['url_hash'].tolist())]

        # yield chunks
        for i in range(0, len(url_list), args.num_batch):
            yield url_list[i:i + args.num_batch]


def main():
    # parse args
    args = get_args()

    num_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", joblib.cpu_count()))

    # determine the CC dump ID
    cc_dump_id = args.input.split('/')[-2]
    node_id = args.input.split('/')[-1]
    if not cc_dump_id.startswith('CC-MAIN'):
        raise NotImplementedError(
            'only commoncrawl sources are supported at the moment.')
    if not node_id.endswith('.parquet'):
        raise NotImplementedError('URLs must be in a parquet file.')

    cc_dump_id = cc_dump_id.replace('.parquet', '')

    if not Path(args.write_dir).exists():
        Path(args.write_dir).mkdir(parents=True, exist_ok=True)

    num_worker_processes = (num_cpus - CPU_PER_WORKER) // CPU_PER_WORKER

    print(f"[{get_timestamp()}] num_downloaders: {num_worker_processes}")

    queue_buffer_size = 4 * num_worker_processes
    inputs_queue = mp.Queue(maxsize=queue_buffer_size)

    download_processes = []
    for i in range(num_worker_processes):
        downloader = DownloadProcess(inputs_queue, cc_dump_id, args.timeout,
                                     args.retries, args.redirects,
                                     args.backoff_factor, args.num_threads,
                                     args.write_dir)
        downloader.start()
        print("started downloader")
        download_processes.append(downloader)

    provider_process = URLBatchProvider(inputs_queue, args.input,
                                        max_dls=args.subset_size,
                                        num_workers=num_worker_processes)
    provider_process.start()

    # wait for provider to finish
    provider_process.join()

    # wait for workers to finish
    for downloader in download_processes:
        downloader.join()


if __name__ == '__main__':
    main()
