#!/usr/bin/env python
import unittest

import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.output.instance as inst

class _Inst():
    """
    Class to allow quickly building python structures.
    """
    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError()
        value = _Inst()
        setattr(self, name, value)
        return value

class TestInstance(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", 8, fld.Field.INTEGER)
        data = inst.decode(field, dt.Data.from_hex('6e'))
        self.assertEqual(110, data.bob)

    def test_sequence(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertEqual(110, data.bob.cat)
        self.assertEqual("zip", data.bob.dog)

    def test_sequenceof(self):
        sequenceof = sof.SequenceOf("bob", 
            fld.Field("cat", 8, fld.Field.INTEGER),
            4)
        data = inst.decode(sequenceof, dt.Data.from_hex('6e7a6970'))
        self.assertTrue(isinstance(data.bob, list))
        self.assertEqual(4, len(data.bob))
        self.assertEqual(0x6e, int(data.bob[0]))
        self.assertEqual(0x7a, int(data.bob[1]))
        self.assertEqual(0x69, int(data.bob[2]))
        self.assertEqual(0x70, int(data.bob[3]))

    def test_hidden_entries(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        data = inst.decode(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertTrue('cat' not in "".join(dir(data.bob)))
        self.assertEqual("zip", data.bob.dog)

    def _encode(self, protocol, value):
        """
        Wrapper around inst.encode.

        Also validates that we can decode the encoded data, and get the
        same data back again.
        """
        def encode(struct):
            return str(reduce(lambda a,b:a+b, inst.encode(protocol, struct), dt.Data("")))
        data = encode(value)

        # Now validate that we can decode that data...
        re_decoded = inst.decode(protocol, dt.Data(data))
        self.assertEqual(data, encode(re_decoded))
        return data

    def test_field_encode(self):
        field = fld.Field("bob", 8, fld.Field.INTEGER)
        blah = _Inst()
        blah.bob = 0x6e
        self.assertEqual("\x6e", self._encode(field, blah))

    def test_sequence_encode(self):
        sequence = seq.Sequence("bob", [fld.Field("cat", 8, fld.Field.INTEGER), fld.Field("dog", 8, fld.Field.INTEGER)])
        blah = _Inst()
        blah.bob.cat = 0x38
        blah.bob.dog = 0x7a
        self.assertEqual("\x38\x7a", self._encode(sequence, blah))

    def test_children_of_hidden_entries_are_visible(self):
        sequence = seq.Sequence("bob:", [fld.Field("cat", 8, fld.Field.INTEGER), fld.Field("dog", 8, fld.Field.INTEGER)])
        data = inst.decode(sequence, dt.Data("\x38\x7a"))
        self.assertEqual(0x38, data.cat)
        self.assertEqual(0x7a, data.dog)

    def test_sequenceof_encode(self):
        sequenceof = sof.SequenceOf("bob", fld.Field("cat:", 8, fld.Field.INTEGER), 4)
        blah = _Inst()
        blah.bob = [0x38, 0xa7, 0x70, 0x60]
        self.assertEqual("\x38\xa7\x70\x60", self._encode(sequenceof, blah))

    def test_choice_encode(self):
        choice = chc.Choice("bob", [fld.Field("blah", 60, fld.Field.INTEGER), fld.Field("text", 56, fld.Field.TEXT)])
        blah = _Inst()
        blah.bob.text = "chicken"
        self.assertEqual("chicken", self._encode(choice, blah))

    def test_encode_item_with_space(self):
        field = fld.Field("bobs cat", 8, fld.Field.INTEGER)
        blah = _Inst()
        blah.bobs_cat = 0x6e
        self.assertEqual("\x6e", self._encode(field, blah))

    def test_encode_of_missing_hidden_field_doesnt_use_parent_context(self):
        field = fld.Field("bob:", 8, expected=dt.Data("c"))
        class Blah():
            pass
        self.assertEqual("c", self._encode(field, Blah()))

if __name__ == "__main__":
    unittest.main()
