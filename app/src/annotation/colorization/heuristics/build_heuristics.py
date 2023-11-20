from docx.document import Document as _Document
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from typing import Tuple, List

from src.annotation.colorization.mappings import HEURISTIC_LEVEL_BODY
from src.annotation.colorization.mappings import HEURISTIC_LEVEL_TITLE
from src.annotation.colorization.heuristics.utils import (
    get_applied_font_size_bold_italic_par,
    get_applied_font_size_bold_italic_run,
    init_or_add_to_count_map,
    check_for_list_numbering,
    check_if_run_whitespace,
    build_fontprop_string,
    compare_runs_in_par,
    level_to_color_recommendation
)
from src.annotation.colorization.heuristics.content_awareness import \
    check_content_heuristics_par
from src.annotation.config import AnnotationConfig

import settings.annotation as annotation_settings
import settings.colors as color_settings


class ParagraphHeuristic:
    def __init__(self, document: _Document, config: AnnotationConfig):
        r"""
        A mapping from paragraphs to heuristic groupings.
        This is useful in case we encounter a style which is not built-in.
        Currently, the idea mainly relies on font sizes.
        The most common size becomes the body, largest the title, those between
        headers.

        @param document: Document to build heuristics for
        @param config: AnnotationConfig to use during annotation
        """

        # will finally map font sizes to (recommendations) for entity type
        # this either contains heading levels, or special levels indicating
        # (currently) body / doc. title / list text.
        self.heuristic_map = {}

        # ! tracking if the document has builtin heading info we can use
        self.builtin_heading_tracker = []

        # map specific Pt font sizes to how often they appear (charcount)
        # intuitively we should care about the most common size and the largest
        self.font_size_count = {}

        # special levels for body / title, so that we dont mix them up
        # with the push up / push down ideas
        # !negative levels are "reserved" for non-heading cases

        # count how many times a font-size appears
        # (we should only count 1 appearance per time
        # it shows up in a paragraph)
        self.font_size_appearances = {}

        self._config = config

        self.__build_map(document)

    def __evaluate_paragraph(self, par: Paragraph):
        r"""
        Examine _ParagraphStyle and run _CharacterStyles separately.
        If a run has an undef somewhere --> replace it with corresponding
        entry from paragraph style.

        @parameter par: Paragraph object to evaluate

        @return: a mapping font properties --> character count for those
        properties
        """
        applied_par_props = get_applied_font_size_bold_italic_par(
            par=par, style=par.style
        )

        # check if we have a builtin heading here --> track these separately
        builtin_heading_flag = False
        possible_builtin = None
        heading_level = None

        if par.style is not None:
            possible_builtin = color_settings.ENTITY_NAME_TO_COLOR.get(
                par.style.name.lower()
            )

        if (
                possible_builtin is not None and
                possible_builtin in color_settings.COLORS_SECTION_HEADINGS
        ):
            heading_level = int(par.style.name.lower().split()[1])
            builtin_heading_flag = True

        # now go through individual runs
        already_counted_fonts = []
        all_runs_bold = True
        all_runs_italic = True
        # deal with whitespace paragraphs
        all_runs_whitespace = True
        run_font_sizes = []
        for run in par.runs:
            applied_run_props = get_applied_font_size_bold_italic_run(
                run=run, char_style=run.style
            )

            # check if any are missing --> if so, replace with par value
            applied_run_props = compare_runs_in_par(
                applied_par_props=applied_par_props,
                applied_run_props=applied_run_props
            )

            # in the case that we have a builtin, need to check whether all
            # runs in the par are bold also disregard pure whitespace runs
            if not check_if_run_whitespace(run):
                all_runs_bold = all_runs_bold and applied_run_props[1]
                all_runs_italic = all_runs_italic and applied_run_props[2]
                # also need to check wether the builtin is being overridden by
                # all runs having different font sizes
                run_font_sizes.append(applied_run_props[0])
                all_runs_whitespace = False

            # build font property string
            fontprop_string = build_fontprop_string(applied_run_props)

            # add to mapping with character count
            init_or_add_to_count_map(
                self.font_size_count, fontprop_string, len(run.text)
            )
            if fontprop_string not in already_counted_fonts:
                init_or_add_to_count_map(
                    mapping=self.font_size_appearances,
                    key=fontprop_string, count=1
                )
                already_counted_fonts.append(fontprop_string)

        if builtin_heading_flag and (not all_runs_whitespace) and (
                len(par.runs) > 0):
            applied_par_props[1] = applied_par_props[1] or all_runs_bold
            applied_par_props[2] = applied_par_props[2] or all_runs_italic
            possible_size_override = list(set(run_font_sizes))
            if len(possible_size_override) == 1:
                applied_par_props[0] = possible_size_override[0]

            self.builtin_heading_tracker.append(
                (build_fontprop_string(applied_par_props), heading_level))

    def __build_map(self, document: _Document):
        r"""
        Build the heuristic mapping. Should only be run
        during self.init.

        @param document: Document to build initial mapping for
        """

        for child in document.element.body.iterchildren():

            if not isinstance(child, CT_P):
                # only cover paragraph instances
                continue

            # instance is a paragraph
            par = Paragraph(child, document)
            # add this paragraphs counts to global tracker
            self.__evaluate_paragraph(par)

        # ! if we have detected any builtin headeings --> we only assume that
        # ! exact matches to the builtin fonts are on the same level
        if len(self.builtin_heading_tracker) > 0:
            for pair in self.builtin_heading_tracker:
                possible_prior_level = self.heuristic_map.get(pair[0])
                if possible_prior_level is not None:
                    # ! always assign lowest observed heading level
                    if pair[1] > possible_prior_level:
                        self.heuristic_map[pair[0]] = pair[1]
                else:
                    self.heuristic_map[pair[0]] = pair[1]
            return

        # now that we have counted commonness of font types, we can
        # apply any heuristic we want.
        # ! for now: common --> body, largest --> title, 2nd largest -->
        # secheader, between --> other section headings

        # build sorted list of font_prop strings
        # first strip b / i / bi text
        pure_font_sizes = self.font_size_count.keys()
        pure_font_sizes = list(
            map(
                lambda fpropstr: fpropstr.replace("b", "")
                .replace("i", "")
                .replace("n", ""),
                pure_font_sizes,
            )
        )
        pure_font_sizes = list(
            map(lambda fpropstr: float(fpropstr), pure_font_sizes))
        # and make unique
        pure_font_sizes = list(set(pure_font_sizes))

        lg_to_sm_fonts = sorted(pure_font_sizes)
        # fonts from large (at index 0) to small
        lg_to_sm_fonts.reverse()
        # add in b, bi, n, i in order of level we should be at
        ordering_with_bi = []
        for pure_font_size in lg_to_sm_fonts:
            font_str = str(pure_font_size)
            # ! ordering: b, bi, n, i
            for bi_str in ["b", "bi", "i", "n"]:
                if (font_str + bi_str) in self.font_size_count:
                    ordering_with_bi.append((font_str + bi_str))

        lg_to_sm_fonts = ordering_with_bi

        # get most common font size
        if self.font_size_count:
            common_fnt = max(self.font_size_count,
                             key=self.font_size_count.get)
        else:
            self.heuristic_map = {}
            return

        # assign most common font to body
        self.heuristic_map[common_fnt] = HEURISTIC_LEVEL_BODY

        # if there is only one font size --> its body
        if len(lg_to_sm_fonts) == 1:
            self.heuristic_map[lg_to_sm_fonts[0]] = HEURISTIC_LEVEL_BODY
            # nothing more to do in this case
            return

        # assign largest to title, if it only appears once
        if self.font_size_appearances[lg_to_sm_fonts[0]] == 1:
            self.heuristic_map[lg_to_sm_fonts[0]] = HEURISTIC_LEVEL_TITLE
            lg_to_sm_fonts.pop(0)

        # it is possible the most common font was not recognized (i.e -1)
        # in this case, we should consider the most-common font which we
        # can actually recognize as part of the body as well
        common_fnt = max(self.font_size_count, key=self.font_size_count.get)
        self.heuristic_map[common_fnt] = HEURISTIC_LEVEL_BODY

        # we have headers to assign
        if (len(lg_to_sm_fonts) > 1) and (lg_to_sm_fonts[0] != common_fnt):
            # assign second to section header
            self.heuristic_map[lg_to_sm_fonts[0]] = 1
            # assign others to generic header
            lg_to_sm_fonts.pop(0)
            heading_level_count = 2
            while len(lg_to_sm_fonts) > 0:
                # stop if we reach the body
                curr_fnt = lg_to_sm_fonts.pop(0)
                if curr_fnt == common_fnt:
                    break
                self.heuristic_map[curr_fnt] = heading_level_count
                # mapping to native word styles does not let us go over 9
                # heading levels
                heading_level_count = min(heading_level_count + 1, 9)

            while len(lg_to_sm_fonts) > 0:
                curr_fnt = lg_to_sm_fonts.pop(0)
                self.heuristic_map[curr_fnt] = HEURISTIC_LEVEL_BODY

    def get_heuristic_with_runs(
            self, par: Paragraph
    ) -> Tuple[Tuple[int, int, int], List[Tuple[int, int, int]], str]:
        r"""
        Get heuristics, while also taking runs into account

        @param par: paragraph to get heuristics for (and its runs)

        @return: (main color, list of colors, decision source)
        """

        # default decision source
        decision_source = \
            annotation_settings.ANNOTATION_BODY_HEADING_HEURISTIC_BASE

        # if we are in the "mode" of using builtin heading information
        if len(self.builtin_heading_tracker) > 0:
            decision_source = annotation_settings. \
                ANNOTATION_BODY_HEADING_HEURISTIC_USINGBUILTIN

        # first deal with lists, by detecting their XML characteristics
        # we should only perform this check for actual paragraphs
        if check_for_list_numbering(par):
            # if the main color is a list, we should assume all its runs are
            # also part of this list
            return (
                color_settings.COLOR_LIST,
                [color_settings.COLOR_LIST] * len(par.runs),
                # decision source gets updated
                annotation_settings.ANNOTATION_XML_PATTERN
            )

        # check the actual main recommendation, purely based on character count
        # we can do this because we override undef run properties with the
        # paragraph property!
        characters_per_recommendation = {}
        run_heuristics = []

        # again, replace font props with paragraph props if they are undef
        applied_par_props = get_applied_font_size_bold_italic_par(
            par, par.style
        )
        whitespace_run_indices = []

        prev_run_was_heading = True
        curr_heading_length = 0
        for run in par.runs:
            # ! deal with pure whitespace runs
            if check_if_run_whitespace(run):
                run_heuristics.append(color_settings.COLOR_WHITESPACE)
                whitespace_run_indices.append(len(run_heuristics) - 1)
                # this will only be max count if there are no other characters
                init_or_add_to_count_map(
                    mapping=characters_per_recommendation,
                    key=str(color_settings.COLOR_WHITESPACE),
                    count=-1,
                )
                continue

            applied_run_props = get_applied_font_size_bold_italic_run(
                run, run.style
            )
            applied_run_props = compare_runs_in_par(
                applied_par_props, applied_run_props
            )
            applied_run_propstring = build_fontprop_string(applied_run_props)

            # get the level and its associated recommendation
            if applied_run_propstring in self.heuristic_map:
                run_level = self.heuristic_map[applied_run_propstring]
                run_heuristic = level_to_color_recommendation(run_level)

                # ! heading strictness:
                # ! extra heading checks here
                # cannot be in the middle of a body par
                # so must either start the par, or follow an already
                # heading-run. Must also respect maximum length
                if not prev_run_was_heading:
                    run_heuristic = color_settings.COLOR_TEXT

                run_heuristics.append(run_heuristic)

                if (
                        run_heuristic in color_settings.COLORS_SECTION_HEADINGS
                        or
                        run_heuristic == color_settings.COLOR_DOCUMENT_TITLE
                ):
                    # don't let the current heading length get over the max
                    curr_heading_length += len(run.text)
                    if curr_heading_length > self._config.max_heading_len:
                        # set the entire paragraph to body and dont allow any
                        # more headings
                        run_heuristics = \
                            [color_settings.COLOR_TEXT] * len(run_heuristics)
                        # hacky
                        characters_per_recommendation = {
                            str(color_settings.COLOR_TEXT): 1000
                        }
                        prev_run_was_heading = False
                else:
                    prev_run_was_heading = False

                # counting how many characters each color needs to apply to
                # not lists are not hashable --> convert to string
                init_or_add_to_count_map(
                    mapping=characters_per_recommendation,
                    key=str(run_heuristic),
                    count=len(run.text)
                )
            else:
                # ! strictness: opt for body if any uncertainty
                run_heuristics.append(color_settings.COLOR_TEXT)
                prev_run_was_heading = False
                init_or_add_to_count_map(
                    mapping=characters_per_recommendation,
                    key=str(color_settings.COLOR_TEXT),
                    count=len(run.text)
                )

        # if a different color has more characters, that should be the main
        # color! undo the str conversion we performed (in order to enable
        # hashing)
        if characters_per_recommendation:
            main_color = eval(
                max(characters_per_recommendation,
                    key=characters_per_recommendation.get)
            )
            # replace all whitespaces with whatever main color turned out to be
            for index in whitespace_run_indices:
                run_heuristics[index] = main_color
        else:
            main_color = None

        # ! if a content-aware heuristic is passed, use this instead
        (
            possible_split_para,
            possible_split_run,
            split_run_recs,
            new_main_col,
        ) = check_content_heuristics_par(
            par, prev_main_rec=main_color, config=self._config
        )
        if split_run_recs is not None:
            # ! special rule: Lower priority of list check, as this needs to
            # be stricter
            if not ((new_main_col == color_settings.COLOR_LIST) and (
                    len(self.builtin_heading_tracker) > 0)):
                run_heuristics = split_run_recs
                main_color = new_main_col

                # decision source gets updated, since we used content-aware
                decision_source = \
                    annotation_settings.ANNOTATION_CONTENT_AWARE_HEURISTIC

        return main_color, run_heuristics, decision_source
