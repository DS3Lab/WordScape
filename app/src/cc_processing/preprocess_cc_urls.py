from datetime import datetime
import pandas as pd
import regex as re
import hashlib
import urllib.parse
from typing import Union
from src.cc_processing.deduplicate import dedupe_urls
import settings

# regex patterns
CC_ID_PATTERN = re.compile(r'CC-MAIN-[0-9]{4,4}-[0-9]{2,2}')


def get_timestamp():
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def get_source_from_filename(fp: str) -> str:
    """get crawl name from csv filename
    @fp: str path to file
    return: str crawl name
    """
    # commoncrawl sources
    matches = CC_ID_PATTERN.findall(fp)
    if len(matches) != 0:
        return matches[0]

    raise NotImplementedError(
        f"only commoncrawl sources are supported at the moment; "
        f"got {fp}")


def clean_url(
        row: pd.Series, start_pattern: re.Regex, end_pattern: re.Regex
) -> Union[str, None]:
    """ this function converts a string to a valid url
    @param row: pd.Series$
    @param start_pattern: Regex pattern to match the start of the url (http, https or www)
    @param end_pattern: Regex pattern to match the end of the url (.doc or .docx)
    return: str url
    """
    url = str(row.url)
    url = urllib.parse.unquote(url)
    urls_starts = sorted([m.start() for m in start_pattern.finditer(url)])
    urls_ends = sorted([m.end() for m in end_pattern.finditer(url)],
                       reverse=True)

    if len(urls_starts) == 0 or len(urls_ends) == 0:
        return None

    if len(urls_starts) == 1:
        return url[urls_starts[0]:urls_ends[-1]]

    if len(urls_ends) == 1:
        return url[urls_starts[-1]:urls_ends[0]]

    if urls_starts[-1] < urls_ends[-1]:
        # no overlap: in this case we take the url in the middle
        return url[urls_starts[-1]:urls_ends[-1]]

    sub_urls = []
    for i in range(len(urls_starts) - 1):
        if urls_starts[i + 1] < urls_ends[-1]:
            continue
        sub_urls.append(url[urls_starts[i]:urls_ends[-1]])
        urls_ends.pop()

    # in case multiple urls are found, return the first one
    return sub_urls[0]


def load_urls(filepath: str) -> pd.DataFrame:
    """load parquet file into pandas DataFrame
    @param filepath: str filepath
    return: pandas DataFrame
    """
    df = pd.DataFrame({
        'doc_id': pd.Series([], dtype='str'),
        'url': pd.Series([], dtype='str'),
        'url_hash': pd.Series([], dtype='str'),
        'source': pd.Series([], dtype='str')
    })

    fp = filepath

    if not fp.endswith('.parquet'):
        print("WARNING: skipping file {} (not a parquet file)")
        return

    temp_df = pd.read_parquet(fp, columns=['url'])
    temp_df['url'] = temp_df['url'].astype(str)

    # compute hash for each url (used for deduplication)
    temp_df['url_hash'] = temp_df['url'].apply(
        lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest()
    )

    # get source name from filename (currently only commoncrawl is supported
    source = get_source_from_filename(fp)
    temp_df['source'] = source

    df = pd.concat([df, temp_df], ignore_index=True)
    print("loaded {:,} urls".format(len(df)))

    return df


def process_urls(input: str, output: str, dedupe: bool):
    """
    Core function to process and clean urls.

    @param input: Directory containing raw parquets
    @param output: filename base of created cleaned parquets
    @param dedupe: If true, deduplicate URLs globally
    """

    # load urls from csv files
    print("{} loading urls from parquet file".format(get_timestamp()))
    df = load_urls(input)

    print(df.head(10))

    # drop duplicates
    df = df.drop_duplicates(subset=['url_hash'])
    df = df.reset_index(drop=True)

    # make index
    print("{} building document ids".format(get_timestamp()))
    df['doc_id'] = df['source'] + "-"
    indices = df.groupby('source').cumcount().astype(str).str.zfill(9)
    df['doc_id'] = df['doc_id'] + indices

    # clean urls
    print("{} preprocessing urls".format(get_timestamp()))
    start_pattern = re.compile(r'(http|https)')
    end_pattern = re.compile(r'(\.docx|\.doc)')
    df['url'] = df.apply(lambda x: clean_url(x, start_pattern, end_pattern),
                         axis=1)

    # drop missing values
    df.dropna()

    # make hash index
    df = df.set_index('doc_id')

    if dedupe:
        df = dedupe_urls(
            src_dir=str(settings.filesystem.CLEAN_URLS_DIR),
            input_df=df
        )

    print("{} writing cc dump parquet files".format(get_timestamp()))
    df.to_parquet(output, index=True)
    print(f"{get_timestamp()} wrote {output} with {len(df):,} urls")
