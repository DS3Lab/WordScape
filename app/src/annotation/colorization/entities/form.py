from docx.document import Document
from docx.oxml.text.paragraph import CT_P
from docx.text.paragraph import Paragraph
from docx.oxml.text.run import CT_R
from docx.text.run import Run

from src.annotation.colorization import ColorizationHandler
import settings


def colorize_builtin_form_elements(
        doc: Document,
        colorization_handler: ColorizationHandler,
):
    r"""
    Colorizes builtin elements of the type form, form fields and form tags.
    Note this needs its own entity handler, because the form fields do not
    appear as first-level paragraph elements, although their contents are
    embedded in paragraph and run elements.

    @param doc: Document to colorize forms in
    @param colorization_handler: Tracking handler for colorization decisions
    """

    # get all w:sdt elements; these contain w:sdtContent, which contain a
    # w:p Paragraph --> in standard form, this is both the form field and the
    # content

    # ! possibilities:
    # unlabeled variants
    # top level sdt --> paragraph
    # top level sdt --> run

    # labeled variants
    # top level paragraph --> other runs (labels) --> sdt --> paragraph
    # top level paragraph --> other runs (labels) --> sdt --> run

    para_sdt_para = doc.element.body.xpath(
        "//w:p//descendant::w:sdtContent//descendant::w:p"
    )
    para_sdt_run = doc.element.body.xpath(
        "//w:p//descendant::w:sdtContent//descendant::w:r"
    )
    sdtonly_para = doc.element.body.xpath("//w:sdtContent//descendant::w:p")
    sdtonly_run = doc.element.body.xpath("//w:sdtContent//descendant::w:r")

    # make runs and paragraphs unique
    para_unique = list(set(para_sdt_para + sdtonly_para))
    run_unique = list(set(para_sdt_run + sdtonly_run))

    # remove runs covered by existing paragraphs
    for para in para_unique:
        for run in para.xpath(".//descendant::w:r"):
            if run in run_unique:
                run_unique.remove(run)

    # ! remove situations where sdtContents have more than one child (these
    # may be other elements)
    para_unique_filtered = []
    run_unique_filtered = []
    for sdt_elem in para_unique + run_unique:
        # this is the sdtContent
        immediate_parent = sdt_elem.xpath("..")[0]
        if len(immediate_parent.getchildren()) == 1:
            if isinstance(sdt_elem, CT_P):
                para_unique_filtered.append(sdt_elem)
            if isinstance(sdt_elem, CT_R):
                run_unique_filtered.append(sdt_elem)
    para_unique = para_unique_filtered
    run_unique = run_unique_filtered

    # don't double-color already handled tag runs
    # ! use the run_colorization_mask parameter of assign_par_color to prevent
    # full-width coloring

    # handle paragraphs, in order of specificity
    for xml_elem in para_unique:
        # there is an outer wrapping paragraph

        if xml_elem in para_sdt_para:
            # get outer paragraph --> assign labels
            outer_par = xml_elem.xpath("(./ancestor::w:p)[last()]")[0]
            outer_sdt = xml_elem.xpath("(./ancestor::w:sdt)[last()]")[0]
            outer_par = Paragraph(outer_par, doc)

            # get tag-runs (should only be the run right before the field run)
            run_counter = -1
            for child in outer_par._p.iterchildren():
                if child == outer_sdt:
                    break
                elif isinstance(child, CT_R):
                    run_counter += 1

            run_mask = []
            if run_counter != -1:
                run_mask.append(run_counter)

            colorization_handler.assign_par_color(
                outer_par,
                settings.colors.COLOR_FORM_TAG,
                run_colorization_mask=run_mask,
                decision_source=settings.annotation.ANNOTATION_XML_PATTERN
            )

        # ! sdtContent with a paragraph inside it, ONLY occurs if the sdt is
        # not wrapped in any paragraph so, we should be safe in extracting out
        # the paragraph (with style), and deleting the sdt itself

        # grab the sdt parent
        sdt_content_parent = xml_elem.xpath("..")[0]
        sdt_parent = sdt_content_parent.xpath("..")[0]
        # to preserve ordering, set the sdt itself to this paragraph
        sdt_parent_parent = sdt_parent.xpath("..")[0]
        index = list(sdt_parent_parent).index(sdt_parent)
        sdt_parent_parent.remove(sdt_parent)
        sdt_parent_parent.insert(index, xml_elem)

        par = Paragraph(xml_elem, doc)

        colorization_handler.assign_par_color(
            par,
            settings.colors.COLOR_FORM_FIELD,
            run_colorization_mask=[i for i in range(len(par.runs))],
            decision_source=settings.annotation.ANNOTATION_XML_PATTERN
        )

    # handle runs, same as above
    for xml_elem in run_unique:
        # there is an outer wrapping paragraph
        if xml_elem in para_sdt_run:
            # get outer paragraph --> assign labels
            outer_par = xml_elem.xpath("(./ancestor::w:p)[last()]")[0]
            outer_sdt = xml_elem.xpath("(./ancestor::w:sdt)[last()]")[0]
            outer_par = Paragraph(outer_par, doc)

            # get tag-runs (should only be the run right before the field run)
            run_counter = -1
            for child in outer_par._p.iterchildren():
                if child == outer_sdt:
                    break
                elif isinstance(child, CT_R):
                    run_counter += 1

            run_mask = []
            if run_counter != -1:
                run_mask.append(run_counter)

            colorization_handler.assign_par_color(
                outer_par,
                settings.colors.COLOR_FORM_TAG,
                run_colorization_mask=run_mask,
                decision_source=settings.annotation.ANNOTATION_XML_PATTERN
            )

        run = Run(xml_elem, doc)
        colorization_handler.assign_run_color(
            run, settings.colors.COLOR_FORM_FIELD,
            settings.annotation.ANNOTATION_XML_PATTERN
        )

    # XML tags that need to be removed due to display issue in libreoffice
    remove_tags_from_sdt_pr = ["alias", "tag", "text"]
    removables = []
    for remove in remove_tags_from_sdt_pr:
        w_tags = doc.element.body.xpath("//w:sdt//w:sdtPr//w:" + remove)
        removables = list(set(removables + w_tags))

    for xml_elem in removables:
        immediate_parent = xml_elem.xpath("..")[0]
        immediate_parent.remove(xml_elem)
