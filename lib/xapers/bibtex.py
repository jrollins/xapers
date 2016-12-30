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
import io
import json
import pybtex
from pybtex.bibtex.utils import split_name_list
from pybtex.database import Entry, Person
from pybtex.database.input import bibtex as inparser
from pybtex.database.output import bibtex as outparser


def clean_bib_string(string):
    for char in ['{', '}']:
        string = string.replace(char,'')
    return string

##################################################

class BibtexError(Exception):
    """Base class for Xapers bibtex exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

##################################################

class Bibtex():
    """Represents a bibtex database.

    """
    # http://www.bibtex.org/Format/
    def __init__(self, bibtex):

        parser = inparser.Parser(encoding='utf-8')

        if os.path.exists(bibtex):
            bibdata = parser.parse_file(bibtex)
        else:
            # StringIO requires unicode input
            # http://nedbatchelder.com/text/unipain.html
            assert type(bibtex) is unicode, "Bibtex strings must be unicode"
            with io.StringIO(bibtex) as stream:
                bibdata = parser.parse_stream(stream)

        self.keys = bibdata.entries.keys()
        self.entries = bibdata.entries.values()

        self.index = -1
        self.max = len(self.entries)

    def __getitem__(self, index):
        key = self.keys[index]
        entry = self.entries[index]
        return Bibentry(key, entry)

    def __iter__(self):
        return self

    def __len__(self):
        return self.max

    def next(self):
        self.index = self.index + 1
        if self.index == self.max:
            raise StopIteration
        return self[self.index]

##################################################

class Bibentry():
    """Represents an individual entry in a bibtex database.

    """
    def __init__(self, key, entry):
        self.key = key
        self.entry = entry

    def get_authors(self):
        """Return a list of authors."""
        authors = []
        if 'author' in self.entry.persons:
            for p in self.entry.persons['author']:
                authors.append(clean_bib_string(unicode(p)))
        return authors

    def get_fields(self):
        """Return a dict of non-author fields."""
        bibfields = self.entry.fields
        # entry.fields is actually already a dict, but we want to
        # clean the strings first
        fields = {}
        for field in bibfields:
            fields[field] = unicode(clean_bib_string(bibfields[field]))
        return fields

    def set_file(self, path):
        # FIXME: what's the REAL proper format for this
        self.entry.fields['file'] = ':%s:%s' % (path, 'pdf')

    def get_file(self):
        """Returns file path if file field exists.

        Expects either single path string or Mendeley/Jabref format.

        """
        try:
            parsed = self.entry.fields['file'].split(':')
            if len(parsed) > 1:
                return parsed[1]
            else:
                return parsed[0]
        except KeyError:
            return None
        except IndexError:
            return None

    def _entry2db(self):
        db = pybtex.database.BibliographyData()
        db.add_entry(self.key, self.entry)
        return db

    def as_string(self):
        """Return entry as formatted bibtex string."""
        writer = outparser.Writer()
        with io.StringIO() as stream:
            writer.write_stream(self._entry2db(), stream)
            string = stream.getvalue()
        string = string.strip()
        return string

    def to_file(self, path):
        """Write entry bibtex to file."""
        writer = outparser.Writer(encoding='utf-8')
        writer.write_file(self._entry2db(), path)

##################################################

def data2bib(data, key, type='article'):
    """Convert a python dict into a Bibentry object."""

    if not data:
        return

    # need to remove authors field from data
    authors = None
    if 'authors' in data:
        authors = data['authors']
        if isinstance(authors, str):
            authors = split_name_list(authors)
            if len(authors) == 1:
                authors = authors[0].split(',')
        del data['authors']

    entry = Entry(type, fields=data)
    if authors:
        for p in authors:
            entry.add_person(Person(p), 'author')

    return Bibentry(key, entry).as_string()


def json2bib(jsonstring, key, type='article'):
    """Convert a json string into a Bibentry object."""

    if not json:
        return

    data = json.loads(jsonstring)

    # need to remove authors field from data
    authors = None
    if 'author' in data:
        authors = data['author']
        del data['author']

    if 'issued' in data:
        data['year'] = str(data['issued']['date-parts'][0][0])
        del data['issued']

    # delete other problematic fields
    if 'editor' in data:
        del data['editor']

    entry = Entry(type, fields=data)

    if authors:
        for author in authors:
            entry.add_person(Person(first=author['given'], last=author['family']), 'author')

    return Bibentry(key, entry).as_string()
