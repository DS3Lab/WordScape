"""
code based on
https://github.com/facebookresearch/cc_net/blob/main/cc_net/text_normalizer.py
"""

from pathlib import Path
from sentencepiece import SentencePieceProcessor
import kenlm

from src.quality import text_normalizer


def perplexity(log_score, length):
    return 10.0 ** (-log_score / length)


class SentencePiece:

    def __init__(self, model: Path, normalize=True):
        self._normalize = normalize

        self._sp = SentencePieceProcessor()
        self._sp.load(str(model))

    def tokenize(self, text: str):
        if self._normalize:
            text = text_normalizer.normalize(text)

        tokenized = self._sp.encode_as_pieces(text)
        return " ".join(tokenized)


class LanguageModel:
    def __init__(self, sp_model: Path, lm_model: Path):
        # init models
        self._sp = SentencePiece(sp_model, normalize=True)
        lm_config = kenlm.Config()
        self._lm = kenlm.Model(str(lm_model), lm_config)

    def compute_perplexity(self, content: str) -> float:
        # tokenize
        content = self._sp.tokenize(content)

        # get lines
        lines = content.split("\n")

        doc_log_score, doc_length = 0, 0

        for line in lines:
            log_score = self._lm.score(line)
            length = len(line.split()) + 1
            doc_log_score += log_score
            doc_length += length

        return perplexity(doc_log_score, doc_length)
