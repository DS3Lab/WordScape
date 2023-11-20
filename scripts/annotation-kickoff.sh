#!/bin/bash

set -e

WORKERS=25
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CRAWL_ID="$1"
DATA_ROOT="$2"
OUTPUT_DIR="data/annotated/${CRAWL_ID}/${TIMESTAMP}"
PARTITIONS_DIR="${OUTPUT_DIR}/partitions"
mkdir -p "$PARTITIONS_DIR"

echo "CRAWL_ID: $CRAWL_ID"
echo "DATA_ROOT: $DATA_ROOT"
echo "PARTITIONS_DIR: $PARTITIONS_DIR"
echo "OUTPUT_DIR: $OUTPUT_DIR"

TMP_FILE="${PARTITIONS_DIR}/tmp.txt"

echo $(find "$DATA_ROOT" -type f -name "*.tar.gz") | tr " " "\n" >"$TMP_FILE"

# split into partitions
N_FILES=$(wc -l <"$TMP_FILE")
N_FILES_PER_PARTITION=$((N_FILES / WORKERS + 1))
split -d -l $N_FILES_PER_PARTITION "$TMP_FILE" "${PARTITIONS_DIR}/part_"

# remove tmp file
rm "$TMP_FILE"

# rename partitions to have .txt extension
for f in "${PARTITIONS_DIR}/part_"*; do
  mv "$f" "${f}.txt"
  echo "created partition ${f}.txt"
done

sbatch scripts/annotation-launch.sbatch "$CRAWL_ID" "$OUTPUT_DIR" "$PARTITIONS_DIR"
