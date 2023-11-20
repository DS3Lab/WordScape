#!/bin/bash
# shellcheck disable=SC2206
#SBATCH --time=93:59:00
#SBATCH --job-name=annotate
#SBATCH --cpus-per-task=24
#SBATCH --mem-per-cpu=4GB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --tasks-per-node=1
#SBATCH --array=1-25
#SBATCH --output="logs/annotation/mp_annotation-docs-%j.out"
#SBATCH --error="logs/annotation/mp_annotation-docs-%j.err"

set -e

mkdir -p logs/annotation

# load modules
# [... placeholder ...]

# activate virtual environment
source .venv/bin/activate

# read args
CRAWL_ID="$1"
OUTPUT_DIR="$2"
PARTITIONS_DIR="$3"

# export env variables
export SLURM_CPUS_PER_TASK

echo "SLURM_CPUS_PER_TASK: ${SLURM_CPUS_PER_TASK}"
echo "SLURM_MEM_PER_CPU: ${SLURM_MEM_PER_CPU}"

if [ -z "$PARTITIONS_DIR" ]; then
  echo "PARTITIONS_DIR is not set"
  exit 1
fi

if [ -z "$CRAWL_ID" ]; then
  echo "CRAWL_ID is not set"
  exit 1
fi

if [ -z "$OUTPUT_DIR" ]; then
  echo "OUTPUT_DIR is not set"
  exit 1
fi

INPUT_FILE=$(ls ${PARTITIONS_DIR}/part_*.txt | sed -n "${SLURM_ARRAY_TASK_ID}p")
echo "starting annotation on $(hostname) with inputs from ${INPUT_FILE}; using ${SLURM_CPUS_PER_TASK} cpu cores."

python -u annotate_run.py \
  --input_files "$INPUT_FILE" \
  --crawl_id "$CRAWL_ID" \
  --output_dir "$OUTPUT_DIR" \
  --soffice_executable ".apps/libreoffice/opt/libreoffice7.4/program/soffice" \
  --max_docs -1
