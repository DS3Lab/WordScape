import argparse
import os
import urllib.request
import io
import gzip
from datetime import datetime
from pathlib import Path
import settings

parser = argparse.ArgumentParser()
parser.add_argument("--crawl", default=None, type=str,
                    help="Common Crawl crawl")
parser.add_argument("--partition-size", default=13, type=int,
                    help="Partition size")
parser.add_argument("--num_nodes", default=180, type=int,
                    help="number of nodes")
args = parser.parse_args()

DATA_TYPE = "wat"
BASE_URL = "https://data.commoncrawl.org"

LISTINGS_DIR = settings.filesystem.CC_SEGMENT_DIR / (args.crawl + "/listings")


def get_timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def get_idx(idx: int, n_digits: int = 9):
    return "0" * (n_digits - len(str(idx))) + str(idx)


def main():
    # commoncrawl params
    crawl = args.crawl
    partition_size = args.partition_size

    # directory structure
    listings_dir = LISTINGS_DIR

    print(
        "{} Downloading Common Crawl paths listings"
        "\n\t* crawl:          {}"
        "\n\t* data-type:      {}"
        "\n\t* partition-size: {}"
        "\n\t* listings dir:   {}".format(
            get_timestamp(), crawl, DATA_TYPE, partition_size, listings_dir
        )
    )

    listings_url = os.path.join(BASE_URL,
                                f"crawl-data/{crawl}/{DATA_TYPE}.paths.gz")

    # create dir to save partitioned listings
    if not os.path.exists(listings_dir):
        os.makedirs(listings_dir)

    # download listings
    response = urllib.request.urlopen(listings_url)
    compressed_file = io.BytesIO(response.read())
    decompressed_file = gzip.GzipFile(fileobj=compressed_file)
    listings = decompressed_file.read().decode("utf-8").splitlines()

    # partition listings and save as txt files
    idx = 0
    for i in range(0, len(listings), int(partition_size)):
        save_as = os.path.join(
            listings_dir, f"wat.paths.part_{get_idx(idx, n_digits=4)}.txt"
        )

        with open(save_as, "w") as f:
            f.write("\n".join(listings[i: i + int(partition_size)]))

        idx += 1

    # distribute accross node folders
    for i in range(1, args.num_nodes + 1):
        subdir = os.path.join(listings_dir, str(i))
        os.mkdir(subdir)

    files = list(Path(listings_dir).glob('*.txt'))

    curr_subdir = 1
    for f in files:
        f.rename(Path(listings_dir) / str(curr_subdir) / f.name)
        curr_subdir = (curr_subdir % args.num_nodes) + 1


if __name__ == '__main__':
    main()
