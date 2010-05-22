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

import getopt
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

def usage(program):
    print 'Compile bdec specifications into language specific decoders.'
    print 'Usage:'
    print '   %s [options] <spec_filename> [output_dir]' % program
    print
    print 'Arguments:'
    print '   spec_filename -- The filename of the specification to be compiled.'
    print '   output_dir -- The directory to save the generated source code. If'
    print '       not specified the current working directory will be used.'
    print
    print 'Options:'
    print '  -h    Print this help.'
    print '  -V    Print the version of the bdec compiler.'

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hV')
    except getopt.GetoptError, ex:
        sys.exit("%s.\nRun '%s -h' for correct usage." % (ex, sys.argv[0]))

    for opt, arg in opts:
        if opt == '-h':
            usage(sys.argv[0])
            sys.exit(0)
        elif opt == '-V':
            print bdec.__version__
            sys.exit(0)
        else:
            assert False, 'Unhandled option %s!' % opt

    if len(args) not in [1, 2]:
        sys.exit('Usage: %s [options] <spec_filename> [output_dir]' % sys.argv[0])

    spec, common, lookup = _load_spec(args[0])
    if len(args) == 2:
        outputdir = args[1]
    else:
        outputdir = os.getcwd()

    language = 'c'
    try:
        bdec.compiler.generate_code(spec, language, outputdir, common.itervalues())
    except:
        sys.exit(mako.exceptions.text_error_template().render())

if __name__ == '__main__':
    main()

