from docx.text.paragraph import Paragraph
from docx.text.run import Run
from typing import Union, List, Tuple
import copy
import re

from src.annotation.config import AnnotationConfig
import settings
import settings.content_awareness as settings_ca


def form_check(
        element: Paragraph, form_field_min_length: int, *args, **kwargs
) -> bool:
    """
    Check if an element represents a form field.

    @param element: Paragraph to check (requires run splitting!)
    @param form_field_min_length: minimum length to be heuristically considered a field (see settings module)

    returns: bool decision
    """

    # check for field indicators, such as _____ or .....
    # requires run splitting of these field areas

    # ! another indicator: if there is a whitespace run, which is underlined!
    if isinstance(element, Paragraph):
        for run in element.runs:
            if (
                    run.underline is not None
                    and run.underline is not False
                    and len(run.text) >= form_field_min_length
            ):
                if run.text.isspace():
                    return True

    # go through entire text --> if there is some valid field indicator,
    # we need to go into form handling
    current_field_text = ""
    for char in element.text:
        if char in settings_ca.FORM_FIELD_SYMBOLS:
            current_field_text += char
            if len(current_field_text) >= form_field_min_length:
                return True
        # broken sequence
        else:
            current_field_text = ""

    return False


def quote_check(element: Paragraph, *args, **kwargs) -> bool:
    """
    Check if an element represents a quote.

    @param element: Paragraph to check

    returns: bool decision
    """

    # check if element starts and ends with quotation mark
    if len(element.text) > 0:
        return (element.text[0] == element.text[-1]) and (
                element.text[0] in settings_ca.QUOTE_SYMBOLS
        )
    return False


def list_check_run(run: Run) -> bool:
    """
    Check if a run forms a single list item.

    @param run: run to check

    returns: bool decision
    """
    number_regexes = []
    for follower_char in settings_ca.NUMBERING_FOLLOWERS:
        number_regexes.append(re.compile('^[0-9]+' + follower_char))
        # also check a single letter, followed by a follower
        number_regexes.append(re.compile('^\w' + follower_char))

    if (len(run.text) > 0) and not (run.text.isspace()):
        first_word = run.text.split()[0]
        # list character first, or number followed by
        if run.text[0] in settings_ca.NUMBERING_SYMBOLS:
            return True

        for reg_exp in number_regexes:
            if reg_exp.search(first_word):
                return True


def list_check(element: Paragraph, *args, **kwargs) -> bool:
    """
    Check if a paragraph consists entirely of list runs.

    @param element: paragraph to check

    returns: bool decision
    """

    # check if element is numbered (as builtin),
    # or other numbering indicators exist

    # check for runs starting / ending with a number
    # or any designated list characters

    # !all runs should start with a list indicator
    for run in element.runs:
        if not list_check_run(run):
            return False

    return True


# handlers: need to return the paragraph (which may have more runs due to
# splitting!) or a list of runs (one run may be split into multiple runs!)
# and the coloring decision list for each now created run

def form_handler(
        element: Paragraph,
        prev_main_rec: List[List[List[int]]],
        form_field_min_length: int
) -> Tuple[
    Union[Paragraph, None],
    List[Run],
    List[List[List[List[int]]]],
    List[List[List[int]]],
]:
    """
    Handle an element which has been determined to contain form fields, and possibly tags.

    @param element: Paragraph to handle (run spltting will be utilized on this paragraph!)
    @param: prev_main_rec: Previously recommended colorization for entire entity; this will wrap the form colorizations
    @param form_field_min_length: minimum length to be heuristically considered a field (see settings module)

    return: wrapper element, new run splits, color recommendations per run split, wrapper colorization recommendation
    """

    new_runs = []
    color_recommendations = []

    # first, just identify all form fields (possibly in their own runs)
    # possibilities for runs:
    # (non-field) (field) (non-field) --> split field(s) into its own run(s)
    # (entirely field) --> keep color run as field on its own

    # note: we need to track the "current field length" at the end of each run;
    # it may be that the field is not long enough at the end of one run,
    # but becomes long enough after viewing the next run in the sequence.

    # split all 
    for run in element.runs:
        # special case for underlined whitespace runs
        if (
                (run.underline is not None)
                and (run.underline is not False)
                and (run.text.isspace())
                and (len(run.text) >= form_field_min_length)
        ):
            new_runs.append(run)
            color_recommendations.append(settings.colors.COLOR_FORM_FIELD)

            # don't need other checks in this case
            continue

        # ! special case: run beginning contains field characters, but is not
        # long enough --> check if it becomes long enough when considering
        # previous run
        run_chara_index = 0
        current_field_text = ""
        current_non_field_text = ""

        # track beginning form_field characters differently, due to "seams"
        form_field_beginning_text = ""
        for char in run.text:
            if char in settings_ca.FORM_FIELD_SYMBOLS:
                form_field_beginning_text += char
                run_chara_index += 1
            else:
                break

        # case: previously added new form field run --> we need to make any
        # field characters at the beginning of this run part of a form field
        if (len(color_recommendations) > 0) and (
                color_recommendations[-1] == settings.colors.COLOR_FORM_FIELD):
            # create a new field run
            if len(form_field_beginning_text) > 0:
                field_run = copy.deepcopy(run)
                field_run.text = form_field_beginning_text
                new_runs.append(field_run)
                color_recommendations.append(settings.colors.COLOR_FORM_FIELD)

        # case: previously added regular run --> check if this ends with a
        # field run that is long enough when combined with our beginning
        elif (len(color_recommendations) > 0) and (
                color_recommendations[-1] != settings.colors.COLOR_FORM_FIELD):
            prev_run = new_runs[-1]
            # check how many form characters are at the end of the prev. run
            prev_run_field_chars = ""
            for prev_run_char_from_end in range(
                    len(prev_run.text) - 1, -1, -1
            ):
                char = prev_run.text[prev_run_char_from_end]

                if char in settings.content_awareness.FORM_FIELD_SYMBOLS:
                    prev_run_field_chars = char + prev_run_field_chars
                else:
                    break

            # check if previous (unmarked) plus current are long enough
            # --> mark them both as field
            if (
                    len(prev_run_field_chars) + len(form_field_beginning_text)
                    >= form_field_min_length
            ):
                # split the previous run
                # ! may be that the prev. run was entirely composed of field
                # chars, but was too short to qualify as a field --> use a
                # flag to check wether we replace it here (and append next),
                # or replace with a field recommendation only
                prev_already_replaced = False

                if len(prev_run.text) > len(prev_run_field_chars):
                    prev_already_replaced = True
                    # first the non-field beginning part
                    prev_run_nofield = copy.deepcopy(prev_run)
                    # get the last characters that are field chars
                    n_last = len(prev_run.text) - len(prev_run_field_chars)
                    prev_run_nofield.text = prev_run.text[:n_last]
                    new_runs[-1] = prev_run_nofield
                    color_recommendations[-1] = prev_main_rec

                # now get the field characters
                prev_run_field = copy.deepcopy(prev_run)
                prev_run_field.text = prev_run_field_chars
                if prev_already_replaced:
                    new_runs.append(prev_run_field)
                    color_recommendations.append(
                        settings.colors.COLOR_FORM_FIELD)
                else:
                    new_runs[-1] = prev_run_field
                    color_recommendations[
                        -1] = settings.colors.COLOR_FORM_FIELD

                # now make the field from beginning of this run
                if len(form_field_beginning_text) > 0:
                    field_run = copy.deepcopy(run)
                    field_run.text = form_field_beginning_text
                    new_runs.append(field_run)
                    color_recommendations.append(
                        settings.colors.COLOR_FORM_FIELD)

            # if we were unable to create a full form, we may still have
            # grabbed some form characters --> need to go into current form
            # buffer
            else:
                current_field_text = form_field_beginning_text

        # if neither of these held, we have to treat any field text we found
        # in the beginning as part of currently processed text
        else:
            current_field_text = form_field_beginning_text

        # proceed as normal, after having considered special beginning case
        for pos in range(run_chara_index, len(run.text)):
            char = run.text[pos]

            # track chars individually, creating runs as we go
            if char in settings.content_awareness.FORM_FIELD_SYMBOLS:
                current_field_text += char
            # we've run out of chars for a field
            else:
                # we have no chars to make a field out of --> keep counting
                # regular chars
                if len(current_field_text) < form_field_min_length:
                    current_non_field_text += current_field_text
                    current_field_text = ""
                    current_non_field_text += char

                # if it's long enough for its own field --> make runs
                if len(current_field_text) >= form_field_min_length:
                    non_field_run = copy.deepcopy(run)
                    non_field_run.text = current_non_field_text
                    # start tracking starting from newly encountered non-field
                    # character
                    current_non_field_text = char
                    new_runs.append(non_field_run)
                    color_recommendations.append(prev_main_rec)

                    # create field run
                    field_run = copy.deepcopy(run)
                    field_run.text = current_field_text

                    # all field chars have been put in run --> none remain to
                    # track
                    current_field_text = ""
                    new_runs.append(field_run)
                    color_recommendations.append(
                        settings.colors.COLOR_FORM_FIELD)

        # perform checks for form creation again at end of going through run
        # characters
        if len(current_field_text) < form_field_min_length:
            current_non_field_text += current_field_text
            current_field_text = ""

        if len(current_non_field_text) > 0:
            non_field_run = copy.deepcopy(run)
            non_field_run.text = current_non_field_text
            current_non_field_text = ""
            new_runs.append(non_field_run)
            color_recommendations.append(prev_main_rec)

        # create field run
        # note we would already have added it to non_field_text if it was
        # below min. length
        if len(current_field_text) > 0:
            field_run = copy.deepcopy(run)
            field_run.text = current_field_text
            current_field_text = ""
            new_runs.append(field_run)
            color_recommendations.append(settings.colors.COLOR_FORM_FIELD)

    # rebuild the paragraph with new split runs (this preserves styling)
    old_text = element.text
    old_text_len = len(element.text)

    element_para = element._p
    for run in element.runs:
        element_para.remove(run._r)

    # add rebuilt runs
    for new_run in new_runs:
        element_para.append(new_run._r)

    # ! sanity check
    new_text = element.text
    new_text_len = len(element.text)
    if new_text != old_text:
        raise ValueError(
            f"Reconstructed content-aware form paragraph has mismatched text. "
            f"Old text: \n {old_text} \n Length: {old_text_len} \n "
            f"New text: \n {new_text} \n Length: {new_text_len}"
        )

    return element, new_runs, color_recommendations, prev_main_rec


def quote_handler(
        element: Paragraph,
        prev_main_rec: List[List[List[int]]],
        *args, **kwargs
) -> Tuple[
    Union[Paragraph, None],
    List[Run],
    List[List[List[List[int]]]],
    List[List[List[int]]],
]:

    """
    Handle an element which has been determined to constitute a quote.

    @param element: Paragraph to handle
    @param: prev_main_rec: Previously recommended colorization for entire entity

    return: wrapper element, established run splits, color recommendations per run split, wrapper colorization recommendation
    """

    # no splitting necessary, can just return as-is with color
    return element, element.runs, [settings.colors.COLOR_QUOTE] * len(
        element.runs), settings.colors.COLOR_QUOTE


def list_handler(
        element: Paragraph,
        prev_main_rec: List[List[List[int]]],
        *args, **kwargs
) -> Tuple[
    Union[Paragraph, None],
    List[Run],
    List[List[List[List[int]]]],
    List[List[List[int]]],
]:

    """
    Handle an element which has been determined to constitute a list.

    @param element: Paragraph to handle
    @param: prev_main_rec: Previously recommended colorization for entire entity; this MAY wrap the list colorizations

    return: wrapper element, established run splits, color recommendations per run split, wrapper colorization recommendation
    """
    # return those runs as list that match list criteria
    run_colorings = []
    list_charas = 0
    for run in element.runs:
        if list_check_run(run):
            run_colorings.append(settings.colors.COLOR_LIST)
            list_charas += len(run.text)
        else:
            run_colorings.append(prev_main_rec)

    # if the total text length is now majority list --> make list new main
    # color
    new_main_col = prev_main_rec
    if list_charas >= len(element.text):
        new_main_col = settings.colors.COLOR_LIST

    # only need to change color recommendations
    return element, element.runs, run_colorings, new_main_col


# ordered list, which determines by what priority a passed check should apply
# and what handler the object should be passed to
CHECK_ORDERING = {
    form_check: form_handler,
    quote_check: quote_handler,
    list_check: list_handler,
}
CHECK_LIST = [form_check, quote_check, list_check]


def check_content_heuristics_par(
        par: Paragraph,
        prev_main_rec: List[List[List[int]]],
        config: AnnotationConfig
) -> Tuple[
    Union[Paragraph, None],
    Union[List[Run], None],
    Union[List[List[List[List[int]]]], None],
    Union[List[List[List[int]]], None],
]:

    """
    Perform content aware heuristics on an entire paragraph; If any checks match, pass the paragraph to the associated handler.
    
    @param par: Paragraph to handle
    @param: prev_main_rec: Previously recommended colorization for entire entity
    @param config: AnnotationConfig to base decisions on

    return: wrapper element, established run splits, color recommendations per run split, wrapper colorization recommendation
    
    """
    check_kwargs = {
        "form_field_min_length": config.form_field_min_length
    }
    handler_kwargs = {
        "form_field_min_length": config.form_field_min_length
    }
    for check_function in CHECK_LIST:
        if check_function(par, **check_kwargs):
            fn = CHECK_ORDERING[check_function]
            return fn(par, prev_main_rec, **handler_kwargs)

    return None, None, None, None
