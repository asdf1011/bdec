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

#!/usr/bin/env python
import unittest

import bdec.choice as chc
from bdec.constraints import Equals
import bdec.data as dt
from bdec.entry import Child
from bdec.expression import parse
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.output.instance as inst

class _Inst():
    pass

class TestInstance(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", 8, fld.Field.INTEGER)
        data = inst.decode(field, dt.Data.from_hex('6e'))
        self.assertEqual(110, data)

    def test_sequence(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertEqual(110, data.cat)
        self.assertEqual("zip", data.dog)

    def test_sequenceof(self):
        sequenceof = sof.SequenceOf("bob", 
            fld.Field("cat", 8, fld.Field.INTEGER),
            4)
        data = inst.decode(sequenceof, dt.Data.from_hex('6e7a6970'))
        self.assertTrue(isinstance(data, list))
        self.assertEqual(4, len(data))
        self.assertEqual(0x6e, int(data[0]))
        self.assertEqual(0x7a, int(data[1]))
        self.assertEqual(0x69, int(data[2]))
        self.assertEqual(0x70, int(data[3]))

    def test_hidden_entries(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertTrue('cat' not in "".join(dir(data)))
        self.assertEqual("zip", data.dog)

    def _encode(self, protocol, value):
        """
        Wrapper around inst.encode.

        Also validates that we can decode the encoded data, and get the
        same data back again.
        """
        def encode(struct):
            return reduce(lambda a,b:a+b, inst.encode(protocol, struct), dt.Data("")).bytes()
        data = encode(value)

        # Now validate that we can decode that data...
        re_decoded = inst.decode(protocol, dt.Data(data))
        self.assertEqual(data, encode(re_decoded))
        return data

    def test_field_encode(self):
        field = fld.Field("bob", 8, fld.Field.INTEGER)
        self.assertEqual("\x6e", self._encode(field, 0x6e))

    def test_sequence_encode(self):
        sequence = seq.Sequence("bob", [fld.Field("cat", 8, fld.Field.INTEGER), fld.Field("dog", 8, fld.Field.INTEGER)])
        blah = _Inst()
        blah.cat = 0x38
        blah.dog = 0x7a
        self.assertEqual("\x38\x7a", self._encode(sequence, blah))

    def test_children_of_hidden_entries_are_not_visible(self):
        sequence = seq.Sequence("bob:", [fld.Field("cat", 8, fld.Field.INTEGER), fld.Field("dog", 8, fld.Field.INTEGER)])
        data = inst.decode(sequence, dt.Data("\x38\x7a"))
        assert data is None

    def test_sequenceof_encode(self):
        sequenceof = sof.SequenceOf("bob", fld.Field("cat", 8, fld.Field.INTEGER), 4)
        blah = [0x38, 0xa7, 0x70, 0x60]
        self.assertEqual("\x38\xa7\x70\x60", self._encode(sequenceof, blah))

    def test_choice_encode(self):
        choice = chc.Choice("bob", [fld.Field("blah", 60, fld.Field.INTEGER), fld.Field("text", 56, fld.Field.TEXT)])
        blah = _Inst()
        blah.text = "chicken"
        self.assertEqual("chicken", self._encode(choice, blah))

    def test_encode_item_with_space(self):
        field = seq.Sequence('a', [fld.Field("bobs cat", 8, fld.Field.INTEGER)])
        blah = _Inst()
        blah.bobs_cat = 0x6e
        self.assertEqual("\x6e", self._encode(field, blah))

    def test_encode_of_missing_hidden_field_doesnt_use_parent_context(self):
        field = fld.Field("bob:", 8, constraints=[Equals(dt.Data("c"))])
        self.assertEqual("c", self._encode(field, None))

    def test_reference_name(self):
        a = fld.Field('a', 8)
        b = seq.Sequence('b', [Child('c', a)])
        data = inst.decode(b, dt.Data('\x33'))
        self.assertEqual(0x33, int(data.c))

    def test_sequence_value(self):
        a = seq.Sequence('a', [seq.Sequence('hidden:', [])], value=parse('5'))
        data = inst.decode(a, dt.Data())
        self.assertEqual(5, data)

    def test_sequence_with_children_and_value(self):
        a = seq.Sequence('a', [fld.Field('b', length=8, format=fld.Field.INTEGER)], value=parse('7'))
        data = inst.decode(a, dt.Data('\x33'))
        self.assertEqual(0x33, data.b)
        self.assertEqual(7, int(data))

    def test_exception_when_seequence_is_not_an_int(self):
        a = seq.Sequence('a', [])
        data = inst.decode(a, dt.Data())
        self.assertRaises(TypeError, int, data)

    def test_sequence_to_string(self):
        a = seq.Sequence('a', [fld.Field('b', 8, format=fld.Field.INTEGER)])
        data = inst.decode(a, dt.Data('\x09'))
        self.assertEqual("{'b': 9}", str(data))

    def test_sequenceof_to_string(self):
        a = sof.SequenceOf('a', fld.Field('b', 8, format=fld.Field.INTEGER), count=parse('3'))
        data = inst.decode(a, dt.Data('\x09\x01\x0a'))
        self.assertEqual("[9, 1, 10]", str(data))

    def test_sequence_with_hidden_field_to_string(self):
        a = seq.Sequence('a', [fld.Field('length:', 8), fld.Field('b', format=fld.Field.TEXT, length=parse('${length:} * 8'))])
        data = inst.decode(a, dt.Data('\x03cat'))
        self.assertEqual(u"{'b': u'cat'}", unicode(data))

