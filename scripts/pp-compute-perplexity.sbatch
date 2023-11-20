#!/bin/bash
# shellcheck disable=SC2206
#SBATCH --time=23:59:00
#SBATCH --job-name=annotate
#SBATCH --cpus-per-task=32
#SBATCH --mem-per-cpu=4GB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --tasks-per-node=1
#SBATCH --output="logs/postprocess/quality-indicators-%j.out"
#SBATCH --error="logs/postprocess/quality-indicators-%j.err"

set -e

# load modules
module load eth_proxy jdk gcc/6.3.0 python/3.8.5

# activate virtual environment
source .venv/bin/activate

DATA_ROOT="/cluster/project/zhang/opendoc/data/annotated/cc_main_2022_49/20230531_144800"
LANGS=("ru" "en" "uk" "pl" "es" "fr" "it" "pt" "cs" "hu" "de" "bg" "tr" "nl" "el")
for lang in "${LANGS[@]}"; do
  echo "computing perplexity values for $lang"

  python pp_compute_perplexity.py \
    --data "$DATA_ROOT" \
    --lang "$lang"

  # remove language models
  rm resources/wikipedia-models/${lang}.arpa.bin
  rm resources/wikipedia-models/${lang}.sp.model
done
