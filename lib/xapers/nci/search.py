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

Copyright 2012-2017
Jameson Rollins <jrollins@finestructure.net>
"""

import os
import urwid
import subprocess
import collections

from ..cli import initdb
from ..database import DatabaseLockError

PALETTE = [
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
    ('bibkey', 'dark magenta', '',),
    ('bibkey focus', 'dark magenta', 'dark gray', '', 'dark magenta', 'g19'),
    ]

############################################################

def xdg_open(path):
    """open document file"""
    with open(os.devnull) as devnull:
        subprocess.Popen(['xdg-open', path],
                         stdin=devnull,
                         stdout=devnull,
                         stderr=devnull)

def xclip(text):
    """Copy text into X clipboard."""
    p = subprocess.Popen(["xclip", "-i"],
                         stdin=subprocess.PIPE)
    p.communicate(text.encode('utf-8'))

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

    keys = collections.OrderedDict([
        ('enter', "viewFile"),
        ('u', "viewURL"),
        ('b', "viewBibtex"),
        ('+', "addTags"),
        ('-', "removeTags"),
        ('meta i', "copyID"),
        ('meta k', "copyKey"),
        ('meta f', "copyPath"),
        ('meta u', "copyURL"),
        ('meta b', "copyBibtex"),
        ])

    def __init__(self, ui, doc, doc_ind, total_docs):
        self.ui = ui
        self.doc = doc
        self.docid = 'id:{}'.format(doc.docid)

        c1width = 10

        field_data = dict.fromkeys(self.FIELDS, '')

        field_data['tags'] = ' '.join(doc.get_tags())

        bibdata = doc.get_bibdata()
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

                # FIXME: this translation should not be done here
                if field_data['journal'] == '':
                    if 'journal' == field:
                        field_data['journal'] = value
                    elif 'container-title' == field:
                        field_data['journal'] = value
                    elif 'arxiv' == field:
                        field_data['journal'] = 'arXiv.org'
                    elif 'dcc' == field:
                        field_data['journal'] = 'LIGO DCC'

        urls = doc.get_urls()
        if urls:
            field_data['source'] = urls[0]

        summary = doc.get_data()
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
            ('fixed', c1width, urwid.Text('%s' % (self.docid))),
            urwid.AttrMap(self.tag_field, 'tags'),
            urwid.Text('%s%% match (%s/%s)' % (doc.matchp, doc_ind, total_docs), align='right'),
            ]),
            'head')
        pile = [urwid.AttrMap(urwid.Divider(' '), '', ''), header] + \
               [gen_field_row(field, field_data[field]) for field in self.FIELDS]
        for f in doc.get_files():
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

    def keypress(self, size, key):
        if key in self.keys:
            cmd = eval("self.{}".format(self.keys[key]))
            cmd()
        else:
            return key

    ####################

    def viewFile(self):
        """open document file"""
        paths = self.doc.get_fullpaths()
        if not paths:
            self.ui.set_status('No file for document {}.'.format(self.docid))
            return
        for path in paths:
            if not os.path.exists(path):
                self.ui.error('{}: file not found.'.format(self.docid))
            else:
                self.ui.set_status('opening file: {}...'.format(path))
            xdg_open(path)

    def viewURL(self):
        """open document URL in browser"""
        urls = self.doc.get_urls()
        if not urls:
            self.ui.set_status('No URLs for document {}.'.format(self.docid))
            return
        # FIXME: open all instead of just first?
        url = urls[0]
        self.ui.set_status('opening url: {}...'.format(url))
        xdg_open(url)

    def viewBibtex(self):
        """view document bibtex"""
        self.ui.newbuffer(['bibview', self.docid])

    def copyID(self):
        """copy document ID to clipboard"""
        xclip(self.docid)
        self.ui.set_status('yanked docid: {}'.format(self.docid))

    def copyKey(self):
        """copy document bibtex key to clipboard"""
        bibkey = self.doc.get_key()
        xclip(bibkey)
        self.ui.set_status('yanked bibkey: {}'.format(bibkey))

    def copyPath(self):
        """copy document file path to clipboard"""
        path = self.doc.get_fullpaths()[0]
        if not path:
            self.ui.set_status('No files for document {}.'.format(self.docid))
            return
        xclip(path)
        self.ui.set_status('yanked path: {}'.format(path))

    def copyURL(self):
        """copy document URL to clipboard"""
        urls = self.doc.get_urls()
        if not urls:
            self.ui.set_status('No URLs for document {}.'.format(self.docid))
            return
        # FIXME: copy all instead of just first?
        url = urls[0]
        xclip(url)
        self.ui.set_status('yanked url: {}'.format(url))

    def copyBibtex(self):
        """copy document bibtex to clipboard"""
        bibtex = self.doc.get_bibtex()
        if not bibtex:
            self.ui.set_status('No bibtex for document {}.'.format(self.docid))
            return
        xclip(bibtex)
        self.ui.set_status('yanked bibtex: %s...' % bibtex.split('\n')[0])

    def addTags(self):
        """add tags to document (space separated)"""
        self.promptTag('+')

    def removeTags(self):
        """remove tags from document (space separated)"""
        self.promptTag('-')

    def promptTag(self, sign):
        prompt = "apply tags (space separated): "
        initial = sign
        if sign is '+':
            completions = self.ui.db.get_tags()
        elif sign is '-':
            completions = self.doc.get_tags()
        self.ui.prompt((self.applyTags, []),
                       prompt, initial=initial, completions=completions)

    def applyTags(self, tag_string):
        if not tag_string:
            self.ui.set_status("No tags set.")
            return
        try:
            with initdb(writable=True) as db:
                doc = db[self.doc.docid]
                for tag in tag_string.split():
                    if tag[0] == '+':
                        if tag[1:]:
                            doc.add_tags([tag[1:]])
                    elif tag[0] == '-':
                        doc.remove_tags([tag[1:]])
                    else:
                        doc.add_tags([tag])
                doc.sync()
                msg = "applied tags: {}".format(tag_string)
            tags = doc.get_tags()
            self.tag_field.set_text(' '.join(tags))
        except DatabaseLockError as e:
            msg = e.msg
        self.ui.db.reopen()
        self.ui.set_status(msg)

############################################################

class DocWalker(urwid.ListWalker):
    def __init__(self, ui, docs):
        self.ui = ui
        self.docs = docs
        self.ndocs = len(docs)
        self.focus = 0
        self.items = {}

    def __getitem__(self, pos):
        if pos < 0:
            raise IndexError
        if pos not in self.items:
            self.items[pos] = DocItem(self.ui, self.docs[pos], pos+1, self.ndocs)
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

    keys = collections.OrderedDict([
        ('n', "nextEntry"),
        ('down', "nextEntry"),
        ('p', "prevEntry"),
        ('up', "prevEntry"),
        ('N', "pageDown"),
        ('page down', "pageDown"),
        ('P', "pageUp"),
        ('page up', "pageUp"),
        ('<', "firstEntry"),
        ('>', "lastEntry"),
        ('a', "archive"),
        ('=', "refresh"),
        ('l', "filterSearch"),
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
        self.docwalker = DocWalker(self.ui, docs)
        self.listbox = urwid.ListBox(self.docwalker)
        body = self.listbox
        self.set_body(body)

    def keypress(self, size, key):
        # reset the status on key presses
        self.ui.set_status()
        entry, pos = self.listbox.get_focus()
        # key used if keypress returns None
        if entry and not entry.keypress(size, key):
            return
        # check if we can use key
        elif key in self.keys:
            cmd = eval("self.%s" % (self.keys[key]))
            cmd(size, key)
        # else we didn't use key so return
        else:
            return key

    def help(self):
        lines = []
        for o in [DocItem, self]:
            for k, cmd in o.keys.items():
                h = str(getattr(getattr(o, cmd), '__doc__'))
                lines.append((k, h))
        return lines

    ##########

    def refresh(self, size, key):
        """refresh current search results"""
        entry, pos = self.listbox.get_focus()
        self.ui.db.reopen()
        self.__set_search()
        self.listbox.set_focus(pos)

    def filterSearch(self, size, key):
        """filter current search with additional terms"""
        prompt = 'filter search: {} '.format(self.query)
        self.ui.prompt((self.filterSearch_done, []),
                       prompt)

    def filterSearch_done(self, newquery):
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

    def pageDown(self, size, key):
        """page down"""
        self.listbox.keypress(size, 'page down')
        self.listbox.set_focus_valign('bottom')

    def pageUp(self, size, key):
        """page up"""
        self.listbox.keypress(size, 'page up')
        self.listbox.set_focus_valign('top')

    def lastEntry(self, size, key):
        """last entry"""
        self.listbox.set_focus(-1)

    def firstEntry(self, size, key):
        """first entry"""
        self.listbox.set_focus(0)

    def archive(self, size, key):
        """archive document (remove 'new' tag) and advance"""
        entry = self.listbox.get_focus()[0]
        if not entry:
            return
        entry.applyTags('-new')
        self.nextEntry(None, None)
