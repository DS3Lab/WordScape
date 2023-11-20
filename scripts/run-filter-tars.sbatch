#!/bin/bash
# shellcheck disable=SC2206
#SBATCH --time=23:59:00
#SBATCH --job-name=annotate
#SBATCH --cpus-per-task=64
#SBATCH --mem-per-cpu=2GB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --tasks-per-node=1
#SBATCH --output="logs/postprocess/quality-indicators-%j.out"
#SBATCH --error="logs/postprocess/quality-indicators-%j.err"

set -e

mkdir -p logs/postprocess

# load modules
# [... placeholder ...]

# activate virtual environment
source .venv/bin/activate

python utilties/run_filter_tars.py --data_root "$1"
