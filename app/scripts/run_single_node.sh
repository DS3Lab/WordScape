#!/bin/bash

set -e
trap cleanup_on_error ERR SIGINT SIGTERM

cleanup_on_error() {
  echo "Error: $0:$LINENO: command \`$BASH_COMMAND\` failed with exit code $?"
  exit 1
}

help() {
  echo "Usage: run_single_node.sh [ -d | --dump_id ] [-m | --max_docs]"
  exit 2
}

while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
  -d | --dump_id)
    DUMP_ID="$2"
    shift 2
    ;;
  -m | --max_docs)
    MAX_DOCS="$2"
    shift 2
    ;;
  -h | --help)
    help
    ;;
  --)
    shift
    break
    ;;
  *)
    echo "Invalid option: -$1"
    help
    ;;
  esac
done

# generate random run id
RUN_ID=$(openssl rand -hex 12)

CLEAN_URLS_DIR="/mnt/data/${RUN_ID}/clean_urls"
SOURCES_DIR="/mnt/data/${RUN_ID}/download/${DUMP_ID}"
OUTPUT_DIR="/mnt/data/${RUN_ID}/annotated/${DUMP_ID}"

# create directories
mkdir -p "$CLEAN_URLS_DIR"
mkdir -p "$SOURCES_DIR"
mkdir -p "$OUTPUT_DIR"

printf "Created directories:\n"
printf "  * CLEAN_URLS_DIR: %s\n" "$CLEAN_URLS_DIR"
printf "  * SOURCES_DIR: %s\n" "$SOURCES_DIR"
printf "  * OUTPUT_DIR: %s\n" "$OUTPUT_DIR"

if [ -z "${MAX_DOCS}" ]; then
  MAX_DOCS=-1
fi

# get file fid
case $DUMP_ID in
"CC-MAIN-2013-48")
  FID="1359HSlQighPkMV3iEf_z6pO5rdknZhJ_"
  ;;
"CC-MAIN-2016-50")
  FID="14_YuQeu6S0u2lKYKOcpEy5AUjmvSeQdE"
  ;;
"CC-MAIN-2020-40")
  FID="1hKFv4gkUqV_cJcR-02J7rbVm2vJ8HRHH"
  ;;
"CC-MAIN-2021-43")
  FID="1wuXzQ6RKmV56RldqRImbbbHnnza7GSpF"
  ;;
"CC-MAIN-2023-06")
  FID="1mKWK79_M_ENGJy781tPUCtsNJtuoxu5d"
  ;;
"CC-MAIN-2023-14")
  FID="15Od3TdMrkondhfyCNCBSxijXbuyq5rz3"
  ;;
*)
  echo "Invalid dump id: $DUMP_ID"
  exit 1
  ;;
esac

# download urls
printf "\n================================\nFetching URL List...\n"
gdown "https://drive.google.com/uc?id=$FID" -O "$CLEAN_URLS_DIR/$DUMP_ID.parquet"

mkdir -p /usr/app/data/tmp

# 1) Prepare urls for download
printf "\n================================\nURL prep...\n"
python3 download_prepare_urls.py \
  --cc_dump "$DUMP_ID" \
  --clean_urls_dir "$CLEAN_URLS_DIR" \
  --num_nodes 1

# 2) Download documents
printf "\n================================\nDownloading documents...\n"
python3 download_run.py \
  --input "${CLEAN_URLS_DIR}/${DUMP_ID}/1.parquet" \
  --subset_size $MAX_DOCS \
  --write_dir "$SOURCES_DIR"

# 3) Annotate documents
printf "\n================================\nAnnotating documents...\n"
python3 annotate_run.py \
  --data_dir "$SOURCES_DIR" \
  --crawl_id "$DUMP_ID" \
  --max_docs $MAX_DOCS \
  --output_dir "$OUTPUT_DIR" \
  --soffice_executable "soffice"

printf "\n---------------------------------\n"
printf "WordScape pipeline complete.\n"
printf "Dataset is in %s\n" "$OUTPUT_DIR"
