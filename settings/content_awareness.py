# settings for content-aware heuristics

# symbols we consider to constitute a possible form field
# note the special triple-period symbol, which word likes to auto-create
FORM_FIELD_SYMBOLS = ['_', '.', '…']

# symbols we consider to indicate a quote; must be at start and end.
QUOTE_SYMBOLS = ["\"", "\'"]

# symbols we consider to constitute a possible numbering
# ! warning: we also include any number followed by a '.', there are infinite
# ! such possibilities.
# here we only list single symbols that we consider to indicate a list entry
# also, the check for builtin numbering indicators is handled separately
NUMBERING_SYMBOLS = [
    '-', '\u2022', '\u27A2', '\u25E6', '\u25AA', '\u25AB', '\u25CF', '\u25CB',
    '\u25A0', '\u25A1', '\u25B6', '\u2043', '\u25C6', '\u25C7', '\u25D0',
    '\u25D1'
]

NUMBERING_FOLLOWERS = ['\.', ':', '\)']
