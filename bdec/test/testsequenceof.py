#!/usr/bin/env python
import unittest

import bdec.data as dt
import bdec.field as fld
import bdec.sequenceof as sof

class TestSequenceOf(unittest.TestCase):
    def test_sequence_of_field(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8), 3)

        actual = []
        for is_starting, entry in sequenceof.decode(dt.Data.from_hex("fb028c")):
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

    def test_encoding(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), 3)
        data = {"blah" : [{"cat":5}, {"cat":9}, {"cat":0xf6}]}
        query = lambda context, name: context[name] 
        data = reduce(lambda a,b:a+b, sequenceof.encode(query, data))
        self.assertEqual("\x05\x09\xf6", str(data))

if __name__ == "__main__":
    unittest.main()
