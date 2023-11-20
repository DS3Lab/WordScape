from typing import Union

from docx.text.paragraph import Paragraph, Run

import settings
from src.annotation.colorization.mappings import \
    HEURISTIC_FONT_UNKNOWN, HEURISTIC_LEVEL_BODY, HEURISTIC_LEVEL_TITLE


# ---------------------- PARAGRAPH HEURISTICS ---------------------- #


def get_applied_bold_par(par: Paragraph, style):
    if style is None:
        return None
    possible_bold = style.font.bold
    if possible_bold is not None:
        return possible_bold
    else:
        possible_base_style = style.base_style
        return get_applied_bold_par(par, possible_base_style)


def get_applied_italic_par(par: Paragraph, style):
    if style is None:
        return None
    possible_italic = style.font.italic
    if possible_italic is not None:
        return possible_italic
    else:
        possible_base_style = style.base_style
        return get_applied_italic_par(par, possible_base_style)


def get_applied_font_size_par(par: Paragraph, style):
    if style is None:
        # if we ever reach the point that we have both no
        # base style and no defined font size, we almost
        # certainly are in a latent style definition stub.
        # or we are inheriting directly.
        return HEURISTIC_FONT_UNKNOWN
    possible_size = style.font.size
    if possible_size is not None:
        return possible_size.pt
    else:
        possible_base_style = style.base_style
        return get_applied_font_size_par(par, possible_base_style)


# ---------------------- END PARAGRAPH HEURISTICS ---------------------- #

# ---------------------- RUN HEURISTICS ---------------------- #


def get_applied_font_size_run(run: Run, char_style):
    # first check if there is some direct definition in the font object of
    # the run
    possible_size = run.font.size
    if possible_size is not None:
        return possible_size.pt

    # if we found nothing here and there is no more char style to fall back
    # on, give up
    if char_style is None:
        return HEURISTIC_FONT_UNKNOWN

    # if not, fall back to character style and check the font there
    if char_style is not None:
        # check if this has a font object that can be used
        if (char_style.font is not None) and (
                char_style.font.size is not None):
            return char_style.font.size.pt
        # if this also failed, try going up one level
        return get_applied_font_size_run(run, char_style.base_style)


def get_applied_bold_run(run: Run, char_style):
    # first check if there is some direct definition in the font object of the
    # run
    possible_bold = run.font.bold
    if possible_bold is not None:
        return possible_bold

    # if we found nothing here and there is no more char style to fall back
    # on, give up
    if char_style is None:
        return None

    # if not, fall back to character style and check the font there
    if char_style is not None:
        # check if this has a font object that can be used
        if (char_style.font is not None) and (
                char_style.font.bold is not None):
            return char_style.font.bold
        # if this also failed, try going up one level
        return get_applied_bold_run(run, char_style.base_style)


def get_applied_italic_run(run: Run, char_style):
    # first check if there is some direct definition in the font object of the
    # run
    possible_italic = run.font.italic
    if possible_italic is not None:
        return possible_italic

    # if we found nothing here and there is no more char style to fall back
    # on, give up
    if char_style is None:
        return None

    # if not, fall back to character style and check the font there
    if char_style is not None:
        # check if this has a font object that can be used
        if (char_style.font is not None) and (
                char_style.font.italic is not None):
            return char_style.font.italic
        # if this also failed, try going up one level
        return get_applied_italic_run(run, char_style.base_style)


# ---------------------- END RUN HEURISTICS ---------------------- #

# ---------------------- CONVENIENCE FUNCTIONS ---------------------- #
# Main func. documentation lives here


def get_applied_font_size_bold_italic_par(
        par: Paragraph, style
) -> (float, Union[None, bool]):
    r"""
    Get the font size in Pt that is actually applied to a given style,
    taking inheritance into account. Note the use of base_style.
    If the paragraph itself has a set size, this is returned.
    Otherwise, the inheritance heirarchy is traversed.
    If -1 is returned, this means that nothing could be found
    during the traversal.
    !important: If -1 is returned, we have almost certainly
    !hit a point where a built-in style is being inherited from,
    !so no need to worry.

    For bold, italic return values, always returns True / False / None,
    in keeping with tri-state properties.
    """
    return [
        get_applied_font_size_par(par, style),
        get_applied_bold_par(par, style),
        get_applied_italic_par(par, style),
    ]


def get_applied_font_size_bold_italic_run(run: Run, char_style):
    r"""
    Note: There are in fact subtle differences between run and paragraph
        styles! Runs mainly concern themselves with characters styles (which
        exclusively manipulate fonts), while paragraph styles contain other
        properties besides just font! Main difference: for paragraphs we need
        par.style.font, for runs we should directly examine run.font!

    Note: char_style may become a _ParagraphStyle or BaseStyle while traversing
        style hierarchy
    """

    return [
        get_applied_font_size_run(run, char_style),
        get_applied_bold_run(run, char_style),
        get_applied_italic_run(run, char_style),
    ]


def check_for_list_numbering(par: Paragraph) -> bool:
    r"""
    We can check if the pPr attribute exists, and then check if it contains a
    numPr tag. In this case, par must be a paragraph as only paragaraphs can
    contain a numPr tag; when using word formatting, every individual new list
    item is made a paragraph. Paragraphs in the same list are linked by a
    numId child of numPr.
    """
    xml_to_check = par._p.xml
    # check for the tag --> if contained, this was formatted as a word list.
    if "w:numPr" in xml_to_check:
        return True

    return False


def init_or_add_to_count_map(mapping: dict, key, count: int) -> dict:
    r"""
    utility function to help with various maps we use in
    building and fetching heuristics.
    """

    if key in mapping:
        mapping[key] += count
    else:
        mapping[key] = count

    return mapping


def check_if_run_whitespace(run):
    """
    If a run is pure whitespace, we don't want to color it
    """

    return (
            len(
                run.text.replace(" ", "")
                .replace("\n", "")
                .replace("\t", "")
                .replace("\r", "")
            )
            == 0
    )


def build_fontprop_string(fontprops):
    """
    Represent size, boldness and italicness of the text
    """

    # parse fontprops
    [font_size, is_bold, is_italic] = fontprops

    bi_string = ""
    if is_bold:
        bi_string += "b"
    if is_italic:
        bi_string += "i"

    # normal
    if bi_string == "":
        bi_string = "n"

    return str(font_size) + bi_string


def compare_runs_in_par(applied_par_props, applied_run_props):
    """
    Get the properties of individual runs, then override with paragraph
    properties if they are undefined.
    """
    if applied_run_props[0] == HEURISTIC_FONT_UNKNOWN:
        applied_run_props[0] = applied_par_props[0]
    if applied_run_props[1] is None:
        applied_run_props[1] = applied_par_props[1]
    if applied_run_props[2] is None:
        applied_run_props[2] = applied_par_props[2]

    return applied_run_props


def level_to_color_recommendation(level):
    """
    Map a level to (usually) a haeding, with body, document title and lists
    treated separately
    """

    # !in the case that we are not producing a heading level
    if level == HEURISTIC_LEVEL_BODY:
        return settings.colors.COLOR_TEXT
    if level == HEURISTIC_LEVEL_TITLE:
        return settings.colors.COLOR_DOCUMENT_TITLE

    return getattr(
        settings.colors, "COLOR_SECTION_HEADING_{}".format(str(level))
    )
