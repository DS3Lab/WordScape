from typing import Dict, List
import fasttext

from src.annotation.annotation_objects import Word
import src.annotation.language_detection.utils as lang_utils


def predict_lang_per_page(
        pages_words: Dict[str, List[Word]],
        k: int,
        lm: fasttext.FastText._FastText = None
) -> Dict[str, Dict[str, float]]:
    r""" Detects top-k languages occuring in text using the fasttext model
    trained on trained on data from Wikipedia, Tatoeba and SETimes.

    Reference: https://fasttext.cc/docs/en/language-identification.html

    @param pages_words: dictionary mapping page ids to list of words
    @param k: number of predictions to return, defaults to 5
    @param lm: language model, defaults to None, in which case it is loaded in
        the function

    @return: dictionary mapping page ids to list of predicted languages and
        list of corresponding confidence scores
    """
    if lm is None:
        lm = lang_utils.load_lang_model(version="ftz")

    pages_langs = {}
    for page_id, page_words in pages_words.items():
        page_text = " ".join([word.text for word in page_words])
        pages_langs[page_id] = predict_lang(page_text, k=k, lm=lm)

    return pages_langs


def _clean_text(text: str) -> str:
    return " ".join(text.strip().lower().split())


def predict_lang(text: str, k: int, lm=None) -> Dict[str, float]:
    # clean text
    text = _clean_text(text)

    if len(text) == 0:
        return {"__label__unknown": 1.0}

    if lm is None:
        lm = lang_utils.load_lang_model(version="ftz")

    # predict language
    tags, confs = lm.predict(text, k=k)

    # convert predictions to dictionary
    langs: Dict[str, float] = {
        lang: float(conf) for lang, conf in zip(tags, confs)
    }

    return langs
