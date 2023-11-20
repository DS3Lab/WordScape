#!/bin/bash
# shellcheck disable=SC2206
#SBATCH --time=23:59:00
#SBATCH --job-name=download
#SBATCH --cpus-per-task=64
#SBATCH --mem-per-cpu=2GB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --tasks-per-node=1
#SBATCH --array=1-25
#SBATCH --output="logs/download/mp_download-docs-%j.out"
#SBATCH --error="logs/download/mp_download-docs-%j.err"

set -e

mkdir -p logs/download

# load modules
# [... placeholder ...]

# activate virtual environment
source .venv/bin/activate

INPUT_FILE="$1/${SLURM_ARRAY_TASK_ID}.parquet"
OUTPUT="$3"

echo "starting download on ${HOSTNAME} with inputs from ${INPUT_FILE}, outputting to ${OUTPUT}; using ${SLURM_CPUS_PER_TASK} cpu cores"
python -u download_run.py -i "$INPUT_FILE" -ss $2 -wd "$OUTPUT"
