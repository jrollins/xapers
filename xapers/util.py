def xapian_term_iter(xapian_object, prefix=None):
    """Prefix term iterator for xapian objects

    `xapian_object` can be either a full database or a single
    document.  Iterates over all terms, or just those with prefix if
    specified

    """
    term_iter = iter(xapian_object)

    ownprefix = prefix and prefix.startswith('X')
    plen = len(prefix) if prefix else 0

    def get_value(term):
        # strip prefix
        term = term[plen:]
        # user-defined prefix with extra seperator inserted.
        if ownprefix and term.startswith(':'):
            return term[1:]
        else:
            return term

    if prefix:
        try:
            term = term_iter.skip_to(prefix).term.decode()
        except StopIteration:
            return
        if not term.startswith(prefix):
            return
        yield get_value(term)

    for tli in term_iter:
        term = tli.term.decode()
        if prefix:
            if not term.startswith(prefix):
                break
        yield get_value(term)


# https://xapian.org/docs/omega/termprefixes.html
# For a user-defined prefix (starting with 'X') the prefix and value are
# seperated with a ":" if the value starts with a capital letter or ":" to
# resolve ambiguity.
def get_full_term(prefix, value):
    # convert to string
    value = str(value)
    if prefix is not None and prefix.startswith('X') and \
            value[0].isupper() or value.startswith(':'):
        return '%s:%s' % (prefix, value)
    else:
        return '%s%s' % (prefix, value)
