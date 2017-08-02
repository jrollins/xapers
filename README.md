Xapers - personal journal article management system
===================================================

Xapers is a personal document indexing system, geared towards academic
journal articles.  Think of it as your own personal document search
engine, or a local cache of online libraries.  It provides fast search
of document text and bibliographic data and simple document and bibtex
retrieval.

Document files (in PDF format) and source identifiers (e.g. DOI) are
parsed and indexed into a Xapian search engine [0].  Document text is
extracted from the PDF and fully indexed.  Bibliographic information
downloaded from online libraries is indexed as prefixed search terms.
Existing bibtex databases can be easily imported as well, including
import of pdf files specified in Jabref/Mendeley format.  Documents
can be arbitrarily tagged.  Original document files are easily
retrievable from a simple curses search UI.  The command line
interface allows for exporting bibtex [1] from arbitrary searches,
allowing seamless integration into LaTeX work flows.

Xapers provides source modules for some common online resources:

  * doi: Digital Object Identifier (https://dx.doi.org/)
  * arxiv: Open access e-print service (http://arxiv.org/)
  * dcc: LIGO Document Control Center (https://dcc.ligo.org/)
  * cryptoeprint: Cryptology ePrint Archive (https://eprint.iacr.org/)

Contributions of additional source interface modules is highly
encouraged.  See the "Document Sources" section below for info on
creating new sources.

Xapers is heavily inspired by the notmuch mail indexing system [2].

[0] http://www.xapian.org/
[1] http://www.bibtex.org/
[2] http://notmuchmail.org/

![xapers ncurses UI]](screenshot.png "xapers ncurses UI")


Contact
=======

Xapers was written by:

    Jameson Graef Rollins <jrollins@finestructure.net>

Xapers has a mailing list:

    xapers@lists.mayfirst.org
    https://lists.mayfirst.org/mailman/listinfo/xapers

We also hang out on IRC:

    channel: #xapers
    server:  irc.freenode.net

Please submit all bug reports to the Debian bug tracking system (BTS):

    https://bugs.debian.org/xapers
    https://www.debian.org/Bugs/Reporting


Getting Xapers
==============

Source
------

Clone the repo:

    $ git clone git://finestructure.net/xapers
    $ cd xapers

Dependencies :
  * python3
  * python3-xapian - Python Xapian search engine bindings
  * python3-pybtex - Python bibtex parser
  * poppler-utils - PDF processing tools
  * python3-pycurl - Python bindings to libcurl

Recommends (for curses UI) :
  * python3-urwid - Python Urwid curses library
  * xdg-utils - Desktop tools for opening files and URLs
  * xclip - X clipboard support for copying document fields

On Debian:

    $ sudo apt-get install python3-xapian python3-pybtex python3-pycurl poppler-utils python3-urwid xdg-utils xclip

Run the tests:

    $ make test

Debian
------

Xapers is a part of Debian:

    $ apt install xapers

Debian/Ubuntu snapshot packages can be easily made from the git
source.  You can build the package from any branch but it requires an
up-to-date local branch of origin/debian, e.g.:

    $ git branch debian origin/debian

Then:

    $ sudo apt-get install build-essential devscripts pkg-config python-all-dev python-setuptools debhelper dpkg-dev fakeroot
    $ make debian-snapshot
    $ sudo dpkg -i build/xapers_0.8_amd64.deb


Using Xapers
============

See the included xapers(1) man page for detailed usage and information
on source modules and searching.

Command line interface
----------------------

The main interface to Xapers is the xapers command line utility.  From
this interface you can import documents, search, tag, etc.

The "add" command allows importing or updating single documents.  The
"import" command allows importing an entire bibtex databases (.bib
file).  If the bibtex entries include "file" fields (ala. Mendeley or
Jabref), then those files are retrieved, indexed, and imported as
well.

Curses interface
----------------

The curses interface ("xapers show ...") provides a simple way to
display search results and retrieve files.  Documents matching
searches are displayed with their bibliographic information.  Document
tags can be manipulated, files and bibtex can be viewed, and source
URLs can be opened in a browser.

xapers-adder
------------

xapers-adder is a simple script that helps the adding of individual
documents to your Xapers database.  It can be used e.g. as a PDF
handler in your favorite browser.  It displays the PDF then presents
the user with the option to import the document into Xapers.  The user
is prompted for any sources to retrieve and any initial tags to add.
If the source is known, bibtex is retrieved and indexed.  The
resulting xapers entry for the document is displayed.

Development of more clever import methods is highly encouraged.

Python library
--------------

Xapers is a python library under the hood:

    >>> import xapers
    >>> db = xapers.Database('~/.xapers/docs')
    >>> docs = db.search('tag:new')
    >>> for doc in docs:
            doc.add_tags(['foo'])
            ...
    >>> 

Development of new interfaces to the underlying library is highly
encouraged.


Docuemnt Sources
================

A Xapers "source" is a python module that describes how to interact
with a single online journal database, from which document files and
bibliographic data can be retrieved.

Sources are assigned unique prefixes (e.g. "doi").  Online libraries
associate unique document identifiers to individual documents
(e.g. "10.1364/JOSAA.29.002092").  A particular online document is
therefore described by a unique "source identifier", or "sid", which
can take two equivalent forms:

  full URL            http://dx.doi.org/10.1364/JOSAA.29.002092
  <source>:<id>       doi:10.1364/JOSAA.29.002092

CUSTOM SOURCE MODULES
---------------------

Custom source modules may be written to extend the base functionality
of Xapers.  A source module is described by a single python module
(although it may import arbitrary other modules).  The base name of
the module file is interpreted as the nickname or 'prefix' for the
source (e.g. if the module is named "doi.py" the source nickname will
be "doi").

The module should include the following properties and functions.  If
any are missing, some xapers functionality may be undefined.

  description: a brief string description of the source, e.g.:

    description = "Digital Object Identifier"

  url: base URL of source, e.g.:

    url = 'http://dx.doi.org/'

  url_format: a printf format string that produces a valid source URL
    for a specified source identifier string, e.g.:

    url_format = 'http://dx.doi.org/%s'

  url_regex: a regular expression string that will match the source
    identifier string from a given full URL, e.g.:

    url_regex = 'http://dx.doi.org/(10\.\d{4,}[\w\d\:\.\-\/]+)'

  scan_regex: a regular expression string that will match the source
    identifier string in a scan of a documents plain text, e.g.:

    scan_regex = '(?:doi|DOI)[\s\.\:]{0,2}' + id_regex

  fetch_bibtex(id): a function that will return a bibtex string for a
    source document specified by id.

  fetch_file(id): a function that will return a (file_name, file_data)
    tuple for a source document specified by id.  File should be in
    PDF format.

If your source does not provide bibliographic data directly in bibtex
format, the xapers.bibtex module has several helper functions for
creating bibtex strings from python dictionaries (data2bib) or json
objects (json2bib).

See existing source module contributed with the xapers source as
examples (lib/xapers/sources/).

Source module path
------------------

Once a custom source module has been created, place it
~/.xapers/sources.  The module path can be overridden with the
XAPERS_SOURCE_PATH environment variable, which can be a
colon-separated list of directories to search for modules.

Testing
-------

Once a module is in place, use the xapers source* commands (sources,
source2url, source2bib, source2file) to test it's functionality.  Your
new module should show up in the source listing with the "sources"
command, and should be able to print the relevant data with the other
commands.

Contributing
------------

If you think your module is stable and of general usefulness to the
community, please consider contributing it upstream.  Thanks!
