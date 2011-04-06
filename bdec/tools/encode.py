#   Copyright (C) 2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from optparse import OptionParser
import sys

import bdec
import bdec.data as dt
from bdec.spec import load_specs
import bdec.output.xmlout as xmlout

__doc__ = '''%s <spec 1> [spec 2]...
Encode xml to binary given a bdec specification. It will read the xml to from
encode from stdin.''' % sys.argv[0]

def main():
    parser = OptionParser(usage=__doc__)
    parser.add_option('-f', dest='filename', help='Read the xml from FILE '
            'instead of stdin.', metavar='FILENAME')
    parser.add_option('--main', dest='main', help='Specify the entry to '
            'be encoded instead of the toplevel protocol object.',
            metavar='ENTRY')
    parser.add_option('--remove-unused', dest='remove_unused', help='Remove '
            'unused entries from the specification after loading. This allows '
            "specs to include references that don't resolve.", action='store_true')
    options, args = parser.parse_args()

    if not args:
        sys.exit("No specifications listed! See '%s -h' for more info." % sys.argv[0])

    try:
        protocol, common, lookup = load_specs([(spec, None, None) for spec in args],
                options.main, options.remove_unused)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))

    if options.filename:
        xml = file(options.filename, 'rb').read()
    else:
        xml = sys.stdin.read()

    try:
        binary = xmlout.encode(protocol, xml).bytes()
    except bdec.DecodeError, ex:
        try:
            (filename, line_number, column_number) = lookup[ex.entry]
        except KeyError:
            (filename, line_number, column_number) = ('unknown', 0, 0)
        sys.exit("%s[%i]: %s" % (filename, line_number, str(ex)))
    sys.stdout.write(binary)

if __name__ == '__main__':
    main()
