import pandas as pd
import numpy as np
import os
import settings
import argparse

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--cc_dump", "-cc", type=str, default=None,
                        help="cc dump being processed")
arg_parser.add_argument("--num_nodes", type=int, default=25,
                        help="number of nodes")
args = arg_parser.parse_args()


def main():
    # make folder
    write_folder = settings.filesystem.CLEAN_URLS_DIR / args.cc_dump
    if not (os.path.exists(write_folder)):
        os.mkdir(write_folder)

    # read parquet file
    clean_list = pd.read_parquet(
        settings.filesystem.CLEAN_URLS_DIR / (args.cc_dump + ".parquet"))

    # split accross num_nodes
    df_split = np.array_split(clean_list, args.num_nodes)
    for i in range(1, args.num_nodes + 1):
        df_split[i - 1].to_parquet(str(write_folder / (str(i) + ".parquet")))


if __name__ == '__main__':
    main()
