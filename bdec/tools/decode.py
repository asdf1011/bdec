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

import logging
import sys

import getopt

import bdec
import bdec.data as dt
import bdec.inspect.param
import bdec.output.xmlout as xmlout
from bdec.spec import load

def usage(program):
    print 'Decode a file given a bdec specification to xml.'
    print 'Usage:'
    print '   %s [options] <spec_filename> [data_filename]' % program
    print
    print 'Arguments:'
    print '   spec_filename -- The filename of the specification to be compiled.'
    print '   data_filename -- The file we want to decode. If not specified, it '
    print '       will decode the data from stdin.'
    print
    print 'Options:'
    print '  -h         Print this help.'
    print '  -l         Log status messages.'
    print '  --verbose  Include hidden entries and raw data in the decoded output.'
    print '  -V         Print the version of the bdec compiler.'

def _parse_args():
    verbose = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hlV', 'verbose')
    except getopt.GetoptError, ex:
        sys.exit("%s\nSee '%s -h' for correct usage." % (ex, sys.argv[0]))
    for opt, arg in opts:
        if opt == '-h':
            usage(sys.argv[0])
            sys.exit(0)
        elif opt == '--verbose':
            verbose = True
        elif opt == "-l":
            logging.basicConfig(level=logging.INFO)
        elif opt == '-V':
            print bdec.__version__
            sys.exit(0)
        else:
            assert 0, 'Unhandled option %s!' % opt

    binary = None
    if len(args) == 0:
        sys.exit("Usage: %s [options] <spec_filename> [data_filename]" % sys.argv[0])
    elif len(args) == 1:
        binary = sys.stdin
    elif len(args) == 2:
        binary = file(args[1], 'rb')
    else:
        sys.exit('Too many arguments!')
    spec = args[0]

    return (spec, binary, verbose)


def main():
    spec, binary, verbose = _parse_args()
    try:
        decoder, common, lookup = load(spec)
        bdec.spec.validate_no_input_params(decoder, lookup)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))

    data = dt.Data(binary)
    try:
        xmlout.to_file(decoder, data, sys.stdout, verbose=verbose)
    except bdec.DecodeError, ex:
        try:
            (filename, line_number, column_number) = lookup[ex.entry]
        except KeyError:
            (filename, line_number, column_number) = ('unknown', 0, 0)

        # We include an extra new line, as the xml is unlikely to have finished
        # on a new line (issue164).
        print
        sys.exit("%s[%i]: %s" % (filename, line_number, str(ex)))

    try:
        # Test to see if we have data undecoded...
        remaining = data.pop(1)

        try:
            # Only attempt to display the first 8 bytes; more isn't particularly
            # useful.
            remaining = remaining + data.copy().pop(8 * 8 - 1)
            sys.stderr.write('Over 8 bytes undecoded!\n')
        except dt.NotEnoughDataError:
            remaining = remaining + data
            sys.stderr.write('Data is still undecoded!\n')
        sys.stderr.write(str(remaining) + '\n')
    except dt.NotEnoughDataError:
        # All the data has been decoded.
        pass

if __name__ == '__main__':
    main()

