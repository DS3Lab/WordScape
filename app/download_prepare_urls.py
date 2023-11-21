import pandas as pd
import numpy as np
import os
import pathlib
import settings
import argparse

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument("--cc_dump", "-cc", type=str, default=None,
                        help="cc dump being processed")
arg_parser.add_argument("--clean_urls_dir", type=str, default=None)
arg_parser.add_argument("--num_nodes", type=int, default=25,
                        help="number of nodes")
args = arg_parser.parse_args()


def main():
    if args.clean_urls_dir is None:
        clean_urls_dir = settings.filesystem.CLEAN_URLS_DIR
    else:
        clean_urls_dir = pathlib.Path(args.clean_urls_dir)

    # make folder
    write_folder = clean_urls_dir / args.cc_dump
    if not (os.path.exists(write_folder)):
        os.mkdir(write_folder)

    # read parquet file
    clean_list = pd.read_parquet(
        clean_urls_dir / (args.cc_dump + ".parquet")
    )

    # split accross num_nodes
    df_split = np.array_split(clean_list, args.num_nodes)
    for i in range(1, args.num_nodes + 1):
        df_split[i - 1].to_parquet(str(write_folder / (str(i) + ".parquet")))


if __name__ == '__main__':
    main()
