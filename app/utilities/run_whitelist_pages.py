import argparse
import pandas as pd
import pathlib
import json
import numpy as np
import os

# corresponds to discarding all docs with text perplexity > 80th percentile
PERPLEXITY_PERCENTILE = 80

# minimum confidence threshold for language prediction
LANG_PRED_THRESHOLD = 0.5

# language to exclude
EXCLUDE_LANGS = []


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_root", type=str, default=None,
                        help="Path to the root of the data directory")
    args = parser.parse_args()
    return args


def perplexity_filter(doc_data: pd.DataFrame):
    perplexity_stats = doc_data[(~doc_data.perplexity.isna())][
        ["top_lang", "perplexity"]
    ].groupby("top_lang").agg({
        "perplexity": [lambda x: np.percentile(x, PERPLEXITY_PERCENTILE)]
    })

    thresholds = {
        k: float(perplexity_stats.loc[k, "perplexity"])
        for k in perplexity_stats.index
    }

    def get_bucket(r: pd.Series):
        if np.isnan(r.perplexity):
            return None
        if r.perplexity > thresholds[r.top_lang]:
            return "high"
        else:
            return "low-mid"

    doc_data["bucket"] = doc_data[["top_lang", "perplexity"]].apply(
        lambda p: get_bucket(p), axis=1)

    blacklist_docs = list(doc_data[doc_data.bucket == "high"].url_hash)

    return blacklist_docs


def fiter_data(
        doc_data: pd.DataFrame, page_data: pd.DataFrame
) -> pd.DataFrame:
    doc_data["fn_extension"] = doc_data["sources_filename"].apply(
        lambda s: os.path.splitext(s)[-1]
    )
    # 0) exclude predefined languages
    blacklist_docs = list(
        doc_data[doc_data.top_lang.isin(EXCLUDE_LANGS)].url_hash
    )
    print(f"Discarding {len(blacklist_docs)} cyrillic docs.")

    # 1) Document level filters
    # blacklist all docxs with annotation_quality_score < median
    median_quality = doc_data.annotation_quality_score.median()
    blacklist_docs_low_quality = list(
        doc_data[doc_data.annotation_quality_score < median_quality].url_hash
    )
    print(f"Discarding {len(blacklist_docs)} docs "
          f"with low annotation quality.")
    blacklist_docs.extend(blacklist_docs_low_quality)

    # blacklist all docs that don't have a perplexity score
    blacklist_no_ppl = list(doc_data[doc_data.perplexity.isnull()].url_hash)
    print(f"Discarding {len(blacklist_no_ppl)} docs without perplexity score.")
    blacklist_docs.extend(blacklist_no_ppl)

    blacklist_docs_high_ppl = perplexity_filter(doc_data)
    blacklist_docs.extend(blacklist_docs_high_ppl)
    print(f"Discarding {len(blacklist_docs_high_ppl)} docs "
          f"with high perplexity.")

    black_list_docs_unknown_lang = list(
        doc_data[doc_data.top_lang == "__label__unknown"].url_hash
    )
    blacklist_docs.extend(black_list_docs_unknown_lang)
    print(f"Discarding {len(black_list_docs_unknown_lang)} docs "
          f"with unknown language.")

    blacklist_docs = set(blacklist_docs)

    # blacklist all docs that have perplexity score < 0.33 percentile of all
    # docs per language
    print("Blacklisted docs: ", len(blacklist_docs))

    # # 2) Page level filters
    # filter pages that are not in the blacklist
    num_pre_filter = len(page_data)
    page_data = page_data[~page_data.url_hash.isin(blacklist_docs)]
    print("Removed {} pages based on doc blacklist.".format(
        num_pre_filter - len(page_data)
    ))

    # filter pages with less then WORD_COUNT_PERCENTILE words
    num_pre_filter = len(page_data)
    page_data = page_data[page_data.pdf_word_count > 0]
    print("Removed {} pages without words.".format(
        num_pre_filter - len(page_data)
    ))

    # discard all pages that have no entities
    num_pre_filter = len(page_data)
    page_data["num_entities"] = page_data[
        [col for col in page_data.columns if col.startswith("num_")]].sum(
        axis=1)
    page_data = page_data[page_data.num_entities > 0]
    print(f"Removed {num_pre_filter - len(page_data)} pages without entities.")

    # filter all pages that have only headings
    non_heading_cols = [
        col for col in page_data.columns if (
                not col.startswith("num_heading") and col.startswith("num_")
        )
    ]

    num_pre_filter = len(page_data)
    page_data = page_data[
        ~(
                (
                        page_data.num_heading_1 + page_data.num_heading_2 +
                        page_data.num_heading_3 + page_data.num_heading_4 +
                        page_data.num_heading_5 + page_data.num_heading_6 +
                        page_data.num_heading_7 + page_data.num_heading_8 +
                        page_data.num_heading_9 > 0
                ) & (
                        page_data[non_heading_cols].sum(axis=1) == 0
                )
        )
    ]

    print("Removed {} pages that contain only headings.".format(
        num_pre_filter - len(page_data)
    ))

    # language filters
    num_pre_filter = len(page_data)
    page_data = page_data[page_data.top_lang_score > LANG_PRED_THRESHOLD]
    print("Removed {} pages with low language prediction confidence.".format(
        num_pre_filter - len(page_data)
    ))

    return page_data


def main():
    # parse args
    args = parse_args()
    data_path = pathlib.Path(args.data_root)

    # load metadata
    doc_meta_data = pd.read_parquet(data_path / "doc.meta.parquet")
    print("loaded doc meta data")

    # extract top language for each document
    page_meta_data = pd.read_parquet(data_path / "page.meta.parquet")
    print("loaded page meta data")

    total_num_pages = len(page_meta_data)
    print("Number of pages before filtering: ", total_num_pages)

    # filter data
    page_meta_data = fiter_data(doc_meta_data, page_meta_data)

    print("Number of pages after filtering: {} (-{:.2f}) ".format(
        len(page_meta_data), 100 * (1 - len(page_meta_data) / total_num_pages)
    ))

    # group page_ids by annotated_shard_id
    shard_ids = page_meta_data.annotated_shard_id.unique()
    whitelist_pages = {
        shard_id: page_meta_data[
            page_meta_data.annotated_shard_id == shard_id].page_id.tolist()
        for shard_id in shard_ids
    }

    with open(data_path / "whitelist_pages.json", "w") as f:
        f.write(json.dumps(whitelist_pages))


if __name__ == '__main__':
    main()
