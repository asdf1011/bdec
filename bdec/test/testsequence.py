#!/usr/bin/env python

import unittest
import bdec.data as dt
import bdec.entry as ent
import bdec.field as fld
import bdec.sequence as seq

class TestSequence(unittest.TestCase):
    def test_simple_sequence(self):
        embedded = [fld.Field("bob", 8), fld.Field("cat", 8)]
        sequence = seq.Sequence("blah", embedded)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, entry, entry_data, value in sequence.decode(data):
            if not is_starting:
                calls.append(entry)

        self.assertEqual(3, len(calls))
        self.assertEqual(embedded[0], calls[0])
        self.assertEqual(0x01, int(calls[0]))
        self.assertEqual(embedded[1], calls[1])
        self.assertEqual(0x7a, int(calls[1]))
        self.assertEqual(sequence, calls[2])

    def test_encode_sequence(self):
        embedded = [fld.Field("bob", 8, format=fld.Field.INTEGER), fld.Field("cat", 8, format=fld.Field.INTEGER)]
        sequence = seq.Sequence("blah", embedded)
        struct = {"blah" : {"bob" : 0x01, "cat" : 0x7a}}
        query = lambda context, child: context[child.name]
        data = reduce(lambda a,b:a+b, sequence.encode(query, struct))
        self.assertEqual("\x01\x7a", data.bytes())

    def test_listener(self):
        embedded = [fld.Field("bob", 8, format=fld.Field.INTEGER), fld.Field("cat", 8, format=fld.Field.INTEGER)]
        sequence = seq.Sequence("blah", embedded)
        callbacks = []
        sequence.add_listener(lambda entry, length, context: callbacks.append((entry, length)))
        self.assertEqual(0, len(callbacks))
        list(sequence.decode(dt.Data.from_hex("017a")))
        self.assertEqual(1, len(callbacks))
        self.assertEqual(sequence, callbacks[0][0])
        self.assertEqual(16, callbacks[0][1])

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
