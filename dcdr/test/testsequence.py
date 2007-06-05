#!/usr/bin/env python

import unittest
import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequence as seq

class Sequence(unittest.TestCase):
    def test_simple_sequence(self):
        embedded = [fld.Field("bob", lambda: 8), fld.Field("cat", lambda: 8)]
        sequence = seq.Sequence("blah", embedded)
        data = dt.Data.from_hex("017a")

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

    def test_encode_sequence(self):
        embedded = [fld.Field("bob", lambda: 8, format=fld.Field.INTEGER), fld.Field("cat", lambda: 8, format=fld.Field.INTEGER)]
        sequence = seq.Sequence("blah", embedded)
        struct = {"blah" : {"bob" : 0x01, "cat" : 0x7a}}
        query = lambda context, name: context[name]
        data = reduce(lambda a,b:a+b, sequence.encode(query, struct))
        self.assertEqual("\x01\x7a", str(data))

if __name__ == "__main__":
    unittest.main()
