#!/usr/bin/env python
import unittest

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof

class TestSequenceOf(unittest.TestCase):
    def test_sequence_of_field(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8), 3)

        actual = []
        for is_starting, entry, entry_data in sequenceof.decode(dt.Data.from_hex("fb028c")):
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
        query = lambda context, child: context[child.name] 
        data = reduce(lambda a,b:a+b, sequenceof.encode(query, data))
        self.assertEqual("\x05\x09\xf6", str(data))

    def test_invalid_encoding_count(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), 3)
        data = {"blah" : [{"cat":5}, {"cat":9}]}
        query = lambda context, child: context[child.name] 
        self.assertRaises(sof.InvalidSequenceOfCount, list, sequenceof.encode(query, data))

    def test_encoding_greedy_sequenceof(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), None)
        data = {"blah" : [{"cat":5}, {"cat":9}, {"cat":0xf6}]}
        query = lambda context, child: context[child.name] 
        data = reduce(lambda a,b:a+b, sequenceof.encode(query, data))
        self.assertEqual("\x05\x09\xf6", str(data))

    def test_negative_count(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), -1)
        self.assertRaises(sof.NegativeSequenceofLoop, list, sequenceof.decode(dt.Data("")))

    def test_end_entries(self):
        null = fld.Field("null", 8, expected=dt.Data('\x00'))
        char = fld.Field("char", 8)
        sequenceof = sof.SequenceOf("null terminated string", chc.Choice('entry', [null, char]), None, end_entries=[null])
        actual = []
        data = dt.Data("hello\x00bob")
        result = ""
        for is_starting, entry, entry_data in sequenceof.decode(data):
            if not is_starting and entry.name == "char":
                result += str(entry_data)

        self.assertEqual("hello", result)
        self.assertEqual("bob", str(data))

if __name__ == "__main__":
    unittest.main()
