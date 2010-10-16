#   Copyright (C) 2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
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

from bdec.spec import load_specs
import bdec.compiler


def usage(program):
    print 'Compile bdec specifications into language specific decoders.'
    print 'Usage:'
    print '   %s [options] <spec_filename> [spec_filename] ...' % program
    print
    print 'Arguments:'
    print '   spec_filename -- The filename of the specification to be compiled.'
    print
    print 'Options:'
    print '  -h, --help        Print this help.'
    print '  -d <directory>    Directory to save the generated source code. Defaults'
    print '                    to %s.' % os.getcwd()
    print '  --encoder         Generate an encoder as well as a decoder.'
    print '  --main=<name>     Specify the entry to be use as the default decoder.'
    print '  --remove-unused   Remove any entries that are not referenced from the'
    print '                    main entry.'
    print '  --template=<name> Set the template to compile. If there is a directory'
    print '                    with the specified name, it will be used as the'
    print '                    template directory. Otherwise it will use the internal'
    print '                    template with the specified name. If not specified a'
    print '                    C language decoder will be compiled.'
    print '  -V                Print the version of the bdec compiler.'

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'd:hV', ['encoder', 'help', 'main=', 'remove-unused', 'template='])
    except getopt.GetoptError, ex:
        sys.exit("%s.\nRun '%s -h' for correct usage." % (ex, sys.argv[0]))

    main_spec = None
    template_dir = None
    outputdir = os.getcwd()
    should_remove_unused = False
    options = {
            'generate_encoder' : False
            }
    for opt, arg in opts:
        if opt == '-d':
            outputdir = arg
        elif opt == '--encoder':
            options['generate_encoder'] = True
        elif opt in ['-h', '--help']:
            usage(sys.argv[0])
            sys.exit(0)
        elif opt == '--main':
            main_spec = arg
        elif opt == '-V':
            print bdec.__version__
            sys.exit(0)
        elif opt == '--remove-unused':
            should_remove_unused = True
        elif opt == '--template':
            if os.path.exists(arg):
                template_dir = bdec.compiler.FilesystemTemplate(arg)
            else:
                template_dir = bdec.compiler.BuiltinTemplate(arg)
        elif opt == '--main':
            main_spec = arg
        else:
            assert False, 'Unhandled option %s!' % opt

    try:
        spec, common, lookup = load_specs([(s, None, None) for s in args], main_spec, should_remove_unused)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))

    if template_dir is None:
        template_dir = bdec.compiler.BuiltinTemplate('c')

    try:
        templates = bdec.compiler.load_templates(template_dir)
        bdec.compiler.generate_code(spec, templates, outputdir, common, options)
    except:
        sys.exit(mako.exceptions.text_error_template().render())

if __name__ == '__main__':
    main()

