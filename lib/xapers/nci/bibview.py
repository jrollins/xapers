import urwid

from ..cli import initdb

############################################################

class Bibview(urwid.Frame):

    def __init__(self, ui, query):
        self.ui = ui

        htxt = [urwid.Text("Bibtex: " + query)]
        header = urwid.AttrMap(urwid.Columns(htxt), 'header')

        string = ''

        with initdb() as db:
            if db.count(query) == 0:
                self.ui.set_status('No documents found.')
            else:
                for doc in db.search(query, limit=20):
                    bibtex = doc.get_bibtex()
                    if bibtex:
                        string = string + bibtex + '\n'

        body = urwid.Filler(urwid.Text(string))

        super(Bibview, self).__init__(body, header=header)
