#   Copyright (C) 2008, 2009 Henry Ludemann
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

#!/usr/bin/env python

import unittest
from bdec.constraints import ConstraintError, Equals
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as expr
import bdec.field as fld
import bdec.sequence as seq

class TestSequence(unittest.TestCase):
    def test_simple_sequence(self):
        embedded = [fld.Field("bob", 8), fld.Field("cat", 8)]
        sequence = seq.Sequence("blah", embedded)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, name, entry, entry_data, value in sequence.decode(data):
            if not is_starting:
                calls.append((entry, entry_data))

        self.assertEqual(3, len(calls))
        self.assertEqual(embedded[0], calls[0][0])
        self.assertEqual(0x01, int(calls[0][1]))
        self.assertEqual(embedded[1], calls[1][0])
        self.assertEqual(0x7a, int(calls[1][1]))
        self.assertEqual(sequence, calls[2][0])

    def test_encode(self):
        embedded = [fld.Field("bob", 8, format=fld.Field.INTEGER), fld.Field("cat", 8, format=fld.Field.INTEGER)]
        sequence = seq.Sequence("blah", embedded)
        struct = {"bob" : 0x01, "cat" : 0x7a}
        query = lambda context, child: context[child.name]
        data = reduce(lambda a,b:a+b, sequence.encode(query, struct))
        self.assertEqual("\x01\x7a", data.bytes())

    def test_bad_length(self):
        embedded = [fld.Field("bob", 8, format=fld.Field.INTEGER), fld.Field("cat", 8, format=fld.Field.INTEGER)]
        sequence = seq.Sequence("blah", embedded, length=17)
        self.assertRaises(ent.DecodeLengthError, list, sequence.decode(dt.Data('abc')))
        sequence = seq.Sequence("blah", embedded, length=15)
        self.assertRaises(ent.EntryDataError, list, sequence.decode(dt.Data('abc')))

    def test_range(self):
        children = [fld.Field("bob", 8), fld.Field("cat", 8)]
        sequence = seq.Sequence("blah", children)
        self.assertEqual(16, sequence.range().min)
        self.assertEqual(16, sequence.range().max)

    def test_sequence_expected_value(self):
        a = seq.Sequence('a', [fld.Field('b', 8), fld.Field('c', 8)], value=expr.compile('${b} + ${c}'))
        a.constraints.append(Equals(7))
        list(a.decode(dt.Data('\x03\x04')))
        list(a.decode(dt.Data('\x06\x01')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x05\x01')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x07\x01')))

