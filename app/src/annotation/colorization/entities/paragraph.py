from docx.oxml.xmlchemy import serialize_for_reading
from docx.text.paragraph import Paragraph

import settings
from src.annotation.builtin_styles import BUILTIN_STYLES
from src.annotation.colorization import ColorizationHandler
from src.annotation.colorization import ParagraphHeuristic
from src.annotation.colorization.mappings import MAP_BUILTIN_TO_ENTITY_COLOR
from src.annotation.utils.color_utils import check_if_par_is_numbered


def colorize_paragraph(
        paragraph: Paragraph,
        colorization_handler: ColorizationHandler,
        paragraph_heuristics: ParagraphHeuristic
):
    r""" Colorize a paragraph. This function relies primarily on builtin styles
    to identify which category a paragraph belongs to. If no builtin style is
    found, we fall back to heuristics.

    @param paragraph: the paragraph to colorize
    @param colorization_handler: the colorization handler
    @param paragraph_heuristics: the paragraph heuristics
    """
    # skip paragraph if it has no style associated
    if paragraph.style is None:
        return

    # skip paragraph if it is empty
    par_style = paragraph.style.name.lower()
    par_text = "".join(s for s in paragraph.text if s not in ["\n", "\t"])
    if len(par_text) == 0 and "toc" not in par_style:
        return

    # if no built-in style, we can try to fall back to heuristics
    if par_style not in BUILTIN_STYLES:
        colorization_handler.assign_par_color_considering_runs(
            paragraph, paragraph_heuristics,
            original_was_builtin=False,
            original_builtin_entity_id=settings.entities.ENTITY_TEXT_ID
        )
        return

    # check the builtin --> entity mapping
    entity_color_found_for_builtin = None
    for possible_start in MAP_BUILTIN_TO_ENTITY_COLOR:
        if par_style.startswith(possible_start):
            entity_color_found_for_builtin = \
                MAP_BUILTIN_TO_ENTITY_COLOR[possible_start]

    # ! some entity types we want to deal with specially
    # ! this may include run-checking or detecting other entity signals
    if entity_color_found_for_builtin == settings.colors.COLOR_TEXT:
        attributes = set(
            paragraph._p.xml._attr_seq(serialize_for_reading(paragraph._p))
        )

        if "</m:oMath>" in attributes or "</m:oMathPara>" in attributes:
            colorization_handler.assign_par_color(
                par=paragraph,
                base_color=settings.colors.COLOR_EQUATION,
                decision_source=settings.annotation.ANNOTATION_XML_PATTERN
            )
        elif check_if_par_is_numbered(paragraph):
            colorization_handler.assign_par_color(
                par=paragraph,
                base_color=settings.colors.COLOR_LIST,
                decision_source=settings.annotation.ANNOTATION_XML_PATTERN
            )
        else:
            colorization_handler.assign_par_color_considering_runs(
                par=paragraph,
                para_heuristics=paragraph_heuristics,
                original_was_builtin=True,
                original_builtin_entity_id=settings.entities.ENTITY_TEXT_ID
            )

    elif entity_color_found_for_builtin is not None:
        colorization_handler.assign_par_color(
            par=paragraph,
            base_color=entity_color_found_for_builtin,
            decision_source=settings.annotation.ANNOTATION_BUILTIN
        )

    else:
        print(f"unrecognized style {par_style}")
