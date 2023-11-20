r"""Utility module, which globally deduplicates URLs obtained from CC dumps 
(i.e after running this script, a URL will show up only once globally accross all dump parquets)
before passing them to download_docs_ray. Input are parquet files in CLEAN_URLS_DIR,
output is globally deduplicated df."""

import pandas as pd
import os
from pathlib import Path

def dedupe_urls(src_dir: str, input_df: pd.DataFrame) -> pd.DataFrame:
    r"""
    Deduplicate URLs globally: While processing a new URL dump, deduplicate against already processed dumps.
    @param src_dir: dir with parquets to deduplicate against.
    @param input_df: df of URLs currently being processed.
    @raises ValueError: No files in src_dir, or unexpected parquet format.
    
    return: Globally deduplicated df
    """

    # list parquet files in src_dir
    unprocessed = list(filter(lambda x: x.endswith('.parquet'), os.listdir(src_dir)))
    initial_len = len(input_df)
    
    if (len(unprocessed) <= 0):
        raise ValueError("No parquet files found in " + src_dir)
    
    # build initial set (note: set lookup for contains is O(1))
    # ! note individual parquets are already deduped on per-dump basis
    try:
        pqname =  unprocessed.pop()
        curr_df = pd.read_parquet(Path(src_dir, pqname))
    except:
        raise ValueError("Cannot read initial parquet file from " + src_dir)
    try:
        url_hash_tracker = set(curr_df['url_hash'])
    except:
        raise ValueError("Unexpected parquet format, url_hash required (in file) " + pqname)

    # go through each parquet file, and get the hashes
    while (len(unprocessed) > 0):
        pqname = unprocessed.pop()
        curr_df = pd.read_parquet(Path(src_dir, pqname))
        try:
            url_hashes = set(curr_df['url_hash'])
        except:
            raise ValueError("Unexpected parquet format, url_hash required (in file) " + pqname)
        # add to hashes we compare against
        url_hash_tracker = url_hash_tracker.union(url_hashes)

    # remove duplicates
    hash_series = pd.Series(list(url_hash_tracker))
    out_df = input_df[~input_df['url_hash'].isin(hash_series)]
    end_len = len(out_df)

    print('Removed ' + str(initial_len - end_len) + ' duplicates through comparison with already processed dumps')
    return out_df