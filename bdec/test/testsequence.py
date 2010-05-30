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

    def test_multiple_validates(self):
        a = fld.Field('a', 8)

        # Now embed 'a' in a sequence, but add a new reference to it; make
        # sure we can still decode.
        b = seq.Sequence('b', [a], value=expr.ValueResult('a'))
        result = list(b.decode(dt.Data('\x01')))
        self.assertEqual('b', result[-1][1])
        self.assertEqual(1, int(result[-1][-1]))

    def test_validate_doesnt_remove_parameters(self):
        # Test that a second validate call doesn't remove parameters added
        # by the first validate call.
        a = fld.Field('a', 8)
        b = seq.Sequence('b', [a])
        c = seq.Sequence('c', [b], value=expr.ValueResult('b.a'))
        d = seq.Sequence('d', [b])

        list(c.decode(dt.Data('\x00')))

        # The bug in the second validate removed the parameter from the 'a'
        # field, causing the second decode to fail.
        list(c.decode(dt.Data('\x00')))
        list(d.decode(dt.Data('\x00')))

    def test_validate_with_unused_output(self):
        a = fld.Field('a', 8)
        b = seq.Sequence('b', [ent.Child('a1', a)])

        # Create one object where 'b.a' is required.
        c = seq.Sequence('c', [b], value=expr.ValueResult('b.a1'))

        # Create another object where 'a' is required, but not 'b.a'.
        d = seq.Sequence('d', [a, b], value=expr.ValueResult('a'))

        list(c.decode(dt.Data('\x00')))
        list(d.decode(dt.Data('\x00\x00')))

