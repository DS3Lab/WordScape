#!/bin/bash
# shellcheck disable=SC2206
#SBATCH --time=23:59:00
#SBATCH --job-name=cc_docs
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=2GB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --tasks-per-node=1
#SBATCH --array=1-180
#SBATCH --output="logs/cc_docs/mp_cc-docs-%j.out"
#SBATCH --error="logs/cc_docs/mp_cc-docs-%j.err"

set -e

mkdir -p logs/cc_docs

# load modules
# [... placeholder ...]

# activate virtual environment
source .venv/bin/activate

export SLURM_CPUS_PER_TASK

INPUT_DIR="$1"/"${SLURM_ARRAY_TASK_ID}"
CC_DUMP="$2"

echo "starting url parsing on ${HOSTNAME} with inputs from ${INPUT_DIR} for dump ${CC_DUMP}; using ${SLURM_CPUS_PER_TASK} cpu cores."

python -u cc_parse_snapshot.py \
  --input "$INPUT_DIR" \
  --cc_dump "$CC_DUMP"
