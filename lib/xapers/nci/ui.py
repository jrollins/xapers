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
import sys
import urwid
import collections

from ..cli import initdb
from . import search
from . import bibview
from . import help

############################################################

class UI():

    palette = [
        ('header', 'white', 'dark blue'),
        ('footer', 'white', 'dark blue'),
        ('prompt', 'black', 'dark green'),
        ]

    keys = collections.OrderedDict([
        ('s', "promptSearch"),
        ('q', "killBuffer"),
        ('Q', "quit"),
        ('?', "help"),
        ])

    default_status_string = "s: search, q: close buffer, Q: quit, ?: help and additional commands"
    buffers = []
    search_history = []

    def __init__(self, cmd=None):
        self.db = initdb()

        # FIXME: set this properly
        self.palette = list(set(self.palette) | set(Search.palette))

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

    def merge_palette(self, buffer):
        if hasattr(buffer, 'palette'):
            self.palette = list(set(self.palette) | set(buffer.palette))

    def set_status(self, text=None):
        if not text:
            text = self.default_status_string
        self.view.set_footer(urwid.AttrMap(urwid.Text(text), 'footer'))

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
        if self.search_history and query == self.search_history[-1]:
            pass
        else:
            self.search_history.append(query)
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
        elif key == 'ctrl a':
            key = 'home'
        elif key == 'ctrl e':
            key = 'end'
        elif key == 'ctrl k':
            self._delete_highlighted()
            self.set_edit_text(self.edit_text[:self.edit_pos])
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
        elif key == 'tab' and self.completions:
            before = self.edit_text[:self.edit_pos]
            if self.completion_data:
                if before != self.completion_data['before']:
                    self.completion_data.clear()
            if self.completion_data:
                self.completion_data['q'].rotate(-1)
            else:
                self.completion_data['before'] = before
                # harvest completions
                q = collections.deque()
                for c in self.completions:
                    if c.startswith(before):
                        q.append(c)
                self.completion_data['q'] = q
            # insert completions
            if self.completion_data and self.completion_data['q']:
                pos = self.edit_pos
                self.set_edit_text(self.completion_data['q'][0])
                self.set_edit_pos(pos)
        self.last_text = self.edit_text
        return super(PromptEdit, self).keypress(size, key)
