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
import urwid
import logging
import collections

from ..cli import initdb
from . import search
from . import bibview
from . import help

############################################################

PALETTE = [
    ('header', 'light gray', 'dark blue'),
    ('header_args', 'white', 'dark blue'),
    ('footer', 'light gray', 'dark blue'),
    ('prompt', 'black', 'dark green'),
    ]

class UI():

    keys = collections.OrderedDict([
        ('s', "promptSearch"),
        ('q', "killBuffer"),
        ('Q', "quit"),
        ('?', "help"),
        ])

    default_status_string = "s: search, q: close buffer, Q: quit, ?: help and additional commands"
    buffers = []
    search_history = []
    tag_history = []

    def __init__(self, cmd=None):
        self.db = initdb()

        # FIXME: set this properly
        self.palette = list(set(PALETTE) | set(search.PALETTE))

        self.view = urwid.Frame(urwid.SolidFill())

        self.set_status()

        self.mainloop = urwid.MainLoop(
            self.view,
            self.palette,
            unhandled_input=self.keypress,
            handle_mouse=False,
            )
        self.mainloop.screen.set_terminal_properties(colors=88)

        if not cmd:
            cmd = ['search', 'tag:new']
        self.newbuffer(cmd)

        self.mainloop.run()

    ##########


    def set_status(self, text=None):
        if text:
            T = [urwid.Text(text)]
        else:
            T = [urwid.Text('Xapers [{}]'.format(len(self.buffers))),
                 urwid.Text(self.default_status_string, align='right'),
                 ]
        self.view.set_footer(urwid.AttrMap(urwid.Columns(T), 'footer'))

    def newbuffer(self, cmd):
        if not cmd:
            cmd = ['search', '*']

        if cmd[0] == 'search':
            query = ' '.join(cmd[1:])
            buf = search.Search(self, query)
        elif cmd[0] == 'bibview':
            query = ' '.join(cmd[1:])
            buf = bibview.Bibview(self, query)
        elif cmd[0] == 'help':
            target = None
            if len(cmd) > 1:
                target = cmd[1]
            if isinstance(target, str):
                target = None
            buf = help.Help(self, target)
        else:
            buf = help.Help(self)
            self.set_status("Unknown command '%s'." % (cmd[0]))
        self.buffers.append(buf)
        self.view.set_body(buf)
        self.set_status()

    def killBuffer(self):
        """close current buffer"""
        if len(self.buffers) == 1:
            return
        self.buffers.pop()
        buf = self.buffers[-1]
        self.view.set_body(buf)
        self.set_status()
        self.mainloop.draw_screen()

    def prompt(self, final, *args, **kwargs):
        """user prompt

        final is a (func, args) tuple to be executed upon complection:
        func(text, *args)

        further args and kwargs are passed to PromptEdit

        """
        pe = PromptEdit(*args, **kwargs)
        urwid.connect_signal(pe, 'done', self.prompt_done, final)
        self.view.set_footer(urwid.AttrMap(pe, 'prompt'))
        self.view.set_focus('footer')

    def prompt_done(self, text, final):
        self.view.set_focus('body')
        urwid.disconnect_signal(self, self.prompt, 'done', self.prompt_done)
        (func, args) = final
        func(text, *args)

    ##########

    def promptSearch(self):
        """search database"""
        prompt = 'search: '
        self.prompt((self.promptSearch_done, []),
                    prompt, history=self.search_history)

    def promptSearch_done(self, query):
        if not query:
            self.set_status()
            return
        self.newbuffer(['search', query])

    def quit(self):
        """quit"""
        sys.exit()

    def help(self):
        """help"""
        self.newbuffer(['help', self.buffers[-1]])

    def keypress(self, key):
        if key in self.keys:
            cmd = "self.%s()" % (self.keys[key])
            eval(cmd)

############################################################

class PromptEdit(urwid.Edit):
    __metaclass__ = urwid.signals.MetaSignals
    signals = ['done']

    def __init__(self, prompt, initial=None, completions=None, history=None):
        super(PromptEdit, self).__init__(caption=prompt)
        if initial:
            self.insert_text(initial)
        self.completions = completions
        self.completion_data = {}
        self.history = history
        self.history_pos = -1
        self.last_text = ''

    def keypress(self, size, key):
        if self.last_text and self.edit_text != self.last_text:
            self.completion_data.clear()
            self.history_pos = -1

        if key == 'enter':
            urwid.emit_signal(self, 'done', self.get_edit_text())
            return
        elif key in ['esc', 'ctrl g']:
            urwid.emit_signal(self, 'done', None)
            return

        # navigation
        elif key == 'ctrl a':
            # move to beginning
            key = 'home'
        elif key == 'ctrl e':
            # move to end
            key = 'end'
        elif key == 'ctrl b':
            # back character
            self.set_edit_pos(self.edit_pos-1)
        elif key == 'ctrl f':
            # forward character
            self.set_edit_pos(self.edit_pos+1)
        elif key == 'meta b':
            # back word
            text = self.edit_text
            pos = self.edit_pos - 1
            inword = False
            while True:
                try:
                    text[pos]
                except IndexError:
                    break
                if text[pos] != ' ' and not inword:
                    inword = True
                    continue
                if inword:
                    if text[pos] == ' ':
                        break
                pos -= 1
            self.set_edit_pos(pos+1)
        elif key == 'meta f':
            # forward word
            text = self.edit_text
            pos = self.edit_pos
            inword = False
            while True:
                try:
                    text[pos]
                except IndexError:
                    break
                if text[pos] != ' ' and not inword:
                    inword = True
                    continue
                if inword:
                    if text[pos] == ' ':
                        break
                pos += 1
            self.set_edit_pos(pos+1)

        # deletion
        elif key == 'ctrl d':
            # delete character
            text = self.edit_text
            pos = self.edit_pos
            ntext = text[:pos] + text[pos+1:]
            self.set_edit_text(ntext)
        elif key == 'ctrl k':
            # delete to end
            self.set_edit_text(self.edit_text[:self.edit_pos])

        # history
        elif key in ['up', 'ctrl p']:
            if self.history:
                if self.history_pos == -1:
                    self.history_full = self.history + [self.edit_text]
                try:
                    self.history_pos -= 1
                    self.set_edit_text(self.history_full[self.history_pos])
                    self.set_edit_pos(len(self.edit_text))
                except IndexError:
                    self.history_pos += 1
        elif key in ['down', 'ctrl n']:
            if self.history:
                if self.history_pos != -1:
                    self.history_pos += 1
                    self.set_edit_text(self.history_full[self.history_pos])
                    self.set_edit_pos(len(self.edit_text))

        # tab completion
        elif key == 'tab' and self.completions:
            # tab complete on individual words

            # retrieve current text and position
            text = self.edit_text
            pos = self.edit_pos

            # find the completion prefix
            tpos = pos - 1
            while True:
                try:
                    if text[tpos] == ' ':
                        tpos += 1
                        break
                except IndexError:
                    break
                tpos -= 1
            prefix = text[tpos:pos]
            # FIXME: this prefix stripping should not be done here
            prefix = prefix.lstrip('+-')
            # find the end of the word
            tpos += 1
            while True:
                try:
                    if text[tpos] == ' ':
                        break
                except IndexError:
                    break
                tpos += 1

            # record/clear completion data
            if self.completion_data:
                # clear the data if the prefix is new
                if prefix != self.completion_data['prefix']:
                    self.completion_data.clear()
                # otherwise rotate the queue
                else:
                    self.completion_data['q'].rotate(-1)
            else:
                self.completion_data['prefix'] = prefix
                # harvest completions
                q = collections.deque()
                for c in self.completions:
                    if c.startswith(prefix):
                        q.append(c)
                self.completion_data['q'] = q

            logging.debug(self.completion_data)

            # insert completion at point
            if self.completion_data and self.completion_data['q']:
                c = self.completion_data['q'][0][len(prefix):]
                ntext = text[:pos] + c + text[tpos:]
                self.set_edit_text(ntext)
                self.set_edit_pos(pos)

        # record the last text
        self.last_text = self.edit_text
        return super(PromptEdit, self).keypress(size, key)
