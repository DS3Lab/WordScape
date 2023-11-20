import dataclasses
from docx.oxml import CT_R
from docx.shared import RGBColor
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from typing import List, Union, Dict

from src.annotation.colorization.heuristics.build_heuristics import (
    ParagraphHeuristic
)
from src.annotation.utils.color_utils import rgb_to_hex, hsv_to_rgb
from src.annotation.utils.color_utils import shade_element
from src.annotation.colorization.mappings import CONSIDER_RUN_COLORING_FOR

import settings.colors as color_settings
import settings.entities as entity_settings
import settings.annotation as annotation_settings


@dataclasses.dataclass
class ColorizationDecision:
    r"""
    A colorization decision, which is made by the colorization handler
    """

    # the element which is colorized
    text: str
    # the colorization decision
    decision_source: str
    # the id of the entity category
    entity_decision: int

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class ColorizationHandler:
    r"""
    Handles colorization of elements, including looping colorization
    """

    def __init__(self):
        # track current color to be applied, depending on element decision
        # we will later loop through saturation values --> allows us to
        # distinguish neighboring elements of the same type

        # base color decision is translated to actual applicable color
        self.color_decision_to_application = {}
        # track used colors
        self._used_colors = {}
        for base_color in color_settings.ALL_COLORS:
            self.color_decision_to_application[str(base_color)] = base_color
            self._used_colors[str(base_color)] = {base_color}

        # ! A JSON which tracks how a colorization decision was made
        # see settings.annotation
        self._colorization_decisions: List[ColorizationDecision] = []

    def update_application_color(self, base_color, new_color):
        # for table cells and table header cells, we have a different color
        # cycling scheme which additionally takes into account the saturation;
        # in this case the below update rule is not applicable and we provide
        # the new color directly and update the used colors accordingly
        assert new_color is not None

        # this takes care of tables inside table cells, where the base color
        # starts at the used table cell color; so we need to update the base
        # color to the table color in this case since we want to keep track of
        # it in the table (header) color space
        if base_color[0] == color_settings.COLOR_TABLE[0]:
            base_color = color_settings.COLOR_TABLE
        elif base_color[0] == color_settings.COLOR_TABLE_HEADER[0]:
            base_color = color_settings.COLOR_TABLE_HEADER

        self._used_colors[str(base_color)].add(new_color)

    def update_colorization_decisions(
            self,
            text: Union[str, None],
            decision_source: str,
            entity_decision: int
    ):
        r""" Update the colorization decisions

        @param text: the text to be colored
        @param decision_source: the source of the entity decision
        @param entity_decision: the id of the entity category
        """
        self._colorization_decisions.append(ColorizationDecision(
            text=text,
            decision_source=decision_source,
            entity_decision=entity_decision
        ))

    def __update_application_color(self, base_color):
        r""" Update color to apply during looping procedure """
        # extract current color tracking state
        hue, sat, val = self.color_decision_to_application[str(base_color)]

        if hue in color_settings.ENTITIES_HUES_WITHOUT_CYCLING:
            # for these entities, we do not cycle through the color space
            return

        _, sat_base, val_base = base_color

        # only modify the val
        val -= color_settings.SAT_VAL_STEP
        # we need less steps before reset for regular elements
        if val < color_settings.NONTABLE_VAL_MIN:
            val = val_base

        # save in mapping
        new_color = (hue, sat, val)
        self.color_decision_to_application[str(base_color)] = new_color
        self._used_colors[str(base_color)].add(new_color)

    def assign_par_color(self, par: Paragraph, base_color,
                         run_colorization_mask: List[int] = None,
                         decision_source=None) -> None:
        r"""assign a color to a paragraph
        @param par: an object obtained from docx.text.paragraph
        @param base_color: a color constant from settings.colors (hsv encoded)
        @param run_colorization_mask: It may sometimes be desirable to only
            color certain runs, for example in order to keep bounding boxes
            tight. If this is not none, then only the runs of the paragraph at
            the given index will be colored, and no (further) style will be
            applied to the entire paragraph.
        @param decision_source: How the colorization decision was made (see
            settings.annotation).
        """
        if (
                base_color == color_settings.COLOR_WHITESPACE
                or par.text.isspace()
                or len(par.text) == 0
        ):
            return

        # applying a default style may have side effects
        # although normal style should always be applied in renderer to
        # undef-style paragraphs by default
        if par.style is None:
            return

        # get color to actually use
        color = self.color_decision_to_application[str(base_color)]
        # and update for the next appearance of this element
        self.__update_application_color(base_color)

        r, g, b = hsv_to_rgb(hsv_color=color)
        color_hex = rgb_to_hex(rgb_color=(r, g, b))

        colorized_text = par.text

        if run_colorization_mask is None:
            shade_element(par._p.get_or_add_pPr(), color_hex=color_hex)
            # colorize font same as background shading
            par.style.font.color.rgb = RGBColor(r=r, g=g, b=b)
            for run in par.runs:
                shade_element(run._r.get_or_add_rPr(), color_hex=color_hex)
                run.font.color.rgb = RGBColor(r=r, g=g, b=b)
        else:
            # ! only color the runs at index allowed by the mask
            # and do not style the paragraph any extra
            colorized_text = ""
            for run_index in range(len(par.runs)):
                if run_index in run_colorization_mask:
                    run = par.runs[run_index]
                    colorized_text += run.text
                    if not (run.text.isspace()):
                        shade_element(
                            run._r.get_or_add_rPr(), color_hex=color_hex
                        )
                        run.font.color.rgb = RGBColor(r=r, g=g, b=b)

        # to deal with rels / hyperlinks in normal text, we can for now just
        # make them the same color as the par
        # !important: This requires us to go directly into the XML, using lxml
        # in python
        par_xml = par._p
        for child_element in list(par_xml):
            if "hyperlink" in child_element.tag:
                for possible_run in child_element.iterchildren():
                    if isinstance(possible_run, CT_R):
                        # now we can colour it normally
                        run = Run(possible_run, par)
                        run.font.color.rgb = RGBColor(r=r, g=g, b=b)
                        shade_element(
                            run._r.get_or_add_rPr(), color_hex=color_hex
                        )

        # track the colorization of this paragraph
        if decision_source is not None:
            entity_id = color_settings.get_entity_category_id(str(base_color))
            self.update_colorization_decisions(
                text=colorized_text,
                decision_source=decision_source,
                entity_decision=entity_id
            )

    def assign_run_color(
            self, run: Run, base_color,
            decision_source=None
    ) -> None:
        r"""assign a color to a single unwrapped run (in some rare cases, runs
        appear unwrapped by a paragraph)
        @param run: an object obtained from docx.text.run
        @param base_color: a color constant from color_cube_entities
            (hsv encoded)
        @param decision_source: How the colorization decision was made
        """
        if (
                base_color == color_settings.COLOR_WHITESPACE
                or run.text.isspace()
                or len(run.text) == 0
        ):
            return

        # get color to actually use
        color = self.color_decision_to_application[str(base_color)]
        # and update for the next appearance of this element
        self.__update_application_color(base_color)

        r, g, b = hsv_to_rgb(hsv_color=color)
        color_hex = rgb_to_hex(rgb_color=(r, g, b))

        if decision_source:
            self.update_colorization_decisions(
                run.text, decision_source,
                color_settings.get_entity_category_id(str(base_color))
            )

        run.font.color.rgb = RGBColor(r=r, g=g, b=b)
        shade_element(run._r.get_or_add_rPr(), color_hex=color_hex)

    def __handle_run_colorization(
            self, par: Paragraph, maincol, runcols,
    ):
        r"""assign a color to a paragraph, while considering that some runs may
        be different
        @param par: T Paragraph object, where we believe some runs may require
            special consideration
        @param maincol: The color based on the paragraph (pPr element) style
        @param runcols: The colors (multiple) based on individual run styling
            (rPr elements!); must be same length as par.runs
        """

        # first do normal coloring of the par
        self.assign_par_color(par, maincol)

        # now give special consideration to the runs!
        # do this after default paragraph behavior

        # ! we should not always consider recommended differences in runs.
        # this should really only be applied if we consider the main color
        # to be the body color
        if maincol in CONSIDER_RUN_COLORING_FOR:
            for i in range(len(par.runs)):
                run = par.runs[i]
                # ! careful not to color whitespace (preserve bbox separation)
                if len(run.text) != 0:
                    # ! no need to perform looping here, as this is handled in
                    # assign_par_color
                    runcol = runcols[i]

                    # we should only consider headings if:
                    # They are the first run
                    # They continue an existing heading (e.g underlined vs.
                    #   non-underlined part)
                    # they immediately follow a carriage return
                    if runcol in color_settings.COLORS_SECTION_HEADINGS:
                        if (
                                i != 0
                                and (runcols[i - 1] != runcol)
                                and (not par.runs[i - 1].text.endswith('\r'))
                        ):
                            runcol = maincol

                    # again go to actual applicable color
                    runcol_cycled = self.color_decision_to_application[
                        str(runcol)
                    ]
                    r, g, b = hsv_to_rgb(hsv_color=runcol_cycled)
                    color_hex = rgb_to_hex(rgb_color=(r, g, b))

                    # check if this leads to creation of a new element
                    if (runcol != maincol) and (not run.text.isspace()):
                        shade_element(
                            run._r.get_or_add_rPr(), color_hex=color_hex
                        )
                        run.font.color.rgb = RGBColor(r=r, g=g, b=b)
                        self.__update_application_color(runcol)

    def assign_par_color_considering_runs(
            self,
            par: Paragraph,
            para_heuristics: ParagraphHeuristic,
            original_was_builtin: bool,
            original_builtin_entity_id: int
    ):
        r""" Check individual run-level attributes of a paragraph.

        Note: In the heuristics module, we still attempt to conserve
            "guaranteed" builtin information as long as no run overrides it.

        Note: For some elements (currently only body), we still use heuristics
        to Try to extract some interesting information, therefore we have the
        original_was_builtin and original_builtin_entity @params.
        """
        (
            potential_color,
            potential_run_colors,
            decision_source
        ) = para_heuristics.get_heuristic_with_runs(par)

        if potential_color is None:
            return

        # !important: in heuristics situation, it makes sense to consider
        # individual runs
        self.__handle_run_colorization(
            par, potential_color, potential_run_colors
        )

        for run_index in range(len(par.runs)):
            run = par.runs[run_index]
            recommended_entity_id = color_settings.get_entity_category_id(
                color=potential_run_colors[run_index]
            )

            # no recommendation made
            if recommended_entity_id is None:
                continue

            # if the original was builtin, we need to consider the
            # whether the run was recognized the same as the original
            # entity
            if (
                    original_was_builtin and
                    recommended_entity_id != original_builtin_entity_id
            ):
                # for every run that is not the same as builtin --> track
                # as heuristic that created it
                self.update_colorization_decisions(
                    text=run.text,
                    decision_source=decision_source,
                    entity_decision=recommended_entity_id
                )
            elif (
                    original_was_builtin and
                    recommended_entity_id == original_builtin_entity_id
            ):
                # run was builtin and did not get overridden --> track as
                # builtin
                self.update_colorization_decisions(
                    text=run.text,
                    decision_source=annotation_settings.ANNOTATION_BUILTIN,
                    entity_decision=original_builtin_entity_id
                )
            else:
                # original was not builtin --> track all runs as respective
                # heuristic decision
                self.update_colorization_decisions(
                    text=run.text,
                    decision_source=decision_source,
                    entity_decision=recommended_entity_id
                )

    def aggregate_colorization_decisions(self) -> Dict[int, int]:
        r""" Aggregate colorization decisions to get a count of how many
        characters were recognized by which source.

        @return: Dict of annotation_source to count
        """
        source_counts = dict.fromkeys(
            annotation_settings.DECISION_SOURCES + [
                "text_builtin", "text_fallback"
            ], 0
        )

        for col_decision in self._colorization_decisions:
            if col_decision.entity_decision == entity_settings.ENTITY_TEXT_ID:
                if col_decision.decision_source == \
                        annotation_settings.ANNOTATION_BUILTIN:
                    decision_source = "text_builtin"
                else:
                    decision_source = "text_fallback"
            else:
                decision_source = col_decision.decision_source

            source_counts[decision_source] += len(col_decision.text or "")

        return source_counts

    @property
    def used_colors(self):
        r"""
        Get Colors that have been used during colorization, in order to draw
        bounding boxes
        """
        return self._used_colors

    @property
    def colorization_decisions(self):
        return self._colorization_decisions
