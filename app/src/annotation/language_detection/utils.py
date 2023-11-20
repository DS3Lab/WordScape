import iso639
import fasttext
from pathlib import Path
from settings.filesystem import FASTTEXT_CLASSIFIERS_DIR

# suppress fasttext warning
fasttext.FastText.eprint = lambda x: None


def lang_code_to_name(lang_code: str) -> str:
    r""" Convert language iso639 code to human readable language name. """
    try:
        return iso639.to_name(lang_code)
    except iso639.NonExistentLanguageError:
        return "unknown"


def load_lang_model(version: str = "bin") -> fasttext.FastText._FastText:
    r""" Load language model. """
    if version.lower() == "bin":
        return fasttext.load_model(
            path=str(Path(FASTTEXT_CLASSIFIERS_DIR, "lid.176.bin"))
        )
    elif version.lower() == "ftz":
        return fasttext.load_model(
            path=str(Path(FASTTEXT_CLASSIFIERS_DIR, "lid.176.ftz"))
        )
    else:
        raise ValueError(f"Invalid fasttext model version {version}")
