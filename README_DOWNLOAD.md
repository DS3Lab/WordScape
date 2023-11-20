# Downloading DOC / DOCX Files from obtained URLS

All instructions are assumed to be executed from the root directory of the project, with the python virtual environment
activated. In this example, we will be downloading files from the commoncrawl dump `CC-MAIN-2023-06`; in the previous
step, we extracted URLs of possible interest to download files from. It is recommended to use absolute paths for
arguments wherever possible, as outlined in the example.

## Preparing URL list for input to nodes

In order to split the downloading task among multiple slurm nodes, the cleaned URL list obtained in the last step must
be subdivided.

To do this, use the command:

```shell
python download_prepare_urls.py --cc_dump CC-MAIN-2023-06 --num_nodes 25
```

The `cc_dump` argument denotes the URL list being processed. After the previous pipeline phase, this list should be
located in `data/clean_urls/{cc_dump}.parquet`.

The `num_nodes` argument must be the same as the number of slurm nodes you intend to run the download job on. If
running via the `launch-download-mp.sbatch`
script, it should be the same as sbatch `array` pragma: e.g. with `array=1-25`, this argument should be set to `25`. If
running locally, this argument should be set to `1`.

After running this command, a folder `data/clean_urls/{cc_dump}` will be created, with .parquet files numbered
1-num_nodes, which will serve as inputs to each slurm node.

## Running download script

Now that the distribution of .parquet files to slurm nodes has been set, we can run the download process.
to run using sbatch, you can use the included script:

```shell
sbatch ./scripts/launch-download-mp.sbatch "./data/clean_urls/CC-MAIN-2023-06" 0 "./data/download/CC-MAIN-2023-06"
```

The first argument should be the folder which we created in the step above. The second argument should be the number of
files each node will attempt to download; if set to 0 or less, each node will attempt to download all its assigned URLs.
The third argument is the folder to which the downloaded files, the metadata parquets and the logs will be written.

To run locally, you may run:

```shell
python download_run.py
--input "./data/clean_urls/CC-MAIN-2023-06/1.parquet"
--subset_size 0
--write_dir "./data/download/CC-MAIN-2023-06"
```

Note that a `/1.parquet` must be added to the end of the input in the local case, as your local machine will be
operating analagously to a single slurm node.
Again, the `subset_size` argument determines how many URLs to attempt to download from before stopping, and `write_dir` the directory all produced files will be written to.

Further customizations (such as max download attempts and allowed redirects) can also be made via the arguments of this
python script.

After sucessful completion of the download job, there will be a folder containing multiple
tar files (each referred to as a 'shard') with the downloaded documents, and a .parquet file containing metadata for
each associated shard, together with log files per spawned worker.
These files will be used in the next and final pipeline step, annotation.

## Dumping metadata to Database

We include a script which will produce exportable URLs (all successful URLs including a bytehash of the URLs file response, to protect against poisoning) and can also be set to dump the metadata to a database (managed with alembic). To run this script:

```shell
python download_dump_data.py
--input "./data/download/CC-MAIN-2023-06"
--urls_dir "./data/clean_urls/CC-MAIN-2023-06"
--write_dir "./data/download_export"
--crawl_id "CC-MAIN-2023-06"
--db_dump
```

The `input` argument should be the directory containing the metadata files, and the `urls_dir` the directory containing the cleaned URLs which were used to initialize the download job (they are needed to perform sanity checks against actually processed URLs, and to generate the end report).

The `write_dir` argument specifies where the exportable URL files are written to, and `crawl_id` should be set as usual. The `db_dump` flag, if set, will write all download metadata to the `doc_sources` table.

#### Database Management

To create a new migration, add models in orm/models.py, then run

```shell
alembic revision --autogenerate -m "Migration message here"
```

To update the database after creating new migrations, run

```shell
alembic upgrade heads
```

Note you must have psycopg2-binary installed, which does not always come through using requirements.txt.

```shell
pip install psycopg2-binary
```

Also, ensure that the database connection string in alembic.ini is correct.
