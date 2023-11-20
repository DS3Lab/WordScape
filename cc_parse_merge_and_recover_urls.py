"""
Util used after downloading one URL-Batch from CC
- Merges parquet files into one input file for DL script
- Recovers any missed WAT segments into one TXT file
- Deduplicates URLs within one CC Dump
"""

import argparse
import pandas as pd
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
import time

import settings
from src.cc_processing.preprocess_cc_urls import process_urls

BASE_URL = "https://data.commoncrawl.org/"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", "-i", default=None, type=str,
        help="directory containing URL parquets to merge and deduplicate"
    )
    parser.add_argument(
        "--cc_dump", "-cc", default=None, type=str,
        help="cc dump being processed"
    )
    parser.add_argument(
        "--listings_dir", "-ld", type=str, default=None,
        help="listings dir to compare against",
    )
    parser.add_argument(
        "--dedupe", "-dd", type=bool, default=False,
        help="set to true in order to deduplicate current dump compared to "
             "already processed dumps"
    )
    args = parser.parse_args()

    # end-results will be written to here
    write_dir = settings.filesystem.CLEAN_URLS_DIR

    if not Path(write_dir).exists():
        Path(write_dir).mkdir(parents=True)

    pdir = Path(args.input)
    pqfiles = [i for i in pdir.glob('*.parquet')]
    with pq.ParquetWriter(str(pdir / (args.cc_dump + "_merged_raw.parquet")),
                          schema=pa.schema([('url', pa.string())])) as writer:
        for item in pqfiles:
            pqtab = pq.read_table(item)
            # some parquets may be empty (no docx urls in segment)
            if pqtab.schema.equals(writer.schema):
                writer.write_table(pq.read_table(item))

    time.sleep(5)

    # deduplicate parquet
    df = pd.read_parquet(str(pdir / (args.cc_dump + "_merged_raw.parquet")))
    num_undupe_rows = len(df)
    df = df.drop_duplicates()
    num_rows = len(df)
    df.to_parquet(str(pdir / (args.cc_dump + "_merged.parquet")))

    print("total unique URLs: " + str(num_rows) + " removed " + str(
        num_undupe_rows - num_rows) + " duplicates")

    # check if any segments need to be recovered
    lstdir = Path(args.listings_dir)
    lstfiles = [i for i in lstdir.glob('**/*.txt')]
    needed_segments = []
    for item in lstfiles:
        with open(item) as file:
            for line in file:
                needed_segments.append(line.strip())

    logfiles = [i for i in pdir.glob('worker_log_*')]
    gotten_segments = []
    for item in logfiles:
        with open(item) as file:
            last_seen_seg = ''
            for line in file:
                if 'Fetching ' in line:
                    last_seen_seg = line.split('Fetching ')[-1].strip()
                if 'Success! got URL list' in line:
                    gotten_segments.append(last_seen_seg)

    missed_segments = [x for x in needed_segments if
                       ((BASE_URL + x) not in gotten_segments)]

    # write the segments to recover to a txt file
    with open(str(write_dir / (args.cc_dump + "_recovery_segments.txt")),
              'w') as file:
        for item in missed_segments:
            file.write(item + '\n')

    print("sucessfully parsed " + str(
        len(gotten_segments)) + " segments, missed " + str(
        len(missed_segments)))

    # do remaining processing and cleaning of urls
    process_urls(input=str(pdir / (args.cc_dump + "_merged.parquet")),
                 output=str(write_dir / (args.cc_dump + ".parquet")),
                 dedupe=args.dedupe)


if __name__ == '__main__':
    main()
