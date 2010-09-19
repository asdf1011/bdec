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
from bdec.spec import load_specs

def usage(program):
    print 'Decode standard input to xml given a bdec specification.'
    print 'Usage:'
    print '   %s [options] <spec_filename>' % program
    print
    print 'Arguments:'
    print '   spec_filename -- The filename of the specification to be compiled.'
    print
    print 'Options:'
    print '  -f <filename>     Decode from filename instead of stdin.'
    print '  -h, --help        Print this help.'
    print '  -l                Log status messages.'
    print '  --main=<name>     Specify the entry to be used as the decoder.'
    print '  -q                Quiet output. Only errors will be printed to stderr.'
    print '  --remove-unused   Remove any entries that are not referenced from the main'
    print '                    entry.'
    print '  --verbose         Include hidden entries and raw data in the decoded output.'
    print '  -V                Print the version of the bdec compiler.'

def _parse_args():
    verbose = 1
    binary = sys.stdin
    main_spec = None
    should_remove_unused = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'f:hlqV', ['help', 'main=', 'remove-unused', 'verbose'])
    except getopt.GetoptError, ex:
        sys.exit("%s\nSee '%s -h' for correct usage." % (ex, sys.argv[0]))
    for opt, arg in opts:
        if opt == '-f':
            binary = open(arg, 'rb')
        elif opt in ['-h', '--help']:
            usage(sys.argv[0])
            sys.exit(0)
        elif opt == '--main':
            main_spec = arg
        elif opt == '-q':
            verbose = 0
        elif opt == '--verbose':
            verbose = 2
        elif opt == '--remove-unused':
            should_remove_unused = True
        elif opt == "-l":
            logging.basicConfig(level=logging.INFO)
        elif opt == '-V':
            print bdec.__version__
            sys.exit(0)
        else:
            assert 0, 'Unhandled option %s!' % opt

    if len(args) == 0:
        sys.exit("Missing arguments! See '%s -h' for more info." % sys.argv[0])

    return (main_spec, args, binary, verbose, should_remove_unused)


def main():
    main_spec, specs, binary, verbose, should_remove_unused = _parse_args()
    try:
        decoder, common, lookup = load_specs([(s, None, None) for s in specs], main_spec, should_remove_unused)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))

    data = dt.Data(binary)
    try:
        if verbose == 0:
            for item in decoder.decode(data):
                pass
        else:
            xmlout.to_file(decoder, data, sys.stdout, verbose=(verbose==2))
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

