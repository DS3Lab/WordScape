# handlers
from .colorization_handler import ColorizationHandler, ColorizationDecision
from .heuristics.build_heuristics import ParagraphHeuristic

# entities modules
from .entities import colorize_builtin_form_elements
from .entities import colorize_builtin_toc_elements
from .entities import colorize_figures
from .entities import colorize_header_and_footer
from .entities import colorize_paragraph
from .entities import colorize_table
from .entities import colorize_text_boxes
