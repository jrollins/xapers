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
along with notmuch.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2012
Jameson Rollins <jrollins@finestructure.net>
"""

import os
import sys
import shutil
import xapian
import xapers.bibtex

##################################################

class DocumentError(Exception):
    """Base class for Xapers document exceptions."""
    pass

class IllegalImportPath(DocumentError):
    pass

class ImportPathExists(DocumentError):
    def __init__(self, docid):
        self.docid = docid

##################################################

class Documents():
    """Represents a set of Xapers documents given a Xapian mset."""

    def __init__(self, db, mset):
        # Xapers db
        self.db = db
        self.mset = mset
        self.index = -1
        self.max = len(mset)

    def __iter__(self):
        return self

    def next(self):
        self.index = self.index + 1
        if self.index == self.max:
            raise StopIteration
        m = self.mset[self.index]
        doc = Document(self.db, m.document)
        doc.matchp = m.percent
        return doc

##################################################

class Document():
    """Represents a single Xapers document."""

    def __init__(self, db, doc=None):
        # Xapers db
        self.db = db
        self.root = self.db.root

        # if Xapian doc provided, initiate for that document
        if doc:
            self.doc = doc
            self.docid = doc.get_docid()
            self.path = self._get_terms(self.db._find_prefix('file'))

        # else, create a new empty document
        # document won't be added to database until sync is called
        else:
            self.doc = xapian.Document()
            self.docid = self.db._generate_docid()
            self._add_term(self.db._find_prefix('id'), self.docid)

        # specify a directory in the Xapers root for document data
        self.docdir = os.path.join(self.root, '%010d' % int(self.docid))

    def get_docid(self):
        """Return document id of document."""
        return self.docid

    def _make_docdir(self):
        os.makedirs(self.docdir)

    def _rm_docdir(self):
        if os.path.exists(self.docdir):
            shutil.rmtree(self.docdir)

    def sync(self):
        """Sync document to database."""
        self.db.replace_document(self.docid, self.doc)

    def purge(self):
        try:
            self.db.delete_document(self.docid)
        except xapian.DocNotFoundError:
            pass
        self._rm_docdir()

    ########################################
    # internal stuff

    # FIXME: should we add equivalent of
    # _notmuch_message_ensure_metadata, that would extract fields from
    # the xapian document?

    # add an individual prefix'd term for the document
    def _add_term(self, prefix, value):
        term = '%s%s' % (prefix, value)
        self.doc.add_term(term)

    # remove an individual prefix'd term for the document
    def _remove_term(self, prefix, value):
        term = '%s%s' % (prefix, value)
        self.doc.remove_term(term)

    # Parse 'text' and add a term to 'message' for each parsed
    # word. Each term will be added both prefixed (if prefix_name is
    # not NULL) and also non-prefixed).
    # http://xapian.org/docs/bindings/python/
    # http://xapian.org/docs/quickstart.html
    # http://www.flax.co.uk/blog/2009/04/02/xapian-search-architecture/
    def _gen_terms(self, prefix, text):
        term_gen = self.db.term_gen
        term_gen.set_document(self.doc)
        if prefix:
            term_gen.index_text(text, 1, prefix)
        term_gen.index_text(text)
            
    # return a list of terms for prefix
    # FIXME: is this the fastest way to do this?
    def _get_terms(self, prefix):
        list = []
        for term in self.doc:
            if term.term.find(prefix) == 0:
                index = len(prefix)
                list.append(term.term[index:])
        return list

    # set the data object for the document
    def _set_data(self, text):
        self.doc.set_data(text)

    def get_data(self):
        """Get data object for document."""
        return self.doc.get_data()

    ########################################
    # files

    # index/add a new file for the document
    # file should be relative to xapian.root
    # FIXME: codify this more
    def _index_file(self, path):
        base, full = self.db._basename_for_path(path)

        # FIXME: pick parser based on mime type
        from .parsers import pdf as parser
        text = parser.parse_file(full)

        # FIXME: set mime type term

        self._gen_terms(None, text)

        summary = text[0:997].translate(None,'\n') + '...'

        return summary

    def _add_path(self, path):
        base, full = self.db._basename_for_path(path)
        prefix = self.db._find_prefix('file')
        self._add_term(prefix, base)

    def _get_paths(self):
        return self._get_terms(self.db._find_prefix('file'))

    def get_fullpaths(self):
        """Return fullpaths associated with document."""
        list = []
        for path in self._get_paths():
            # FIXME: this is a hack for old bad path specifications and should be removed
            if path.find(self.root) == 0:
                index = len(self.root) + 1
                path = path[index:]
            path = path.lstrip('/')
            # FIXME
            base, full = self.db._basename_for_path(path)
            list.append(full)
        return list

    def add_file(self, infile):
        """Add a file to document, copying into new xapers doc directory."""
        # base, full = self.db._basename_for_path(path)
        # if not base:
        #     raise IllegalImportPath()

        # FIXME: do we really need to do this check?
        # doc = self.db.doc_for_path(base)
        # if doc:
        #     raise ImportPathExists(doc.get_docid())

        self._make_docdir()
        outfile = os.path.join(self.docdir, os.path.basename(infile))
        shutil.copyfile(infile, outfile)

        base, full = self.db._basename_for_path(outfile)

        summary = self._index_file(full)

        self._add_path(base)

        # set data to be text sample
        # FIXME: what should really be in here?  what if we have
        # multiple files for the document?  what about bibtex?
        self._set_data(summary)

        return full

    ########################################

    # SOURCES
    def add_sources(self, sources):
        """Add sources from dict (source:sid)."""
        p = self.db._find_prefix('source')
        for source,sid in sources.items():
            source = source.lower()
            self._add_term(p, source)
            sp = self.db._make_source_prefix(source)
            self._add_term(sp, sid)

    def get_source_id(self, source):
        """Return source id for specified source."""
        # FIXME: this should produce a single term
        prefix = self.db._make_source_prefix(source)
        sid = self._get_terms(prefix)
        if sid:
            return sid[0]
        else:
            return None

    def get_sources(self):
        """Return a source:sid dictionary associated with document."""
        prefix = self.db._find_prefix('source')
        sources = {}
        for source in self._get_terms(prefix):
            if not source:
                break
            sources[source] = self.get_source_id(source)
        return sources

    def get_sources_list(self):
        list = []
        sources = self.get_sources()
        for source,sid in sources.items():
            list.append('%s:%s' % (source,sid))
        return list

    def remove_source(self, source):
        """Remove source from document."""
        prefix = self.db._make_source_prefix(source)
        for sid in self._get_terms(prefix):
            self._remove_term(prefix, sid)
        self._remove_term(self.db._find_prefix('source'), source)

    # TAGS
    def add_tags(self, tags):
        """Add tags from list to document."""
        prefix = self.db._find_prefix('tag')
        for tag in tags:
            self._add_term(prefix, tag)
            # FIXME: index tags so they're searchable

    def get_tags(self):
        """Return a list of tags associated with document."""
        prefix = self.db._find_prefix('tag')
        return self._get_terms(prefix)

    def remove_tags(self, tags):
        """Remove tags from a document."""
        prefix = self.db._find_prefix('tag')
        for tag in tags:
            self._remove_term(prefix, tag)

    # TITLE
    def _set_title(self, title):
        pt = self.db._find_prefix('title')
        for term in self._get_terms(pt):
            self._remove_term(pt, term)
        # FIXME: what the clean way all these prefixed terms?
        for term in self._get_terms('ZS'):
            self._remove_term('ZS', term)
        self._gen_terms(pt, title)

    # AUTHOR
    def _set_authors(self, authors):
        pa = self.db._find_prefix('author')
        for term in self._get_terms(pa):
            self._remove_term(pa, term)
        # FIXME: what the clean way all these prefixed terms?
        for term in self._get_terms('ZA'):
            self._remove_term('ZA', term)
        self._gen_terms(pa, authors)

    # YEAR
    def _set_year(self, year):
        # FIXME: this should be a value
        pass
        prefix = self.db._find_prefix('year')
        for term in self._get_terms(prefix):
            self._remove_term(prefix, term)
        self._add_term(prefix, year)

    ########################################
    # bibtex

    def get_bibpath(self):
        return os.path.join(self.root, self.docdir, 'bibtex')

    def _set_bibkey(self, key):
        prefix = self.db._find_prefix('bib')
        for term in self._get_terms(prefix):
            self._remove_term(prefix, term)
        self._add_term(prefix, key)

    def _index_bibtex(self, bibtex):
        bibentry = xapers.bibtex.Bibentry(bibtex)
        data = bibentry.get_data()
        if 'title' in data:
            self._set_title(data['title'])
        if 'author' in data:
            self._set_authors(data['author'])
        if 'year' in data:
            self._set_year(data['year'])

        # FIXME: do this better for arbitrary source
        for source in ['doi', 'dcc', 'arxiv', 'ads']:
            if source in data:
                self.add_sources({source: data[source]})

        self._set_bibkey(bibentry.key)
        return bibentry

    def _write_bibfile(self, bibentry):
        bibfile = self.get_bibpath()
        f = open(bibfile, 'w')
        f.write(bibentry.as_string())
        f.write('\n')
        f.close()
        return bibfile

    def add_bibtex(self, bibtex):
        """Add bibtex to document."""
        self._make_docdir()
        bibentry = self._index_bibtex(bibtex)
        bibfile = self._write_bibfile(bibentry)
        return bibfile

    def get_bibtex(self):
        bibpath = self.get_bibpath()
        if not os.path.exists(bibpath):
            return
        f = open(bibpath, 'r')
        bibtex = f.read()
        f.close()
        return bibtex.strip()

    def get_bibentry(self):
        bibtex = self.get_bibtex()
        if bibtex:
            return xapers.bibtex.Bibentry(bibtex)
        else:
            return None

    def get_bibdata(self):
        bibentry = self.get_bibentry()
        if bibentry:
            return bibentry.get_data()
        else:
            return None

    ########################################

    def get_url(self):
        bibdata = self.get_bibdata()
        if 'url' in bibdata:
            return bibdata['url']
        else:
            return None
