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

Copyright 2012-2016
Jameson Rollins <jrollins@finestructure.net>
"""

import os
import urwid
import subprocess
import collections

from ..cli import initdb
from ..database import DatabaseLockError

############################################################

def xdg_open(path):
    """open document file"""
    with open(os.devnull) as devnull:
        subprocess.Popen(['xdg-open', path],
                         stdin=devnull,
                         stdout=devnull,
                         stderr=devnull)

def xclip(text, isfile=False):
    """Copy text or file contents into X clipboard."""
    f = None
    if isfile:
        f = open(text, 'r')
        sin = f
    else:
        sin = subprocess.PIPE
    p = subprocess.Popen(["xclip", "-i"],
                         stdin=sin)
    p.communicate(text)
    if f:
        f.close()

############################################################

class DocItem(urwid.WidgetWrap):

    FIELDS = ['title',
              'authors',
              'journal',
              'year',
              'source',
              #'tags',
              #'file',
              #'summary',
              ]

    def __init__(self, doc, doc_ind, total_docs):
        self.doc = doc
        self.docid = self.doc.docid

        c1width = 10

        field_data = dict.fromkeys(self.FIELDS, '')

        field_data['tags'] = ' '.join(self.doc.get_tags())

        bibdata = self.doc.get_bibdata()
        if bibdata:
            for field, value in bibdata.iteritems():
                if 'title' == field:
                    field_data[field] = value
                elif 'authors' == field:
                    field_data[field] = ' and '.join(value[:4])
                    if len(value) > 4:
                        field_data[field] += ' et al.'
                elif 'year' == field:
                    field_data[field] = value

                if field_data['journal'] == '':
                    if 'journal' == field:
                        field_data['journal'] = value
                    elif 'container-title' == field:
                        field_data['journal'] = value
                    elif 'arxiv' == field:
                        field_data['journal'] = 'arXiv.org'
                    elif 'dcc' == field:
                        field_data['journal'] = 'LIGO DCC'

        urls = self.doc.get_urls()
        if urls:
            field_data['source'] = urls[0]

        summary = self.doc.get_data()
        if not summary:
            summary = 'NO FILE'
        field_data['summary'] = summary

        def gen_field_row(field, value):
            if field in ['journal', 'year', 'source']:
                color = 'journal'
            elif field in ['file']:
                color = 'field'
            else:
                color = field
            return urwid.Columns([
                ('fixed', c1width, urwid.Text(('field', field + ':'))),
                urwid.Text((color, value)),
                ])

        self.tag_field = urwid.Text(field_data['tags'])
        header = urwid.AttrMap(urwid.Columns([
            ('fixed', c1width, urwid.Text('id:%d' % (self.docid))),
            urwid.AttrMap(self.tag_field, 'tags'),
            urwid.Text('%s%% match (%s/%s)' % (doc.matchp, doc_ind, total_docs), align='right'),
            ]),
            'head')
        pile = [urwid.AttrMap(urwid.Divider(' '), '', ''), header] + \
               [gen_field_row(field, field_data[field]) for field in self.FIELDS]
        for f in self.doc.get_files():
            pile += [gen_field_row('file', os.path.basename(f))]
        w = urwid.AttrMap(urwid.AttrMap(urwid.Pile(pile), 'field'),
                          '',
                          {'head': 'head focus',
                           'field': 'field focus',
                           'tags': 'tags focus',
                           'title': 'title focus',
                           'authors': 'authors focus',
                           'journal': 'journal focus',
                           },
                          )

        self.__super.__init__(w)

############################################################

class DocWalker(urwid.ListWalker):
    def __init__(self, docs):
        self.docs = docs
        self.ndocs = len(docs)
        self.focus = 0
        self.items = {}

    def __getitem__(self, pos):
        if pos < 0:
            raise IndexError
        if pos not in self.items:
            self.items[pos] = DocItem(self.docs[pos], pos+1, self.ndocs)
        return self.items[pos]

    def set_focus(self, focus):
        if focus == -1:
            focus = self.ndocs - 1
        self.focus = focus
        self._modified()

    def next_position(self, pos):
        return pos + 1

    def prev_position(self, pos):
        return pos - 1
        
############################################################

class Search(urwid.Frame):

    palette = [
        ('head', 'dark blue, bold', ''),
        ('head focus', 'white, bold', 'dark blue'),
        ('field', 'light gray', ''),
        ('field focus', '', 'dark gray', '', '', 'g19'),
        ('tags', 'dark green', ''),
        ('tags focus', 'light green', 'dark blue'),
        ('title', 'yellow', ''),
        ('title focus', 'yellow', 'dark gray', '', 'yellow', 'g19'),
        ('authors', 'light cyan', ''),
        ('authors focus', 'light cyan', 'dark gray', '', 'light cyan', 'g19'),
        ('journal', 'dark magenta', '',),
        ('journal focus', 'dark magenta', 'dark gray', '', 'dark magenta', 'g19'),
        ]

    keys = collections.OrderedDict([
        ('n', "nextEntry"),
        ('down', "nextEntry"),
        ('p', "prevEntry"),
        ('up', "prevEntry"),
        ('<', "firstEntry"),
        ('>', "lastEntry"),
        ('=', "refresh"),
        ('l', "filterSearch"),
        ('enter', "viewFile"),
        ('u', "viewURL"),
        ('b', "viewBibtex"),
        ('+', "addTags"),
        ('-', "removeTags"),
        ('a', "archive"),
        ('meta i', "copyID"),
        ('meta k', "copyKey"),
        ('meta f', "copyPath"),
        ('meta u', "copyURL"),
        ('meta b', "copyBibtex"),
        ])

    def __init__(self, ui, query=None):
        self.ui = ui
        self.query = query
        super(Search, self).__init__(urwid.SolidFill())
        self.__set_search()

    def __set_search(self):
        count = self.ui.db.count(self.query)
        if count == 0:
            self.ui.set_status('No documents found.')
            docs = []
        else:
            docs = [doc for doc in self.ui.db.search(self.query)]
        if count == 1:
            cstring = "%d result" % (count)
        else:
            cstring = "%d results" % (count)

        htxt = [urwid.Text("Search: %s" % (self.query)),
                urwid.Text(cstring, align='right'),
                ]
        header = urwid.AttrMap(urwid.Columns(htxt), 'header')
        self.set_header(header)

        self.lenitems = count
        self.docwalker = DocWalker(docs)
        self.listbox = urwid.ListBox(self.docwalker)
        body = self.listbox
        self.set_body(body)

    def keypress(self, size, key):
        # reset the status on key presses
        self.ui.set_status()
        entry, pos = self.listbox.get_focus()
        # returns key if not handled, none otherwise
        if entry and not entry.keypress(size, key):
            return
        if key in self.keys:
            cmd = eval("self.%s" % (self.keys[key]))
            cmd(size, key)
        else:
            return key

    ##########

    def refresh(self, size, key):
        """refresh current search results"""
        entry, pos = self.listbox.get_focus()
        self.ui.db.reopen()
        self.__set_search()
        self.listbox.set_focus(pos)

    def filterSearch(self, size, key):
        """filter current search with additional terms"""
        prompt = 'filter search: '
        urwid.connect_signal(self.ui.prompt(prompt), 'done', self._filterSearch_done)

    def _filterSearch_done(self, newquery):
        self.ui.view.set_focus('body')
        urwid.disconnect_signal(self.ui, self.ui.prompt, 'done', self._filterSearch_done)
        if not newquery:
            self.ui.set_status()
            return
        self.ui.newbuffer(['search', self.query, newquery])

    def nextEntry(self, size, key):
        """next entry"""
        entry, pos = self.listbox.get_focus()
        if not entry: return
        if pos + 1 >= self.lenitems: return
        self.listbox.set_focus(pos + 1)

    def prevEntry(self, size, key):
        """previous entry"""
        entry, pos = self.listbox.get_focus()
        if not entry: return
        if pos == 0: return
        self.listbox.set_focus(pos - 1)

    def lastEntry(self, size, key):
        """last entry"""
        self.listbox.set_focus(-1)

    def firstEntry(self, size, key):
        """first entry"""
        self.listbox.set_focus(0)

    def viewFile(self, size, key):
        """open document file"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        paths = entry.doc.get_fullpaths()
        if not paths:
            self.ui.set_status('No file for document id:%d.' % entry.docid)
            return
        for path in paths:
            if not os.path.exists(path):
                self.ui.set_status('ERROR: id:%d: file not found.' % entry.docid)
            self.ui.set_status('opening file: %s...' % path)
            xdg_open(path)

    def viewURL(self, size, key):
        """open document URL in browser"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        urls = entry.doc.get_urls()
        if not urls:
            self.ui.set_status('ERROR: id:%d: no URLs found.' % entry.docid)
            return
        # FIXME: open all instead of just first?
        url = urls[0]
        self.ui.set_status('opening url: %s...' % url)
        xdg_open(url)

    def viewBibtex(self, size, key):
        """view document bibtex"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        self.ui.newbuffer(['bibview', 'id:' + str(entry.docid)])

    def copyID(self, size, key):
        """copy document ID to clipboard"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        docid = "id:%d" % entry.docid
        xclip(docid)
        self.ui.set_status('yanked docid: %s' % docid)

    def copyKey(self, size, key):
        """copy document bibtex key to clipboard"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        bibkey = entry.doc.get_key()
        xclip(bibkey)
        self.ui.set_status('yanked bibkey: %s' % bibkey)

    def copyPath(self, size, key):
        """copy document file path to clipboard"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        path = entry.doc.get_fullpaths()[0]
        if not path:
            self.ui.set_status('ERROR: id:%d: file path not found.' % entry.docid)
            return
        xclip(path)
        self.ui.set_status('yanked path: %s' % path)

    def copyURL(self, size, key):
        """copy document URL to clipboard"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        urls = entry.doc.get_urls()
        if not urls:
            self.ui.set_status('ERROR: id:%d: URL not found.' % entry.docid)
            return
        # FIXME: copy all instead of just first?
        url = urls[0]
        xclip(url)
        self.ui.set_status('yanked url: %s' % url)

    def copyBibtex(self, size, key):
        """copy document bibtex to clipboard"""
        entry = self.listbox.get_focus()[0]
        if not entry: return
        bibtex = entry.doc.get_bibpath()
        if not bibtex:
            self.ui.set_status('ERROR: id:%d: bibtex not found.' % entry.docid)
            return
        xclip(bibtex, isfile=True)
        self.ui.set_status('yanked bibtex: %s' % bibtex)

    def addTags(self, size, key):
        """add tags to document (space separated)"""
        self.promptTag('+')

    def removeTags(self, size, key):
        """remove tags from document (space separated)"""
        self.promptTag('-')

    def promptTag(self, sign):
        entry = self.listbox.get_focus()[0]
        if not entry: return
        if sign is '+':
            # FIXME: autocomplete to existing tags
            prompt = 'add tags: '
        elif sign is '-':
            # FIXME: autocomplete to doc tags only
            prompt = 'remove tags: '
        urwid.connect_signal(self.ui.prompt(prompt), 'done', self._promptTag_done, sign)

    def _promptTag_done(self, tag_string, sign):
        self.ui.view.set_focus('body')
        urwid.disconnect_signal(self, self.ui.prompt, 'done', self._promptTag_done)
        if not tag_string:
            self.ui.set_status('No tags set.')
            return
        entry = self.listbox.get_focus()[0]
        try:
            with initdb(writable=True) as db:
                doc = db[entry.docid]
                tags = tag_string.split()
                if sign is '+':
                    doc.add_tags(tags)
                    msg = "Added tags: %s" % (tag_string)
                elif sign is '-':
                    doc.remove_tags(tags)
                    msg = "Removed tags: %s" % (tag_string)
                doc.sync()
            tags = doc.get_tags()
            entry.tag_field.set_text(' '.join(tags))
        except DatabaseLockError as e:
            msg = e.msg
        self.ui.db.reopen()
        self.ui.set_status(msg)

    def archive(self, size, key):
        """archive document (remove 'new' tag) and advance"""
        self._promptTag_done('new', '-')
        self.nextEntry()
