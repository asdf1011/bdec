#!/usr/bin/python

import os.path
import sys

sys.path.append(os.path.join(os.path.split(__file__)[0], '..', '..', '..'))

from bdec import DecodeError
from bdec.data import Data
from bdec.output.xmlout import to_file
from ole import decode, load_msword_spec

if __name__ == '__main__':

    data = Data(open(sys.argv[1], 'rb'))
    spec, common, lookup = load_msword_spec()
    try:
        to_file(decode(data, common), sys.stdout)
    except DecodeError, ex:
        try:
            (filename, line_number, column_number) = lookup[ex.entry]
        except KeyError:
            (filename, line_number, column_number) = ('unknown', 0, 0)

        print
        sys.exit("%s[%i]: %s" % (filename, line_number, str(ex)))
