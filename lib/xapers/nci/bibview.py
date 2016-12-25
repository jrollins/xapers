import urwid

############################################################

class Bibview(urwid.Frame):

    def __init__(self, ui, query):
        self.ui = ui

        htxt = [urwid.Text("Bibtex: " + query)]
        header = urwid.AttrMap(urwid.Columns(htxt), 'header')

        string = ''

        db = self.ui.db
        if db.count(query) == 0:
            self.ui.set_status('No documents found.')
        else:
            for doc in db.search(query, limit=20):
                bibtex = doc.get_bibtex()
                if bibtex:
                    string = string + bibtex + '\n'

        content = [urwid.Text(s) for s in string.split('\n')]
        body = urwid.ListBox(urwid.SimpleListWalker(content))

        super(Bibview, self).__init__(body, header=header)

    def help(self):
        return []

    def keypress(self, size, key):
        if key == ' ':
            return self.get_body().keypress(size, 'page down')
        return super(Bibview, self).keypress(size, key)
