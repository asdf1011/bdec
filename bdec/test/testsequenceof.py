#!/usr/bin/env python
import unittest

import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq
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
        query = lambda context, child: context[child.name] 
        data = reduce(lambda a,b:a+b, sequenceof.encode(query, data))
        self.assertEqual("\x05\x09\xf6", str(data))

    def test_invalid_encoding_length(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), 3)
        data = {"blah" : [{"cat":5}, {"cat":9}]}
        query = lambda context, child: context[child.name] 
        self.assertRaises(sof.InvalidSequenceOfLength, list, sequenceof.encode(query, data))

    def test_decoding_greedy_sequenceof(self):
        dog = seq.Sequence('dog', [fld.Field('bear', 8), fld.Field('id', 8, expected=dt.Data('a'))])
        sequenceof = sof.SequenceOf("blah", dog, None)
        data = dt.Data('1a2a3bb')
        # Lets decode until 'id' decodes twice...
        count = total = 0
        for is_starting, entry in sequenceof.decode(data):
            total += 1 
            if not is_starting and entry.name == "id":
                count += 1
                if count == 2:
                    sequenceof.stop()

        self.assertEqual(14, total)
        self.assertEqual(24, len(data))

    def test_encoding_greedy_sequenceof(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), None)
        data = {"blah" : [{"cat":5}, {"cat":9}, {"cat":0xf6}]}
        query = lambda context, child: context[child.name] 
        data = reduce(lambda a,b:a+b, sequenceof.encode(query, data))
        self.assertEqual("\x05\x09\xf6", str(data))

if __name__ == "__main__":
    unittest.main()
