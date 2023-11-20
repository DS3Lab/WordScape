# Annotation of Word files

All instructions are assumed to be executed from the root directory of the project, with the python virtual environment
activated and all necessary dependencies installed. In this example, we will be processing the word files downloaded in
the previous step of the WordScape pipeline.

This part of WordScape assumes that you have input files (i.e. Word .doc or .docx files) stored in
gzip compressed tar archives:

```
DATA_DIR
├── archive_1.tar.gz
    ├── file_1.doc
    ├── file_2.docx
    ...
    ├── file_k.doc
├── archive_2.tar.gz
    ├── file_1.doc
    ...
├── archive_n.tar.gz
```

The Word Scape pipeline will process each archive in parallel. The output will have the following components:

- A `failed` directory with jsonl files that contain the filenames of Word files that failed to process, including the
  reason for
  failure.
- A `logs` directory with log files from each worker.
- A `meta` directory with jsonl files that contain metadata on document level, and metadata on page level.
- A `multimodal` directory with tar.gz files that contain multimodal data for each document. The multimodal data
  includes images of each page, and json files that contain OCR text, word bounding boxes, and entity bounding boxes.
- A `text` directory with jsonl files that contain OCR text for each document and each page.
- A `version_info.txt` file that contains the timestamp and git branch and commit hash of the code used to process the
  data.
- A `args.json` file that contains the arguments used to run the pipeline.
- A `config.yaml` file that contains the configuration used to run the pipeline.

The output directory structure will look like this:

```
./data/annotated/<CC_DUMP_ID>/<timestamp>/
├── failed
    ├── failed_<shard_id>.jsonl
    ...
├── logs
    ├── <worker_id>.log
    ...
├── meta
    ├── doc_meta_<shard_id>.jsonl
    ├── page_meta_<shard_id>.jsonl
    ...
├── multimodal
    ├── docs_<shard_id>.tar.gz
        ├── doc_<url_hash>_p<page_num>.jpg
        ├── entities_<url_hash>_p<page_num>.json
        ├── text_<url_hash>_p<page_num>.json
        ├── words_<url_hash>_p<page_num>.json
        ...
    ...
├── text
    ├── doc_text_<shard_id>.jsonl
    ├── page_text_<shard_id>.jsonl
    ...
├── version_info.txt
├── args.json
├── config.yaml
```

## Running annotation scripts

Here we describe how to run the annotation scripts. The scripts are designed to be run on a Slurm cluster, but can also
be run locally.

### Running on a Slurm cluster

To run WordScape on a Slurm cluster, you can use the `annotation-kickoff.sh` script from the `scripts` directory.
This script will divide all files ending in `.tar.gz` into partitions. Each partition will be processed by a separate
Slurm job. To run using slurm, use

```bash
bash scripts/annotation-kickoff.sh $CRAWL_ID $DATA_DIR
```

where the environment variables `$CRAWL_ID` corresponds to the id of the crawl (e.g., "CC-MAIN-2022-49") and `$DATA_DIR`
is the directory of the Word source files. After creating the partitions, the script submits the jobs to
the slurm cluster by calling the script `scripts/annotation-launch.sbatch`.

### Running locally

Alternatively, you can also run the annotation script locally. To do so, you can directly call the `run_annotate.py`
script:

```bash
python annotate_run.py \
  --data_dir $DATA_DIR \
  --crawl_id $CRAWL_ID \
  --max_docs -1 \
  --output_dir $OUTPUT_DIR
```

## Computing perplexity scores

Perplexity scores can be computed using the `pp_compute_perplexity.py` script. This script will download the 5-gram
Kneser-Ney models and SentencePiece tokenizers used in the [CCNet pipeline](https://github.com/facebookresearch/cc_net).
You can run the script with the following command:

```bash
python pp_compute_perplexity.py \
  --lang $LANG \
  --data $ANNOTATIONS_ROOT
```

After downloading the language model for the specified language, the script will compute the perplexity scores for each
document in the annotations directory, and write the results to the `meta_ppl` directory, that contains the same data
as the `meta` directory, but with the perplexity scores added to the document level metadata.
