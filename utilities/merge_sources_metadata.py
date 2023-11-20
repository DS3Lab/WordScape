import argparse
import concurrent.futures
import joblib
import pandas as pd
import pathlib
from tqdm import tqdm

MAX_ROWS_IN_MEM = 100_000


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--meta_dir", type=str, default=None)
    args = parser.parse_args()
    return args


def _load_parquet(meta_fp: pathlib.Path):
    return pd.read_parquet(meta_fp)


def main():
    args = get_args()
    data_dir = pathlib.Path(args.meta_dir)
    dump_id = data_dir.name

    meta_files = list(data_dir.glob("*.parquet"))

    print("Found", len(meta_files), "source meta files")

    full_df = pd.DataFrame()
    full_df_fp = data_dir.parent / f"sources_{dump_id}.meta.parquet"

    append = False

    with concurrent.futures.ProcessPoolExecutor(
            max_workers=joblib.cpu_count() - 2
    ) as executor:
        for part_df in (pbar := tqdm(
                executor.map(_load_parquet, meta_files),
                total=len(meta_files)
        )):
            full_df = pd.concat([full_df, part_df], ignore_index=True)
            rows_in_mem = len(full_df)

            if rows_in_mem > MAX_ROWS_IN_MEM:
                full_df.to_parquet(
                    path=full_df_fp, append=append, engine="fastparquet"
                )
                pbar.set_postfix_str(
                    f"wrote to {full_df_fp} with append={append}"
                )
                append = True
                full_df = pd.DataFrame(columns=full_df.columns)

    if len(full_df) > 0:
        full_df.to_parquet(
            path=full_df_fp, append=append, engine="fastparquet"
        )

    del full_df


if __name__ == '__main__':
    main()
