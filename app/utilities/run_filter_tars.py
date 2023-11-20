import argparse
import pathlib
import tarfile
import multiprocessing as mp
import json
from typing import List, Tuple, Union
from pathlib import Path

import joblib

parser = argparse.ArgumentParser()
parser.add_argument("--data_root", type=str, default=None)
args = parser.parse_args()


def get_page_id(fn: str) -> str:
    return fn[fn.find("doc_"):].replace("doc_", "")


def filter_tar_file(
        inputs: Tuple[pathlib.Path, List[str]]
) -> Union[int, None]:
    src_tar_fp, whitelist_pages = inputs

    whitelist_pages = set(get_page_id(p) for p in whitelist_pages)

    filtered_tar_fn = src_tar_fp.name.replace(".tar.gz", ".filtered.tar.gz")
    filtered_tar_fp = src_tar_fp.parent / filtered_tar_fn

    src_tar = tarfile.open(src_tar_fp, 'r:gz')
    tgt_tar = tarfile.open(filtered_tar_fp, 'w:gz')

    try:
        all_jpg_members = set(
            get_page_id(Path(mem.name).stem) for mem in src_tar.getmembers()
            if mem.name.endswith(".jpg")
        )
        all_txt_members = set(
            get_page_id(Path(mem.name).stem) for mem in src_tar.getmembers()
            if mem.name.startswith("text_doc_")
        )
        all_ent_members = set(
            get_page_id(Path(mem.name).stem) for mem in src_tar.getmembers()
            if mem.name.startswith("entities_doc_")
        )
        all_wrd_members = set(
            get_page_id(Path(mem.name).stem) for mem in src_tar.getmembers()
            if mem.name.startswith("words_doc_")
        )

        all_page_ids = all_jpg_members & all_txt_members \
                       & all_ent_members & all_wrd_members

        filtered_pages = all_page_ids & whitelist_pages

        # write all matching members to target tar
        num_files = 0
        for mem in src_tar.getmembers():
            num_files += 1
            page_id = get_page_id(Path(mem.name).stem)
            if page_id not in filtered_pages:
                continue

            fobj = src_tar.extractfile(mem)
            fobj.seek(0)

            # write to target tar
            tgt_tar.addfile(mem, fobj)

    except Exception as e:
        print("Error processing: ", src_tar_fp)
        tgt_tar.close()
        src_tar.close()
        filtered_tar_fp.unlink(missing_ok=True)
        print(e)
        return 0

    num_filtered_files = len(filtered_pages) * 4
    print("Processed: ", src_tar_fp)
    print(f"Total files: {num_files}, Filtered files: {num_filtered_files}")

    tgt_tar.close()
    src_tar.close()

    return 1


def main():
    data_root = pathlib.Path(args.data_root)
    annotations_dir = data_root / "multimodal"
    paths = list(annotations_dir.glob("*.tar.gz"))
    total_paths = len(paths)

    if total_paths == 0:
        print("No files found in: ", args.data_root)
        return

    # load whitelisted urls
    with open(data_root / "whitelist_pages.json", 'r') as f:
        whitelist_pages = json.load(f)

    # construct inputs
    inputs = list()
    for path in paths:
        shard_id = path.name.replace("docs_", "").replace(".tar.gz", "")
        try:
            inputs.append((path, whitelist_pages[shard_id]))
        except KeyError:
            print("No whitelist for: ", shard_id)
            continue

    with mp.Pool(processes=joblib.cpu_count() - 1) as pool:
        res_codes = pool.map(filter_tar_file, inputs)

    print("Total files: ", total_paths)
    print("Total filtered files: ", sum(res_codes))


if __name__ == '__main__':
    main()
