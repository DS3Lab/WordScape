import argparse
import joblib
import multiprocessing as mp
import os
from pathlib import Path

from src.cc_processing.cc_url_process import CCURLProcess
import settings

BASE_URL = "https://data.commoncrawl.org/"


class URIBatchProvider(mp.Process):
    def __init__(self, inputs_queue: mp.Queue, listings_dir: str, parts: int,
                 num_workers: int):
        """
        Provides warc URIs to cc_url processes input queue. 

        @param inputs_queue: Queue to write uris to
        @param listings_dir: Directory containing wat file part listings to be
            distributed to worker processes
        @param parts: Number of parts to proccess
        @param num_workers: Number of workers to supply with uris
        """

        super(URIBatchProvider, self).__init__()
        self.inputs_queue = inputs_queue
        self.listings_dir = listings_dir
        self.parts = parts
        self.num_workers = num_workers

    def run(self):
        """
        Core process loop required by python multiprocessing
        """

        parts_dir = Path(self.listings_dir)

        for parts_file in parts_dir.glob('*.txt'):
            with parts_file.open() as file:
                contents = file.read()
                processed_contents = list(
                    map(lambda x: BASE_URL + x, contents.split('\n')))
                # split individually over all cores --> better DL parallelism
                for s in processed_contents:
                    self.inputs_queue.put([s])

        for _ in range(self.num_workers):
            self.inputs_queue.put(None)


def get_args() -> argparse.Namespace:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--input", "-i",
                            help="path to folder containing URL listing parts",
                            type=str, default=None)
    arg_parser.add_argument("--parts", "-p",
                            help="number of parts files to process, -1 for all",
                            type=str, default=-1)
    arg_parser.add_argument("--cc_dump", "-cc", help="cc dump being processed",
                            type=str, default="CC-MAIN-2023-06")
    args = arg_parser.parse_args()
    return args


def main():
    args = get_args()

    num_cpus = int(os.environ.get("SLURM_CPUS_PER_TASK", joblib.cpu_count()))

    # make cc dir if not yet existant
    if not Path.exists(settings.filesystem.CC_DIR):
        Path.mkdir(settings.filesystem.CC_DIR)
    if not Path.exists(settings.filesystem.CC_DIR / args.cc_dump):
        Path.mkdir(settings.filesystem.CC_DIR / args.cc_dump)

    num_worker_processes = num_cpus - 2

    queue_buffer_size = 4 * num_worker_processes
    inputs_queue = mp.Queue(maxsize=queue_buffer_size)

    cc_processes = []
    for i in range(num_worker_processes):
        cc_process = CCURLProcess(inputs_queue, BASE_URL, args.cc_dump)
        cc_process.start()
        print("started cc_url parser")
        cc_processes.append(cc_process)

    # provide URI batches
    provider_process = URIBatchProvider(inputs_queue, args.input, 10, 1)
    provider_process.start()
    provider_process.join()

    # wait for workers to finish
    for cc in cc_processes:
        cc.join()


if __name__ == '__main__':
    main()
