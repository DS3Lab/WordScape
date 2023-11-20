from docx.document import Document
from docx.oxml.ns import qn
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.oxml.text.run import CT_R
from docx.text.run import Run

from src.annotation.colorization import ColorizationHandler

import settings


def colorize_builtin_toc_elements(
        doc: Document,
        colorization_handler: ColorizationHandler,
):
    r"""
    Colorizes builtin elements of the type toc_link, and toc.
    Note this needs its own entity handler, because the toc items do not appear
    as first-level paragraph elements, although their contents are embedded in
    paragraph and run elements. Also colorizes Bibliographies, due to their
    similar XML structure.

    @param doc: Document to colorize tocs in
    @param colorization_handler: Tracking handler for colorization decisions
    """

    # ! TOC indicator: w:sdt --> w:sdtPr --> w:docPartObj --> w:docPartGallery
    # --> run / para on same level as sdtPr # noqa
    # find the paragraphs or runs that match this configuration!
    # because of this we need to color TOC BEFORE forms, but after
    # everything else

    # a sdtContent will always contain either only paragraphs, or only runs
    doc_part_gallery_indicators = doc.element.body.xpath(
        "//w:sdt//descendant::w:sdtPr//descendant::w:docPartObj"
        "//descendant::w:docPartGallery"
    )
    # get the sdtContents that are on the same level as the sdtPr containing
    # the indicator tag
    sdt_parents = []
    docpart_vals = []
    for indicator in doc_part_gallery_indicators:
        doc_part_obj = indicator.xpath("..")[0]
        sdt_pr = doc_part_obj.xpath("..")[0]
        sdt = sdt_pr.xpath("..")[0]
        sdt_parents.append(sdt)
        if indicator.attrib[qn('w:val')]:
            docpart_vals.append(indicator.attrib[qn('w:val')])
        else:
            docpart_vals.append(
                settings.colors.get_entity_name(settings.colors.COLOR_TOC))
    # make the resulting list unique
    sdt_parents = list(set(sdt_parents))

    # xpath can figure out the
    # w: prefix above, but not in the below loop.
    # in the below loop we need to specify the prefix --> 
    # namespace mapping ourselves

    if len(sdt_parents) == 0:
        return

    # ! because of a (presumable?) bug we need to manually get the prefix
    # mapping and refresh it in below loop
    if not (sdt_parents[0].nsmap["w"]):
        return
    w_prefix_to_namespace = sdt_parents[0].nsmap["w"]

    # colorize the indicated runs / paragraphs as TOCs
    for i in range(len(sdt_parents)):
        sdt = sdt_parents[i]
        # get the sdtContent
        sdt_content_run = sdt.xpath(
            ".//descendant::w:sdtContent//descendant::w:r",
            namespaces={"w": w_prefix_to_namespace}
        )

        sdt_content_par = sdt.xpath(
            ".//descendant::w:sdtContent//descendant::w:p",
            namespaces={"w": w_prefix_to_namespace}
        )

        # remove the runs covered by paragraphs
        # for par in sdtContent_par:
        #     for child in sdtContent_par:
        #         if child in sdtContent_run:
        #             sdtContent_run.remove(child)

        sdt_content = sdt_content_run + sdt_content_par
        # determine wether this is a toc (default case)
        # or a bibliography (special indicator)
        color = settings.colors.COLOR_TOC
        if 'bib' in docpart_vals[i].lower():
            color = settings.colors.COLOR_BIBLIOGRAPHY

        for par_or_run_child in sdt_content:
            # get pars or runs
            if isinstance(par_or_run_child, CT_P):
                par = Paragraph(par_or_run_child, doc)
                colorization_handler.assign_par_color(
                    par, color,
                    decision_source=settings.annotation.ANNOTATION_XML_PATTERN
                )
            elif isinstance(par_or_run_child, CT_R):
                run = Run(par_or_run_child, CT_R)
                colorization_handler.assign_run_color(
                    run, base_color=color,
                    decision_source=settings.annotation.ANNOTATION_XML_PATTERN
                )
            else:
                raise ValueError(
                    "Unexpected Type {} encountered during TOC colorization "
                    "based on docPartGallery indicator tag".format(
                        str(type(par_or_run_child))
                    )
                )
