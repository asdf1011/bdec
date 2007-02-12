#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequence as seq
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


if __name__ == "__main__":
    unittest.main()
