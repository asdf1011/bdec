#!/usr/bin/env python

import unittest
import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequence as seq

class Sequence(unittest.TestCase):
    def test_simple_sequence(self):
        embedded = [fld.Field("bob", lambda: 8), fld.Field("cat", lambda: 8)]
        sequence = seq.Sequence("blah", embedded)
        data = dt.Data.from_hex("0x017a")

        calls = []
        for is_starting, entry in sequence.decode(data):
            if not is_starting:
                calls.append(entry)

        self.assertEqual(3, len(calls))
        self.assertEqual(embedded[0], calls[0])
        self.assertEqual(0x01, int(calls[0]))
        self.assertEqual(embedded[1], calls[1])
        self.assertEqual(0x7a, int(calls[1]))
        self.assertEqual(sequence, calls[2])

if __name__ == "__main__":
    unittest.main()
