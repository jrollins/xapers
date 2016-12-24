import urwid

############################################################

class Help(urwid.Frame):

    def __init__(self, ui, target=None):
        self.ui = ui

        if target:
            tname = target.__class__.__name__
            htxt = [urwid.Text("Help: " + tname)]
        else:
            htxt = [urwid.Text("Help")]
        header = urwid.AttrMap(urwid.Columns(htxt), 'header')

        pile = []

        # write command help row
        def crow(c, cmd, key):
            f = getattr(c, cmd)
            hstring = str(getattr(f, '__doc__'))
            return urwid.Columns([('fixed', 10, urwid.Text(key)),
                                  urwid.Text(hstring),
                                  ])

        if target and hasattr(target, 'keys'):
            pile.append(urwid.Text('%s commands:' % (tname)))
            pile.append(urwid.Text(''))
            for key, cmd in target.keys.iteritems():
                pile.append(crow(target, cmd, key))
            pile.append(urwid.Text(''))
            pile.append(urwid.Text(''))

        pile.append(urwid.Text('Global commands:'))
        pile.append(urwid.Text(''))
        for key, cmd in self.ui.keys.iteritems():
            pile.append(crow(ui, cmd, key))

        body = urwid.Filler(urwid.Pile(pile))

        super(Help, self).__init__(body, header=header)

    def keypress(self, size, key):
        if key != '?':
            return key
