#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

import mako.exceptions
import os
import sys

import bdec.spec.xmlspec
import bdec.compiler

def _load_spec(filename):
    """Load the protocol specification. """
    try:
        decoder, common, lookup = bdec.spec.xmlspec.load(filename)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))
    return decoder, common, lookup

def main():
    if len(sys.argv) not in [2, 3]:
        sys.exit('Usage: %s <specification> [output dir]' % sys.argv[0])
    spec, common, lookup = _load_spec(sys.argv[1])
    if len(sys.argv) == 3:
        outputdir = sys.argv[2]
    else:
        outputdir = os.getcwd()

    language = 'c'
    try:
        bdec.compiler.generate_code(spec, language, outputdir, common.itervalues())
    except:
        sys.exit(mako.exceptions.text_error_template().render())

if __name__ == '__main__':
    main()

