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

        # format command help line
        def fch(k, h):
            return urwid.Columns([('fixed', 10, urwid.Text(k)),
                                  urwid.Text(h),
                                  ])

        if target:
            hl = target.help()
            if hl:
                pile.append(urwid.Text('%s commands:' % (tname)))
                pile.append(urwid.Text(''))
                for k,h in hl:
                    pile.append(fch(k,h))
                pile.append(urwid.Text(''))
                pile.append(urwid.Text(''))

        pile.append(urwid.Text('Global commands:'))
        pile.append(urwid.Text(''))
        for k, cmd in self.ui.keys.iteritems():
            f = getattr(ui, cmd)
            h = str(getattr(f, '__doc__'))
            pile.append(fch(k,h))

        body = urwid.ListBox(urwid.SimpleListWalker(pile))

        super(Help, self).__init__(body, header=header)

    def keypress(self, size, key):
        # ignore help in help
        if key == '?':
            return
        if key == ' ':
            return self.get_body().keypress(size, 'page down')
        return super(Help, self).keypress(size, key)
