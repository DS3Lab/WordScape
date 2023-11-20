# Getting DOC / DOCX URLS from CommonCrawl

All instructions are assumed to be executed from the root directory of the project, with the python virtual environment
activated. In this example, we will be processing the commoncrawl dump `CC-MAIN-2023-06`. It is recommended to use
absolute paths for arguments wherever possible, as outlined in the example.

## Preparing WAT segment partitions for input to nodes

Extraction of relevant URLs is based on metadata supplied by the WAT files of a given commoncrawl dump.
In order to prepare for downloading URLs, we must therefore first split the responsibility of
downloading dumps accross slurm nodes. Each slurm node will in turn assign individual
WAT files to be downloaded and processed by workers.

In order to prepare these files, run

```shell
python cc_parse_partition_listings.py --crawl CC-MAIN-2023-06 --partition-size 13 --num_nodes 180
```

The `crawl` argument specifies which cc dump to process.

The `partition_size` argument influences the internal task distribution of one slurm node; ideally, it should be set to
the number of cores on each node minus 3; if running locally, it should be set to the number of cores your CPU has.

The `num_nodes` argument must be the same as the number of slurm nodes you intend to run the download job on. If running
via the `cc-parse-launch.sbatch`
script, it should be the same as sbatch `array` pragma: e.g. with `array=1-180`, this argument should be set to `180`.
If running locally, this argument should be set to `1`.

Running this script will output the listings directory to which the results have been written; take note of this, as it
will be needed in the next step:

```shell
[2023-05-25 20:04:38] Downloading Common Crawl paths listings
        * crawl:          CC-MAIN-2023-06
        * data-type:      wat
        * partition-size: 13
        * listings dir:   ./data/crawl-data/CC-MAIN-2023-06/listings
```

## Running URL download process

Now that the distribution of WAT files to slurm nodes and their respective worker processes have been set, we can run
the download process.
To run using sbatch, you can use the included script:

```shell
sbatch ./scripts/cc-parse-launch.sbatch "./data/crawl-data/CC-MAIN-2023-06/listings" "CC-MAIN-2023-06"
```

The first argument must be the listings directory from the output in the last step, and the second the name of the cc
dump (same as above).

In order to run locally, you can use:

```shell
python cc_parse_snapshot.py  \
--input "./data/crawl-data/CC-MAIN-2023-06/listings/1" \
--cc_dump "CC-MAIN-2023-06"
```

Note that a `/1` must be added to the end of the listings directory in the local case, as your local machine will be
operating analagously to a single slurm node.

These processes will then begin outputting raw URL data to the `cc_urls` data folder.

## Cleanup, merge and recovery

After the raw URL download job completes, the produced URLs must be cleaned and merged into a single parquet file in
the `clean_urls` folder for the next steps of the pipeline.

To do this, you can run:

```shell
python cc_parse_merge_and_recover_urls.py \
--input ./data/cc_urls/CC-MAIN-2023-06 \
--listings_dir ./data/crawl-data/CC-MAIN-2023-06/listings \
--cc_dump CC-MAIN-2023-06 \
--dedupe 1
```

The `input` argument must be the `cc_urls` directory being cleaned.

The `listings_dir` and `cc_dump` arguments are the same as above.

If the `dedupe` flag is set, the resulting parquet file will be globally deduplicated against all already processed
dumps inside the `clean_urls` folder; it is recommended to set this flag if you intend to process multiple dumps.

After completing these steps, you should have one parquet file with a list of cleaned
URLS: `./data/clean_urls/CC-MAIN-2023-06.parquet`.

Note that, due to contention on commoncrawl resources, it is possible that some WATs were not able to be processed.
These will be written to `./data/clean_urls/CC-MAIN-2023-06_recovery_segments.txt`, and a report will be output by the
script on how many (if any) segments were missed. Optionally, you may
re-run the download job at a later time, using only these segments as input.

After completing the above steps, you should be ready to move on to the download phase of the pipeline.
