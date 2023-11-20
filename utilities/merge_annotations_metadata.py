import argparse
import concurrent.futures

import jsonlines
import joblib
import pandas as pd
import pathlib
from typing import Dict
from tqdm import tqdm

FP_PATTERNS = {
    "page": "*page_*.jsonl",
    "doc": "*doc_*.jsonl"
}

FLATTEN_KWS = [
    "annotation_sources"
    "builtin_proportion_per_entity"
]

MAX_ROWS_IN_MEM = 100_000

parser = argparse.ArgumentParser()
parser.add_argument("--meta_dir", type=str, default=None)
args = parser.parse_args()


def _flatten_obj(obj: Dict[str, int], key: str):
    if not isinstance(obj, dict):
        raise ValueError

    return {f"{key}_{k}": v for k, v in obj.items()}


def _serialize(obj):
    if isinstance(obj, list):
        return str(obj)
    return obj


def _to_dataframe(jsonl_fp: pathlib.Path) -> pd.DataFrame:
    df = pd.DataFrame()

    data = {}

    try:
        with jsonlines.open(jsonl_fp) as reader:
            for obj in reader:
                obj_procsd = {
                    k: _serialize(v)
                    for k, v in obj.items() if k not in FLATTEN_KWS
                }
                for k in FLATTEN_KWS:

                    if k not in obj:
                        continue

                    obj_procsd.update(_flatten_obj(obj[k], k))

                if len(data) == 0:
                    data = {k: [v] for k, v in obj_procsd.items()}
                    continue

                for k in data.keys():
                    data[k].append(obj_procsd[k])
    except Exception as e:
        print(f"Failed loading {jsonl_fp} with {e.__class__.__name__}:\n{e}")

    return df.from_dict(data)


def do_merge(level: str, meta_dir: pathlib.Path):
    print(f"start generating {level}-level metadata file")
    fp_pattern = FP_PATTERNS[level]

    meta_files = list(meta_dir.glob(fp_pattern))

    full_df = pd.DataFrame()

    full_df_fp = meta_dir / f"{level}.meta.parquet"
    append = False

    print(f"start generating {level}-level metadata file; "
          f"saving to {full_df_fp}")

    with concurrent.futures.ProcessPoolExecutor(
            max_workers=joblib.cpu_count() - 1
    ) as executor:
        for part_df in (pbar := tqdm(
                executor.map(_to_dataframe, meta_files),
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
    do_merge(level="doc", meta_dir=pathlib.Path(args.meta_dir))
    do_merge(level="page", meta_dir=pathlib.Path(args.meta_dir))
