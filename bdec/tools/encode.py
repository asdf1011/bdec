
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

    data = xmlout.encode(protocol, xml)
    try:
        binary = reduce(lambda a,b:a+b, data).bytes()
    except bdec.DecodeError, ex:
        (filename, line_number, column_number) = lookup[ex.entry]
        sys.exit("%s[%i]: %s" % (filename, line_number, str(ex)))
    sys.stdout.write(binary)

if __name__ == '__main__':
    main()
