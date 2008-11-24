
import mako.exceptions
import os
import sys

import bdec.spec.xmlspec
import bdec.compiler

def _load_spec(filename):
    """Load the protocol specification. """
    try:
        decoder, lookup, common = bdec.spec.xmlspec.load(filename)
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))
    return decoder, lookup, common

def main():
    if len(sys.argv) not in [2, 3]:
        sys.exit('Usage: %s <specification> [output dir]' % sys.argv[0])
    spec, lookup, common = _load_spec(sys.argv[1])
    if len(sys.argv) == 3:
        outputdir = sys.argv[2]
    else:
        outputdir = os.getcwd()

    language = 'c'
    try:
        bdec.compiler.generate_code(spec, language, outputdir, common.itervalues())
    except:
        sys.exit(mako.exceptions.text_error_template().render())

