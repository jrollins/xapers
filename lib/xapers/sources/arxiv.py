import urllib.request, urllib.parse, urllib.error
from html.parser import HTMLParser
from xapers.bibtex import data2bib

description = "Open access e-print service"

url = 'http://arxiv.org/'

url_format = 'http://arxiv.org/abs/%s'

url_regex = 'http://arxiv.org/(?:abs|pdf|format)/([^/]*)'

# http://arxiv.org/help/arxiv_identifier
scan_regex = 'arXiv:([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?'

# html parser override to override handler methods
class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.lefthead = False
        self.title = None
        self.author = []
        self.year = None
        self.sid = None

    def handle_starttag(self, tag, attrs):
        title = False
        author = False
        date = False
        sid = False

        if self.lefthead:
            return

        if tag != 'meta':
            return

        for attr in attrs:
            if attr[0] == 'name':
                if attr[1] == 'citation_title':
                    title = True
                if attr[1] == 'citation_author':
                    author = True
                if attr[1] == 'citation_date':
                    date = True
                if attr[1] == 'citation_arxiv_id':
                    sid = True

            if attr[0] == 'content':
                if title:
                    self.title = attr[1]
                if author:
                    self.author.append(attr[1])
                if date:
                    self.year = attr[1].split('/')[0]
                if sid:
                    self.sid = attr[1]

    def handle_endtag(self, tag):
        if tag == 'head':
            self.lefthead = True

def fetch_bibtex(id):
    url = url_format % id

    f = urllib.request.urlopen(url)
    html = f.read()
    f.close()

    parser = MyHTMLParser()
    parser.feed(html)

    data = {
        'arxiv':   id,
        'title':   parser.title,
        'authors': parser.author,
        'year':    parser.year,
        'eprint':  id,
        'url':     url_format % id,
        }

    return data2bib(data, 'arxiv:%s' % id)

def fetch_file(id):
    url = 'http://arxiv.org/pdf/%s' % id
    f = urllib.request.urlopen(url)
    data = f.read()
    f.close()
    name = '%s.pdf' % id
    return name, data
