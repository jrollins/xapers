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

class ParseError(Exception):
    pass

def parse_data(data, mimetype='pdf'):
    """Parse binary data of specified mime type into text (str)

    """

    try:
        mod = __import__('xapers.parsers.' + mimetype, fromlist=['Parser'])
        parse_func = getattr(mod, 'parse')
    except ImportError:
        raise ParseError("Unsupported mime type '%s'." % mimetype)

    try:
        text = parse_func(data)
    except Exception as e:
        raise ParseError("Could not parse file: %s" % e)

    return text

def parse_file(path):
    """Parse file for text (str)

    """

    # FIXME: determine mime type

    if not os.path.exists(path):
        raise ParseError("File '%s' not found." % path)

    if not os.path.isfile(path):
        raise ParseError("File '%s' is not a regular file." % path)

    with open(path, 'br') as f:
        data = f.read()

    return parse_data(data)
