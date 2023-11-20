import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import functools
import multiprocessing as mp
from pathlib import Path
import tarfile
from typing import Set
import hashlib
import polars as pl
from typing import Dict, List
from tqdm import tqdm

# ------ debug
_sources = "/Users/maurice/phd/code/openDoc/WordScape-Data/annotated/cc_main_2022_49/20230601_163415/doc_sources"
_doc_meta = "/Users/maurice/phd/code/openDoc/WordScape-Data/annotated/cc_main_2022_49/20230601_163415/meta_copy/doc.meta.parquet"
# ------ debug

parser = argparse.ArgumentParser()
parser.add_argument("--sources", type=str, default=_sources)
parser.add_argument("--doc_meta", type=str, default=_doc_meta)
parser.add_argument("--out_dir", type=str, default=".")
args = parser.parse_args()


def load_document_ids(meta_fp) -> Set[str]:
    return set((
                   pl.scan_parquet(meta_fp)
                   .select(pl.col("url_hash"))
               ).collect().to_dict()["url_hash"])


def name_to_id(name: str) -> str:
    return name.replace("doc_", "").split(".")[0]


def process_single_file(tar_fp: Path, meta_fp: Path) -> Dict[str, List[str]]:
    document_ids = load_document_ids(meta_fp)
    tar = tarfile.open(tar_fp, 'r:gz')

    data = {
        "url_hash": [], "bytehash": []
    }

    for mem in tar.getmembers():
        url_hash = name_to_id(mem.name)
        if url_hash in document_ids:
            with tar.extractfile(mem) as fobj:
                checksum = hashlib.sha256(fobj.read()).hexdigest()
            data["url_hash"].append(url_hash)
            data["bytehash"].append(checksum)

    return data


def process_all():
    meta_fp = Path(args.doc_meta)
    source_tars = list(Path(args.sources).glob("*.tar.gz"))

    process_fn = functools.partial(process_single_file, meta_fp=meta_fp)

    with ProcessPoolExecutor(max_workers=mp.cpu_count() - 4) as executor:
        futures = list(
            executor.submit(process_fn, tar_fp) for tar_fp in source_tars
        )

        count = 0
        for future in tqdm(as_completed(futures), total=len(futures)):
            single_data = future.result()
            pl.DataFrame(single_data).write_parquet(
                f"{args.out_dir}/checksums-{count}.parquet"
            )
            count += 1
            futures.remove(future)


if __name__ == '__main__':
    process_all()
