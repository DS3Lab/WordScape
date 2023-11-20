import numpy as np
from orm.dbutils.db_connection import connect_to_db
import orm.models
import pyarrow.parquet as pqr
import argparse
import pandas as pd
from pathlib import Path
from alive_progress import alive_bar


def init_or_add_to_count_map(mapping: dict, key, count: int) -> dict:
    if key.strip() in mapping:
        mapping[key.strip()] += count
    else:
        mapping[key.strip()] = count

    return mapping


def error_check(tracker: dict, err_str: str):
    # covers large majority of errors

    if "HTTP HEAD request" in err_str:

        if "HTTPError" in err_str:
            http_err_num = err_str.split('=')[-1]
            init_or_add_to_count_map(tracker, "HTTP-" + str(http_err_num), 1)

        elif "MaxRetryError" in err_str:
            init_or_add_to_count_map(tracker, "HTTP-MaxRetry", 1)

        elif "InvalidContentType" in err_str:
            init_or_add_to_count_map(tracker, "HTTP-ContentType", 1)

        elif (("InvalidURL" in err_str) or ("Invalid URL" in err_str) or (
                "InvalidSchema" in err_str)):
            init_or_add_to_count_map(tracker, "HTTP-InvalidURL", 1)

        elif "TooManyRedirects" in err_str:
            init_or_add_to_count_map(tracker, "HTTP-TooManyRedirects", 1)

        else:
            init_or_add_to_count_map(tracker, "HTTP-Other", 1)

    elif "HTTP GET no response" in err_str:
        init_or_add_to_count_map(tracker, "HTTP-None", 1)

    elif ("max filesize" in err_str) or ("FileSizeExceeded" in err_str):
        init_or_add_to_count_map(tracker, "MaxFileSize", 1)

    elif "maldoc not passed" in err_str:
        malcode = err_str.split(':')[-1]
        malcode_splits = malcode.split(',')
        for split in malcode_splits:
            if '=' in split:
                actual_code = split.split('=')[0]
                init_or_add_to_count_map(tracker,
                                         "maldoc-" + actual_code.strip(), 1)
            elif 'suspicious' in split:
                init_or_add_to_count_map(tracker, "maldoc-suspicious", 1)

    elif not ("Batch handler" in err_str):
        init_or_add_to_count_map(tracker, "Other", 1)


def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--input", "-i",
                            help="path to folder containing parquets",
                            type=str,
                            default="/data/download/CC-MAIN-2013-48")
    arg_parser.add_argument("--urls_dir", "-ud",
                            help="path to folder containing original parquets slated for download",
                            type=str,
                            default="/data/clean_urls/CC-MAIN-2013-48")
    arg_parser.add_argument("--write_dir", "-wd",
                            help="directory where parquets cleaned for export are stored",
                            type=str,
                            default="/data/download_export")
    arg_parser.add_argument("--crawl_id", "-cc", help="CC crawl name",
                            type=str,
                            default="CC-MAIN-2013-48")
    arg_parser.add_argument("--db_dump", "-dd",
                            help="set this to not only produce exportable URLs and report, but to dump metadata to the DB",
                            action='store_true')
    args = arg_parser.parse_args()

    # get type info for conversion
    table_model = orm.models.SourcesRecordDB.__table__
    column_types = {c.name: c.type for c in table_model.columns}

    print("checking logs")

    logs = list(Path(args.input).glob("worker_log*"))
    strange_workers = []
    batch_failures = 0
    reg_workers = 0
    log_urls = 0
    log_files = 0
    err_tracker = {}
    for log in logs:
        log_files += 1
        with open(log) as file:
            data = file.read()
            occ_term = data.count("INFO::Regularly terminated worker")
            occ_dl = data.count("INFO::downloading doc")
            if (occ_dl % 100) != 0:
                strange_workers.append(log)
            occ_batch = data.count("Batch handler error!")
            batch_failures += occ_batch
            log_urls += occ_dl
            reg_workers += occ_term
            file.seek(0)
            for line in file:
                if "ERROR::" in line:
                    error_check(err_tracker, line)

    print("workers started: " + str(
        log_files) + " / terminated regularly: " + str(reg_workers))
    print("processed urls log check " + str(log_urls))

    print("preparing bytehash dedupe")

    # get already processed parquets
    processed_pqs = list(Path(args.write_dir).glob("*.parquet"))
    processed_bytehashes = []
    with alive_bar(len(processed_pqs)) as bar:
        for pq in processed_pqs:
            df = pd.read_parquet(pq)
            hashlist = df['bytehash'].tolist()
            processed_bytehashes = processed_bytehashes + hashlist
            bar()
    processed_bytehashes = set(processed_bytehashes)

    print("checking DB parquets")

    # go through each parquet file and dump it
    source_pqs = list(Path(args.input).glob("*.parquet"))
    urls_processed = 0
    urls_processed_doublecheck = 0
    unique_url_hashes = []
    skipped_urls_db = 0
    all_dfs = []

    with alive_bar(len(source_pqs)) as bar:
        for pq in source_pqs:
            df = pd.read_parquet(pq)
            tab = pqr.read_table(pq)
            urls_processed += len(df)
            urls_processed_doublecheck += tab.num_rows
            # convert data types
            for column_name, _ in column_types.items():
                if column_name in df.columns:
                    df[column_name] = df[column_name].astype(str)

            all_dfs.append(df)
            bar()

    print("merging and cleaning for export")

    merged_df = pd.concat(all_dfs)
    # also exclude the "None" value
    processed_bytehashes.add("None")
    filtered_df = merged_df[~merged_df['bytehash'].isin(processed_bytehashes)]
    final_df = filtered_df.drop_duplicates(subset='bytehash', keep='last')
    final_df = final_df[['url', 'url_hash', 'crawl_id', 'bytehash']]
    final_df.to_parquet(Path(args.write_dir) / (args.crawl_id + ".parquet"),
                        index=False)

    processed_urls = merged_df['url'].tolist()
    alive_urls = final_df['bytehash'].tolist()

    # get required URLs to DL
    print("comparing to original cleaned URLs")
    required_pqs = list(Path(args.urls_dir).glob("*.parquet"))
    required_urls = []
    with alive_bar(len(required_pqs)) as bar:
        for pq in required_pqs:
            df = pd.read_parquet(pq)
            dlist = df['url'].tolist()
            required_urls = required_urls + dlist
            bar()

    required_urls_unique = list(set(required_urls))
    print("required urls total " + str(len(required_urls)))
    print("required urls unique " + str(len(required_urls_unique)))
    processed_urls_unique = list(set(processed_urls))
    print("processed urls total " + str(len(processed_urls)))
    print("processed urls unique " + str(len(processed_urls_unique)))
    missing_urls_unique = list(
        set(required_urls_unique) - set(processed_urls_unique))
    print("missing URLs " + str(len(missing_urls_unique)))

    url_hash_set = list(set(unique_url_hashes))
    print("processed urls " + str(urls_processed))
    print("processed urls raw parquet " + str(urls_processed_doublecheck))
    print("processed urls unique hash check " + str(len(url_hash_set)))
    print("total processed URLs without dedupe " + str(len(unique_url_hashes)))
    print("alive urls " + str(len(alive_urls)))
    print("unique bytehashes " + str(len(list(set(alive_urls)))))

    print("SUMMARY")
    print("required unique: " + str(
        len(required_urls_unique)) + " | processed unique: " + str(
        len(processed_urls_unique)) + " | missed unique: " + str(
        len(missing_urls_unique)) + " | successfuly DLed unique (bytehash): " + str(
        len(alive_urls)))
    print("ERRORS")
    print(err_tracker)

    if args.db_dump:
        print("dumping metadata to DB")

        # get the engine
        engine = connect_to_db()

        # dump the df to db
        # first take care of some typing problems
        df = df.replace(to_replace="None", value=np.nan)
        df = df.where(pd.notnull(df), None)
        df["content_language"] = df["content_language"].str.split(",")

        # note this takes uniqueness of url_hash constraint into account
        # automatically, by skipping on integrityerrors
        with alive_bar(len(df)) as bar:
            for _, row in df.iterrows():
                try:
                    row.to_frame().T.to_sql('sources_record', engine,
                                            if_exists='append', index=False)
                except Exception as _:
                    # print("skipping duplicate / unclean row")
                    skipped_urls_db += 1
                bar()

        print("bad records skipped: " + str(skipped_urls_db))


if __name__ == '__main__':
    main()
