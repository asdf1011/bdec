#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequence as seq
import dcdr.sequenceof as sof
import dcdr.output.instance as inst

class TestInstance(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", lambda: 8, fld.Field.INTEGER)
        data = inst.decode(field, dt.Data.from_hex('0x6e'))
        self.assertEqual(110, data.bob)

    def test_sequence(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat", lambda: 8, fld.Field.INTEGER),
            fld.Field("dog", lambda: 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('0x6e7a6970'))
        self.assertEqual(110, data.bob.cat)
        self.assertEqual("zip", data.bob.dog)

    def test_sequenceof(self):
        sequenceof = sof.SequenceOf("bob", 
            fld.Field("cat", lambda: 8, fld.Field.INTEGER),
            lambda: 4)
        data = inst.decode(sequenceof, dt.Data.from_hex('0x6e7a6970'))
        self.assertTrue(isinstance(data.bob, list))
        self.assertEqual(4, len(data.bob))
        self.assertEqual(0x6e, int(data.bob[0]))
        self.assertEqual(0x7a, int(data.bob[1]))
        self.assertEqual(0x69, int(data.bob[2]))
        self.assertEqual(0x70, int(data.bob[3]))

    def test_hidden_entries(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", lambda: 8, fld.Field.INTEGER),
            fld.Field("dog", lambda: 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('0x6e7a6970'))
        self.assertTrue('cat' not in dir(data.bob))
        self.assertEqual("zip", data.bob.dog)

if __name__ == "__main__":
    unittest.main()
