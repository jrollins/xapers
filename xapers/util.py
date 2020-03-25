def xapian_term_iter(xapian_object, prefix=None):
    """Prefix term iterator for xapian objects

    `xapian_object` can be either a full database or a single
    document.  Iterates over all terms, or just those with prefix if
    specified

    """
    term_iter = iter(xapian_object)
    if prefix:
        plen = len(prefix)
        term = term_iter.skip_to(prefix).term.decode()
        if not term.startswith(prefix):
            return
        yield term[plen:]
    for tli in term_iter:
        term = tli.term.decode()
        if prefix:
            if not term.startswith(prefix):
                break
            yield term[plen:]
        else:
            yield term
