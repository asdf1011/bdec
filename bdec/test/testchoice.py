#!/usr/bin/env python
import unittest

import bdec.entry as ent
import bdec.choice as chc
import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq
import bdec.spec.expression as expr

class TestChoice(unittest.TestCase):
    def test_first_successful(self):
        embedded = [fld.Field("bob", 8), fld.Field("cat", 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("017a")
        results = list(entry for is_starting, entry, entry_data, value in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("bob", results[0].name)
        self.assertEqual(0x01, int(results[0]))
        self.assertEqual("blah", results[1].name)
        self.assertEqual(0x7a, int(data))

    def test_second_successful(self):
        embedded = [fld.Field("bob", 24), fld.Field("cat", 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("7a")
        results = list(entry for is_starting, entry, entry_data, value in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("cat", results[0].name)
        self.assertEqual(0x7a, int(results[0]))
        self.assertEqual("blah", results[1].name)

    def test_uses_best_guess_on_failure(self):
        # In this test both embedded choices will fail, but
        # we should get the 'chicken' entry being reported
        # because it managed to decode the most before failing.
        cat = fld.Field("cat", 8, expected=dt.Data.from_hex("9"))
        embedded = [
            seq.Sequence("chicken", [
                fld.Field("bob", 24), 
                cat]),
            fld.Field("nope", 8, expected=dt.Data.from_hex("7"))]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("01020304")

        ex = None
        results = []
        try:
            for is_starting, entry, entry_data, value in choice.decode(data):
                results.append((is_starting, entry))
        except fld.BadDataError, ex:
            pass
        self.assertTrue(ex is not None)
        self.assertEqual(cat, ex.field)

        # The 'cat', 'chicken', and 'blah' entries should have
        # started decoding, and the 'bob' entry should have
        # fully decoded.
        self.assertEqual(5, len(results))
        self.assertEqual("blah", results[0][1].name)
        self.assertEqual("chicken", results[1][1].name)
        self.assertEqual("bob", results[2][1].name)
        self.assertEqual("bob", results[3][1].name)
        self.assertEqual("cat", results[4][1].name)
        
    def test_data_of_reused_field(self):
        # Test the results of the data of a field that is referenced
        # multiple times in a choice
        cat = fld.Field("cat", 8)
        choice = chc.Choice("blah", [seq.Sequence("chicken", [cat, cat])])
        data = dt.Data.from_hex("0102")

        decoded = []
        for is_starting, entry, entry_data, value in choice.decode(data):
            if not is_starting and len(entry_data) > 0:
                decoded.append(entry_data)

        self.assertEqual(2, len(decoded))
        self.assertEqual(1, int(decoded[0]))
        self.assertEqual(2, int(decoded[1]))

    def test_encode(self):
        # Test encoding of a number that is encoded in different sizes (depending on the size of the data)
        byte_len = seq.Sequence("bob", [fld.Field("id:", 1, expected=dt.Data("\x00", 7, 8)), fld.Field("dog", 8, format=fld.Field.INTEGER)])
        word_len = seq.Sequence("bob", [fld.Field("id:", 1, expected=dt.Data("\x01", 7, 8)), fld.Field("dog", 16, format=fld.Field.INTEGER)])
        choice = chc.Choice("blah", [byte_len, word_len])

        # First try encoding a number that will only fit in the 16 bit storage
        struct = {"blah" : {"bob" : {"dog" : 10023}}}
        def query(context, child):
            if child.name not in context:
                raise ent.MissingInstanceError(context, child)
            return context[child.name]
        data = reduce(lambda a,b:a+b, choice.encode(query, struct))
        self.assertEqual(17, len(data))

        # Now try encoding a number that will fit in the 8 bit storage
        struct = {"blah" : {"bob" : {"dog" : 117}}}
        data = reduce(lambda a,b:a+b, choice.encode(query, struct))
        self.assertEqual(9, len(data))

    def test_range(self):
        options = [fld.Field("bob", 4), fld.Field("cat", 8)]
        choice = chc.Choice("blah", options)
        self.assertEqual(4, choice.range().min)
        self.assertEqual(8, choice.range().max)

    def test_variable_length(self):
        byte = seq.Sequence('8 bit:', [fld.Field('id', 8, expected=dt.Data('\x00')), fld.Field('length', 8)])
        word = seq.Sequence('16 bit:', [fld.Field('id', 8, expected=dt.Data('\x01')), fld.Field('length', 16)])
        length = chc.Choice('variable integer', [byte, word])
        length_value = expr.ValueResult()
        length_value.add_entry(byte.children[1], 'variable integer.length')
        length_value.add_entry(word.children[1], 'variable integer.length')
        data = fld.Field('data', length_value, fld.Field.TEXT)
        spec = seq.Sequence('spec', [length, data])

        results = dict((entry, value)for is_starting, entry, entry_data, value in spec.decode(dt.Data('\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

        results = dict((entry, value)for is_starting, entry, entry_data, value in spec.decode(dt.Data('\x01\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

