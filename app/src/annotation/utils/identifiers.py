def get_page_id(doc_id: str, page_number: int) -> str:
    """ Generate a page id. """
    return f"{doc_id}_p{page_number:05d}"


def get_page_num_from_page_id(page_id: str) -> int:
    """ Extract the page number from a page id. """
    return int(page_id.split("_p")[-1])


def get_doc_id(cc_dump_id: str, doc_number: int) -> str:
    """ Generate a document id. """
    return f"doc_{cc_dump_id}_{doc_number:08d}"
