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

##################################################

class ParseError(Exception):
    """Base class for Xapers parser exceptions."""
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

##################################################

class ParserBase():
    """Base class for Xapers document parsering."""
    def __init__(self, path):
        self.path = os.path.expanduser(path)

    def extract(self):
        pass

##################################################

def parse_data(data):
    """Parse binary file data into text (str)"""
    # FIXME: determine mime type
    mimetype = 'pdf'

    from xapers.parsers.pdf import extract

    try:
        text = extract(data)
    except Exception as e:
        raise ParseError("Could not parse file: %s" % e)

    return text

def parse_file(path):
    # FIXME: determine mime type
    mimetype = 'pdf'

    try:
        mod = __import__('xapers.parsers.' + mimetype, fromlist=['Parser'])
        pmod = getattr(mod, 'Parser')
    except ImportError:
        raise ParseError("Unknown parser '%s'." % mimetype)


    if not os.path.exists(path):
        raise ParseError("File '%s' not found." % path)

    if not os.path.isfile(path):
        raise ParseError("File '%s' is not a regular file." % path)

    try:
        text = pmod(path).extract()
    except Exception as e:
        raise ParseError("Could not parse file: %s" % e)

    return text
