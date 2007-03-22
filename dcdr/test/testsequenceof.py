#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequenceof as sof

class TestSequenceOf(unittest.TestCase):
    def test_sequence_of_field(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", lambda: 8), lambda: 3)

        actual = []
        for is_starting, entry in sequenceof.decode(dt.Data.from_hex("0xfb028c")):
            if not is_starting:
                data = None
                if isinstance(entry, fld.Field):
                    data = int(entry.data)
                actual.append((entry.name, data))

        expected = [("cat", 0xfb),
            ("cat", 0x02),
            ("cat", 0x8c),
            ("blah", None)]
        self.assertEqual(expected, actual)

if __name__ == "__main__":
    unittest.main()
