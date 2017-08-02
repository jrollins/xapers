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
import sets
import shutil
import readline

from . import database
from .documents import Document
from .source import Sources, SourceError
from .parser import ParseError
from .bibtex import Bibtex, BibtexError

############################################################

def initdb(writable=False, create=False, force=False):
    xroot = os.getenv('XAPERS_ROOT',
                      os.path.expanduser(os.path.join('~','.xapers','docs')))
    try:
        return database.Database(xroot, writable=writable, create=create, force=force)
    except database.DatabaseUninitializedError as e:
        print(e, file=sys.stderr)
        print("Import a document to initialize.", file=sys.stderr)
        sys.exit(1)
    except database.DatabaseInitializationError as e:
        print(e, file=sys.stderr)
        print("Either clear the directory and add new files, or use 'retore' to restore from existing data.", file=sys.stderr)
        sys.exit(1)
    except database.DatabaseError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

############################################################

# readline completion class
class Completer:
    def __init__(self, words):
        self.words = words
    def terms(self, prefix, index):
        matching_words = [
            w for w in self.words if w.startswith(prefix)
            ]
        try:
            return matching_words[index]
        except IndexError:
            return None

def prompt_for_file(infile):
    if infile:
        print('file: %s' % infile, file=sys.stderr)
    else:
        readline.set_startup_hook()
        readline.parse_and_bind('')
        readline.set_completer()
        infile = input('file: ')
        if infile == '':
            infile = None
    return infile

def prompt_for_source(db, sources):
    if sources:
        readline.set_startup_hook(lambda: readline.insert_text(sources[0]))
    elif db:
        sources = list(db.term_iter('source'))
    readline.parse_and_bind("tab: complete")
    completer = Completer(sources)
    readline.set_completer(completer.terms)
    readline.set_completer_delims(' ')
    source = input('source: ')
    if source == '':
        source = None
    return source

def prompt_for_tags(db, tags):
    # always prompt for tags, and append to initial
    if tags:
        print('initial tags: %s' % ' '.join(tags), file=sys.stderr)
    else:
        tags = []
    if db:
        itags = list(db.term_iter('tag'))
    else:
        itags = None
    readline.set_startup_hook()
    readline.parse_and_bind("tab: complete")
    completer = Completer(itags)
    readline.set_completer(completer.terms)
    readline.set_completer_delims(' ')
    while True:
        tag = input('tag: ')
        if tag and tag != '':
            tags.append(tag.strip())
        else:
            break
    return tags

############################################################

def print_doc_summary(doc):
    docid = doc.docid
    title = doc.get_title()
    if not title:
        title = ''
    tags = doc.get_tags()
    sources = doc.get_sids()
    key = doc.get_key()
    if not key:
        key = ''

    print("id:%d [%s] {%s} (%s) \"%s\"" % (
        docid,
        ' '.join(sources),
        key,
        ' '.join(tags),
        title,
    ))

############################################################

def add(db, query_string, infile=None, sid=None, tags=None, prompt=False):

    doc = None
    bibtex = None

    sources = Sources()
    doc_sid = sid
    source = None
    file_data = None

    if infile and infile is not True:
        infile = os.path.expanduser(infile)

    ##################################
    # if query provided, find single doc to update

    if query_string:
        if db.count(query_string) != 1:
            print("Search '%s' did not match a single document." % query_string, file=sys.stderr)
            print("Aborting.", file=sys.stderr)
            sys.exit(1)

        for doc in db.search(query_string):
            break

    ##################################
    # do fancy option prompting

    if prompt:
        doc_sids = []
        if doc_sid:
            doc_sids = [doc_sid]
        # scan the file for source info
        if infile is not True:
            infile = prompt_for_file(infile)

            print("Scanning document for source identifiers...", file=sys.stderr)
            try:
                ss = sources.scan_file(infile)
            except ParseError as e:
                print("\n", file=sys.stderr)
                print("Parse error: %s" % e, file=sys.stderr)
                sys.exit(1)
            if len(ss) == 0:
                print("0 source ids found.", file=sys.stderr)
            else:
                if len(ss) == 1:
                    print("1 source id found:", file=sys.stderr)
                else:
                    print("%d source ids found:" % (len(ss)), file=sys.stderr)
                for sid in ss:
                    print("  %s" % (sid), file=sys.stderr)
                doc_sids += [s.sid for s in ss]
        doc_sid = prompt_for_source(db, doc_sids)
        tags = prompt_for_tags(db, tags)

    if not query_string and not infile and not doc_sid:
        print("Must specify file or source to import, or query to update existing document.", file=sys.stderr)
        sys.exit(1)

    ##################################
    # process source and get bibtex

    # check if source is a file, in which case interpret it as bibtex
    if doc_sid and os.path.exists(doc_sid):
        bibtex = doc_sid

    elif doc_sid:
        # get source object for sid string
        try:
            source = sources.match_source(doc_sid)
        except SourceError as e:
            print(e, file=sys.stderr)
            sys.exit(1)

        # check that the source doesn't match an existing doc
        sdoc = db.doc_for_source(source.sid)
        if sdoc:
            if doc and sdoc != doc:
                print("A different document already exists for source '%s'." % (doc_sid), file=sys.stderr)
                print("Aborting.", file=sys.stderr)
                sys.exit(1)
            print("Source '%s' found in database.  Updating existing document..." % (doc_sid), file=sys.stderr)
            doc = sdoc

        try:
            print("Retrieving bibtex...", end=' ', file=sys.stderr)
            bibtex = source.fetch_bibtex()
            print("done.", file=sys.stderr)
        except SourceError as e:
            print("\n", file=sys.stderr)
            print("Could not retrieve bibtex: %s" % e, file=sys.stderr)
            sys.exit(1)

        if infile is True:
            try:
                print("Retrieving file...", end=' ', file=sys.stderr)
                file_name, file_data = source.fetch_file()
                print("done.", file=sys.stderr)
            except SourceError as e:
                print("\n", file=sys.stderr)
                print("Could not retrieve file: %s" % e, file=sys.stderr)
                sys.exit(1)

    elif infile is True:
        print("Must specify source with retrieve file option.", file=sys.stderr)
        sys.exit(1)

    if infile and not file_data:
        with open(infile, 'br') as f:
            file_data = f.read()
        file_name = os.path.basename(infile)

    ##################################

    # if we still don't have a doc, create a new one
    if not doc:
        doc = Document(db)

    ##################################
    # add stuff to the doc

    if bibtex:
        try:
            print("Adding bibtex...", end=' ', file=sys.stderr)
            doc.add_bibtex(bibtex)
            print("done.", file=sys.stderr)
        except BibtexError as e:
            print("\n", file=sys.stderr)
            print(e, file=sys.stderr)
            print("Bibtex must be a plain text file with a single bibtex entry.", file=sys.stderr)
            sys.exit(1)
        except:
            print("\n", file=sys.stderr)
            raise

    # add source sid if it hasn't been added yet
    if source and not doc.get_sids():
        doc.add_sid(source.sid)

    if infile:
        try:
            print("Adding file...", end=' ', file=sys.stderr)
            doc.add_file_data(file_name, file_data)
            print("done.", file=sys.stderr)
        except ParseError as e:
            print("\n", file=sys.stderr)
            print("Parse error: %s" % e, file=sys.stderr)
            sys.exit(1)
        except:
            print("\n", file=sys.stderr)
            raise

    if tags:
        try:
            print("Adding tags...", end=' ', file=sys.stderr)
            doc.add_tags(tags)
            print("done.", file=sys.stderr)
        except:
            print("\n", file=sys.stderr)
            raise

    ##################################
    # sync the doc to db and disk

    try:
        print("Syncing document...", end=' ', file=sys.stderr)
        doc.sync()
        print("done.\n", end=' ', file=sys.stderr)
    except:
        print("\n", file=sys.stderr)
        raise

    print_doc_summary(doc)
    return doc.docid

############################################

def importbib(db, bibfile, tags=[], overwrite=False):
    errors = []

    sources = Sources()

    for entry in sorted(Bibtex(bibfile), key=lambda entry: entry.key):
        print(entry.key, file=sys.stderr)

        try:
            docs = []

            # check for doc with this bibkey
            bdoc = db.doc_for_bib(entry.key)
            if bdoc:
                docs.append(bdoc)

            # check for known sids
            for source in sources.scan_bibentry(entry):
                sdoc = db.doc_for_source(source.sid)
                # FIXME: why can't we match docs in list?
                if sdoc and sdoc.docid not in [doc.docid for doc in docs]:
                    docs.append(sdoc)

            if len(docs) == 0:
                doc = Document(db)
            elif len(docs) > 0:
                if len(docs) > 1:
                    print("  Multiple distinct docs found for entry.  Using first found.", file=sys.stderr)
                doc = docs[0]
                print("  Updating id:%d..." % (doc.docid), file=sys.stderr)

            doc.add_bibentry(entry)

            filepath = entry.get_file()
            if filepath:
                print("  Adding file: %s" % filepath, file=sys.stderr)
                doc.add_file(filepath)

            doc.add_tags(tags)

            doc.sync()

        except BibtexError as e:
            print("  Error processing entry %s: %s" % (entry.key, e), file=sys.stderr)
            print(file=sys.stderr)
            errors.append(entry.key)

    if errors:
        print(file=sys.stderr)
        print("Failed to import %d" % (len(errors)), end=' ', file=sys.stderr)
        if len(errors) == 1:
            print("entry", end=' ', file=sys.stderr)
        else:
            print("entries", end=' ', file=sys.stderr)
        print("from bibtex:", file=sys.stderr)
        for error in errors:
            print("  %s" % (error), file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)

############################################

def search(db, query_string, oformat='summary', sort='relevance', limit=None):
    if query_string == '*' and oformat in ['tags','sources','keys']:
        if oformat == 'tags':
            for tag in db.tag_iter():
                print(tag)
        elif oformat == 'sources':
            for sid in db.sid_iter():
                print(sid)
        elif oformat == 'keys':
            for key in db.term_iter('key'):
                print(key)
        return

    otags = set([])
    osources = set([])
    okeys = set([])

    for doc in db.search(query_string, sort=sort, limit=limit):
        if oformat in ['summary']:
            print_doc_summary(doc)
            continue

        elif oformat in ['file','files']:
            for path in doc.get_fullpaths():
                print("%s" % (path))
            continue

        elif oformat == 'bibtex':
            bibtex = doc.get_bibtex()
            if not bibtex:
                print("No bibtex for doc id:%d." % doc.docid, file=sys.stderr)
            else:
                print(bibtex)
                print()
            continue

        if oformat == 'tags':
            otags = otags | set(doc.get_tags())
        elif oformat == 'sources':
            osources = osources | set(doc.get_sids())
        elif oformat == 'keys':
            key = doc.get_key()
            if key:
                print(key)

    if oformat == 'tags':
        for tag in otags:
            print(tag)
    elif oformat == 'sources':
        for source in osources:
            print(source)

############################################

def export(db, outdir, query_string):
    try:
        os.makedirs(outdir)
    except:
        pass
    import pipes
    for doc in db.search(query_string):
        title = doc.get_title()
        origpaths = doc.get_fullpaths()
        nfiles = len(origpaths)
        for path in origpaths:
            if not title:
                name = os.path.basename(os.path.splitext(path)[0])
            else:
                name = '%s' % (title.replace(' ','_'))
            ind = 0
            if nfiles > 1:
                name += '.%s' % ind
                ind += 1
            name += '.pdf'
            outpath = os.path.join(outdir,name)
            print(outpath)
            shutil.copyfile(path, outpath.encode('utf-8'))
