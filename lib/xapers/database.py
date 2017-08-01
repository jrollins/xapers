"""
This file is part of xapers.

Xapers is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your
option) any later version.

Xapers is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
for more details.

You should have received a copy of the GNU General Public License
along with xapers.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2012-2017
Jameson Rollins <jrollins@finestructure.net>
"""

import os
import sys
import xapian

from .source import Sources
from .documents import Documents, Document

# FIXME: add db schema documentation

##################################################

class DatabaseError(Exception):
    """Base class for Xapers database exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class DatabaseUninitializedError(DatabaseError):
    pass

class DatabaseInitializationError(DatabaseError):
    pass

class DatabaseLockError(DatabaseError):
    pass

##################################################

class Database():
    """Represents a Xapers database"""

    # http://xapian.org/docs/omega/termprefixes.html
    BOOLEAN_PREFIX = {
        'id': 'Q',
        'key': 'XBIB|',
        'source': 'XSOURCE|',
        'year': 'Y',
        'y': 'Y',
        }
    # boolean prefixes for which there can be multiple per doc
    BOOLEAN_PREFIX_MULTI = {
        'tag': 'K',
        }
    # purely internal prefixes
    BOOLEAN_PREFIX_INTERNAL = {
        # FIXME: use this for doi?
        #'url': 'U',
        'file': 'P',

        # FIXME: use this for doc mime type
        'type': 'T',
        }

    PROBABILISTIC_PREFIX = {
        'title': 'S',
        't': 'S',
        'author': 'A',
        'a': 'A',
        }

    # http://xapian.org/docs/facets
    NUMBER_VALUE_FACET = {
        'year': 0,
        'y': 0,
        }

    # FIXME: need to set the following value fields:
    # publication date
    # added date
    # modified date

    # FIXME: need database version

    def _find_prefix(self, name):
        # FIXME: make this a dictionary union
        if name in self.BOOLEAN_PREFIX:
            return self.BOOLEAN_PREFIX[name]
        if name in self.BOOLEAN_PREFIX_MULTI:
            return self.BOOLEAN_PREFIX_MULTI[name]
        if name in self.BOOLEAN_PREFIX_INTERNAL:
            return self.BOOLEAN_PREFIX_INTERNAL[name]
        if name in self.PROBABILISTIC_PREFIX:
            return self.PROBABILISTIC_PREFIX[name]

    def _find_facet(self, name):
        if name in self.NUMBER_VALUE_FACET:
            return self.NUMBER_VALUE_FACET[name]

    def _make_source_prefix(self, source):
        return 'X%s|' % (source.upper())

    ########################################

    def __init__(self, root, writable=False, create=False, force=False):
        # xapers root
        self.root = os.path.abspath(os.path.expanduser(root))

        # xapers db directory
        xapers_path = os.path.join(self.root, '.xapers')

        # xapes directory initialization
        if not os.path.exists(xapers_path):
            if create:
                if os.path.exists(self.root):
                    if os.listdir(self.root) and not force:
                        raise DatabaseInitializationError('Uninitialized Xapers root directory exists but is not empty.')
                os.makedirs(xapers_path)
            else:
                if os.path.exists(self.root):
                    raise DatabaseInitializationError("Xapers directory '%s' does not contain a database." % (self.root))
                else:
                    raise DatabaseUninitializedError("Xapers directory '%s' not found." % (self.root))

        # the Xapian db
        xapian_path = os.path.join(xapers_path, 'xapian')
        if writable:
            try:
                self.xapian = xapian.WritableDatabase(xapian_path, xapian.DB_CREATE_OR_OPEN)
            except xapian.DatabaseLockError:
                raise DatabaseLockError("Xapers database locked.")
        else:
            self.xapian = xapian.Database(xapian_path)

        stemmer = xapian.Stem("english")

        # The Xapian TermGenerator
        # http://trac.xapian.org/wiki/FAQ/TermGenerator
        self.term_gen = xapian.TermGenerator()
        self.term_gen.set_stemmer(stemmer)

        # The Xapian QueryParser
        self.query_parser = xapian.QueryParser()
        self.query_parser.set_database(self.xapian)
        self.query_parser.set_stemmer(stemmer)
        self.query_parser.set_stemming_strategy(xapian.QueryParser.STEM_SOME)
        self.query_parser.set_default_op(xapian.Query.OP_AND)

        # add boolean internal prefixes
        for name, prefix in self.BOOLEAN_PREFIX.items():
            self.query_parser.add_boolean_prefix(name, prefix)
        # for prefixes that can be applied multiply to the same
        # document (like tags) set the filter grouping to use AND:
        # https://xapian.org/docs/apidoc/html/classXapian_1_1QueryParser.html#a67d25f9297bb98c2101a03ff3d60cf30
        for name, prefix in self.BOOLEAN_PREFIX_MULTI.items():
            self.query_parser.add_boolean_prefix(name, prefix, False)

        # add probabalistic prefixes
        for name, prefix in self.PROBABILISTIC_PREFIX.items():
            self.query_parser.add_prefix(name, prefix)

        # add value facets
        for name, facet in self.NUMBER_VALUE_FACET.items():
            self.query_parser.add_valuerangeprocessor(
                xapian.NumberValueRangeProcessor(facet, name+':')
                )

        # register known source prefixes
        # FIXME: can we do this by just finding all XSOURCE terms in
        #        db?  Would elliminate dependence on source modules at
        #        search time.
        for source in Sources():
            name = source.name
            self.query_parser.add_boolean_prefix(name, self._make_source_prefix(name))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.xapian.close()

    def reopen(self):
        self.xapian.reopen()

    def __contains__(self, docid):
        try:
            self.xapian.get_document(docid)
            return True
        except xapian.DocNotFoundError:
            return False

    def __getitem__(self, docid):
        if type(docid) not in [int, int]:
            raise TypeError("docid must be an int")
        xapian_doc = self.xapian.get_document(docid)
        return Document(self, xapian_doc)

    ########################################

    # generate a new doc id, based on the last availabe doc id
    def _generate_docid(self):
        return self.xapian.get_lastdocid() + 1

    ########################################

    # return a list of terms for prefix
    def _term_iter(self, prefix=None):
        term_iter = iter(self.xapian)
        if prefix:
            plen = len(prefix)
            term = term_iter.skip_to(prefix)
            if not term.term.startswith(prefix):
                return
            yield term.term[plen:]
        for term in term_iter:
            if prefix:
                if not term.term.startswith(prefix):
                    break
                yield term.term[plen:]
            else:
                yield term.term

    def term_iter(self, name=None):
        """Generator of all terms in the database.

        If a prefix is provided, will iterate over only the prefixed
        terms, and the prefix will be removed from the returned terms.

        """
        prefix = None
        if name:
            prefix = self._find_prefix(name)
            if not prefix:
                prefix = name
        return self._term_iter(prefix)

    def sid_iter(self):
        """Generator of all source ids in database"""
        for source in self.term_iter('source'):
            # FIXME: do this more efficiently
            for oid in self._term_iter(self._make_source_prefix(source)):
                yield '%s:%s' % (source, oid)

    def get_sids(self):
        """Get all source ids in database as a list"""
        return [sid for sid in self.sid_iter()]

    def tag_iter(self):
        """Generator of all tags in database"""
        for tag in self.term_iter('tag'):
            yield tag

    def get_tags(self):
        """Get all tags in database as a list"""
        return [tag for tag in self.tag_iter()]

    ########################################

    # search for documents based on query string and return mset
    def _search(self, query_string, sort='relevance', limit=None):
        enquire = xapian.Enquire(self.xapian)

        # FIXME: add option for ascending/descending
        if sort == 'relevance':
            enquire.set_sort_by_relevance_then_value(self.NUMBER_VALUE_FACET['year'], True)
        elif sort == 'year':
            enquire.set_sort_by_value_then_relevance(self.NUMBER_VALUE_FACET['year'], True)
        else:
            raise ValueError("sort parameter accepts only 'relevance' or 'year'")

        if query_string == "*":
            query = xapian.Query.MatchAll
        else:
            # parse the query string to produce a Xapian::Query object.
            query = self.query_parser.parse_query(query_string)

        if os.getenv('XAPERS_DEBUG_QUERY'):
            print("query string:", query_string, file=sys.stderr)
            print("final query:", query, file=sys.stderr)

        # FIXME: need to catch Xapian::Error when using enquire
        enquire.set_query(query)

        # set order of returned docs as newest first
        # FIXME: make this user specifiable
        enquire.set_docid_order(xapian.Enquire.DESCENDING)

        if limit:
            mset = enquire.get_mset(0, limit)
        else:
            mset = enquire.get_mset(0, self.xapian.get_doccount())

        return mset

    def search(self, query_string, sort='relevance', limit=None):
        """Search for documents in the database.

        The `sort` keyword argument can be 'relevance' (default) or
        'year'.  `limit` can be used to limit the number of returned
        documents (default is None).

        """
        mset = self._search(query_string, sort=sort, limit=limit)
        return Documents(self, mset)

    def count(self, query_string):
        """Count documents matching search terms."""
        return self._search(query_string).get_matches_estimated()

    def _doc_for_term(self, term):
        enquire = xapian.Enquire(self.xapian)
        query = xapian.Query(term)
        enquire.set_query(query)
        mset = enquire.get_mset(0, 2)
        # FIXME: need to throw an exception if more than one match found
        if mset:
            return Document(self, mset[0].document)
        else:
            return None

    def doc_for_path(self, path):
        """Return document for specified path."""
        term = self._find_prefix('file') + path
        return self._doc_for_term(term)

    def doc_for_source(self, sid):
        """Return document for source id string."""
        source, oid = sid.split(':', 1)
        term = self._make_source_prefix(source) + oid
        return self._doc_for_term(term)

    def doc_for_bib(self, bibkey):
        """Return document for bibtex key."""
        term = self._find_prefix('key') + bibkey
        return self._doc_for_term(term)

    ########################################

    def replace_document(self, docid, doc):
        """Replace (sync) document to database."""
        self.xapian.replace_document(docid, doc)

    def delete_document(self, docid):
        """Delete document from database."""
        self.xapian.delete_document(docid)

    ########################################

    def restore(self, log=False):
        """Restore a database from an existing root."""
        docdirs = os.listdir(self.root)
        docdirs.sort()
        for ddir in docdirs:
            docdir = os.path.join(self.root, ddir)

            # skip things that aren't directories
            if not os.path.isdir(docdir):
                continue

            # if we can't convert the directory name into an integer,
            # assume it's not relevant to us and continue
            try:
                docid = int(ddir)
            except ValueError:
                continue

            if log:
                print(docdir, file=sys.stderr)

            docfiles = os.listdir(docdir)
            if not docfiles:
                # skip empty directories
                continue

            if log:
                print('  docid:', docid, file=sys.stderr)

            try:
                doc = self[docid]
            except xapian.DocNotFoundError:
                doc = Document(self, docid=docid)

            for dfile in docfiles:
                dpath = os.path.join(docdir, dfile)
                if dfile == 'bibtex':
                    if log:
                        print('  adding bibtex', file=sys.stderr)
                    doc.add_bibtex(dpath)
                elif dfile == 'tags':
                    if log:
                        print('  adding tags', file=sys.stderr)
                    with open(dpath, 'r') as f:
                        tags = f.read().strip().split('\n')
                    doc.add_tags(tags)
                else: #elif os.path.splitext(dpath)[1] == '.pdf':
                    if log:
                        print('  adding file:', dfile, file=sys.stderr)
                    doc.add_file(dpath)
            doc.sync()
