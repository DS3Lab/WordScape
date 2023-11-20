import argparse
import itertools
import joblib
import jsonlines
import multiprocessing as mp
import os
from pathlib import Path
from typing import Dict, Union
import warnings
import subprocess

from src.quality.perplexity import LanguageModel

WIKI_LM_URL = "http://dl.fbaipublicfiles.com/cc_net/lm/{lang}.arpa.bin"
WIKI_SP_URL = "http://dl.fbaipublicfiles.com/cc_net/lm/{lang}.sp.model"


def parse_args() -> argparse.Namespace:
    args = argparse.ArgumentParser()
    args.add_argument("--lang", "-l", type=str, required=True)
    args.add_argument("--data", "-d", type=str, required=True,
                      help="Path to data directory containing output of the"
                           "annotation step.")
    return args.parse_args()


def _compute_ppl(
        text_rec: dict, meta_rec: dict, lm: LanguageModel, lang: str
) -> Union[float, None]:
    content = text_rec["text"]

    # identify top lang
    langs: Dict[str, float] = meta_rec["languages_fasttext"]
    top_lang = max(langs, key=langs.get)
    top_lang = top_lang.replace("__label__", "")

    if top_lang == lang:
        # compute perplexity
        perplexity = lm.compute_perplexity(content=content)
    else:
        perplexity = meta_rec.get("perplexity", None)

    return perplexity


def _compute_doclaynet_score() -> Union[float, None]:
    warnings.warn("doclaynet similarity score not implemented yet")
    return None


def process_shard(shard_id: str, data_dir, args: argparse.Namespace):
    print(f"(worker_id={os.getpid()}) start processing shard {shard_id}...")

    # get file paths
    text_fp = data_dir / "text" / f"doc_text_{shard_id}.jsonl"
    meta_fp = data_dir / "meta" / f"doc_meta_{shard_id}.jsonl"

    # make temporary file to store results
    ppl_meta_fp = data_dir / "meta_ppl" / f"temp_doc_meta_{shard_id}.jsonl"

    if not (data_dir / "meta_ppl").exists():
        (data_dir / "meta_ppl").mkdir()
        print(f"(worker_id={os.getpid()}) created directory "
              f"{str(data_dir / 'meta_ppl')}")

    # load models
    sp_fp = Path("resources", "wikipedia-models", f"{args.lang}.sp.model")
    lm_fp = Path("resources", "wikipedia-models", f"{args.lang}.arpa.bin")
    lm = LanguageModel(sp_model=sp_fp, lm_model=lm_fp)

    num_records = 0

    # load data
    with jsonlines.open(ppl_meta_fp, "w") as res_writer:
        with jsonlines.open(text_fp) as text_reader, \
                jsonlines.open(meta_fp) as meta_reader:
            for text, meta in zip(text_reader, meta_reader):
                # compute perplexity
                perplexity = _compute_ppl(text, meta, lm, args.lang)
                meta["perplexity"] = perplexity

                # add to results
                res_writer.write(meta)

                num_records += 1

    print(f"[worker_id={os.getpid()}] done with {shard_id}; "
          f"num_recs: {num_records:<6}")


def _prepare_models(args: argparse.Namespace):
    def _dl_model(url, out_dir: Path):
        subprocess.run(["wget", "-c", "-P", out_dir, url])

    sp_fp = Path("resources", "wikipedia-models", f"{args.lang}.sp.model")
    if not sp_fp.is_file():
        print(f"downloading {args.lang} sentencepiece model...")
        _dl_model(WIKI_SP_URL.format(lang=args.lang), sp_fp.parent)

    lm_fp = Path("resources", "wikipedia-models", f"{args.lang}.arpa.bin")
    if not lm_fp.is_file():
        print(f"downloading {args.lang} Kneser-Ney model...")
        _dl_model(WIKI_LM_URL.format(lang=args.lang), lm_fp.parent)


def main():
    args = parse_args()

    # check if models exist -- if not, downlaoad them.
    _prepare_models(args)

    data_root = Path(args.data)

    if not data_root.exists():
        raise FileNotFoundError(f"could not find data directory: {data_root}")

    text_dir = data_root / "text"

    shard_ids = list(
        s.stem.replace("doc_text_", "") for s in text_dir.glob("*.jsonl")
        if s.is_file() and s.stem.startswith("doc_text_")
    )

    num_workers = joblib.cpu_count() // 2
    print(f"num_workers: {num_workers}")

    with mp.Pool(processes=num_workers) as pool:
        pool.starmap(
            process_shard,
            itertools.product(shard_ids, [data_root], [args])
        )


if __name__ == '__main__':
    main()
