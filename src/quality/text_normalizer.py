"""
code adapted from
https://github.com/facebookresearch/cc_net/blob/main/cc_net/text_normalizer.py
"""
import re
import unicodedata

DIGIT_RE = re.compile(r"\d")
UNICODE_PUNCT = {
    "，": ",",
    "。": ".",
    "、": ",",
    "„": '"',
    "”": '"',
    "“": '"',
    "«": '"',
    "»": '"',
    "１": '"',
    "」": '"',
    "「": '"',
    "《": '"',
    "》": '"',
    "´": "'",
    "∶": ":",
    "：": ":",
    "？": "?",
    "！": "!",
    "（": "(",
    "）": ")",
    "；": ";",
    "–": "-",
    "—": " - ",
    "．": ". ",
    "～": "~",
    "’": "'",
    "…": "...",
    "━": "-",
    "〈": "<",
    "〉": ">",
    "【": "[",
    "】": "]",
    "％": "%",
    "►": "-",
}
UNICODE_PUNCT_RE = re.compile(f"[{''.join(UNICODE_PUNCT.keys())}]")

NON_PRINTING_CHARS_RE = re.compile(
    f"[{''.join(map(chr, list(range(0, 32)) + list(range(127, 160))))}]"
)


def strip_accents(line: str) -> str:
    """Strips accents from a piece of text."""
    nfd = unicodedata.normalize("NFD", line)
    output = [c for c in nfd if unicodedata.category(c) != "Mn"]
    if len(output) == line:
        return line
    return "".join(output)


def replace_unicode_punct(text: str) -> str:
    return "".join((UNICODE_PUNCT.get(c, c) for c in text))


def remove_non_printing_char(text: str) -> str:
    return NON_PRINTING_CHARS_RE.sub("", text)


def normalize(line: str) -> str:
    line = line.strip()

    if not line:
        return line

    line = line.lower()
    line = strip_accents(line)
    line = DIGIT_RE.sub("0", line)
    line = replace_unicode_punct(line)
    line = remove_non_printing_char(line)

    return line
