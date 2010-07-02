
import sys
import bdec
import bdec.data as dt
from bdec.spec import load_specs
import bdec.output.xmlout as xmlout

def main():
    spec = sys.argv[1]
    try:
        protocol, common, lookup = load_specs([(spec, None, None)])
    except bdec.spec.LoadError, ex:
        sys.exit(str(ex))

    if len(sys.argv) == 3:
        xml = file(sys.argv[2], 'rb').read()
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
