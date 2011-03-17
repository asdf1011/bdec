#   Copyright (C) 2008-2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

#!/usr/bin/env python
import operator
import unittest

from bdec.encode.entry import MissingInstanceError
import bdec.entry as ent
from bdec.expression import ValueResult
import bdec.choice as chc
from bdec.constraints import Equals, ConstraintError
import bdec.data as dt
import bdec.field as fld
import bdec.sequence as seq
import bdec.expression as expr


def get_best_guess(entry, data):
    ex = None
    results = []
    try:
        for is_starting, name, entry, entry_data, value in entry.decode(data):
            results.append((is_starting, entry))
    except ConstraintError, ex:
        pass
    assert ex is not None
    return ex.entry, results

def query(context, child, i, name):
    if not context or child.name not in context:
        raise MissingInstanceError(context, child)
    return context[child.name]

class TestChoice(unittest.TestCase):
    def test_first_successful(self):
        embedded = [fld.Field("bob", 8), fld.Field("cat", 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("017a")
        results = list((entry, entry_data) for is_starting, name, entry, entry_data, value in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("bob", results[0][0].name)
        self.assertEqual(0x01, int(results[0][1]))
        self.assertEqual("blah", results[1][0].name)
        self.assertEqual(0x7a, int(data))

    def test_second_successful(self):
        embedded = [fld.Field("bob", 24), fld.Field("cat", 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("7a")
        results = list((entry, entry_data) for is_starting, name, entry, entry_data, value in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("cat", results[0][0].name)
        self.assertEqual(0x7a, int(results[0][1]))
        self.assertEqual("blah", results[1][0].name)

    def test_uses_best_guess_on_failure(self):
        # In this test both embedded choices will fail, but
        # we should get the 'chicken' entry being reported
        # because it managed to decode the most before failing.
        cat = fld.Field("cat", 8, constraints=[Equals(dt.Data.from_hex("9"))])
        embedded = [
            seq.Sequence("chicken", [
                fld.Field("bob", 24), 
                cat]),
            fld.Field("nope", 8, constraints=[Equals(dt.Data.from_hex("7"))])]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("01020304")

        ex = None
        self.assertEqual(cat, get_best_guess(choice, data.copy())[0])
        results = get_best_guess(choice, data.copy())[1]

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
        for is_starting, name, entry, entry_data, value in choice.decode(data):
            if not is_starting and len(entry_data) > 0:
                decoded.append(entry_data)

        self.assertEqual(2, len(decoded))
        self.assertEqual(1, int(decoded[0]))
        self.assertEqual(2, int(decoded[1]))

    def test_encode(self):
        # Test encoding of a number that is encoded in different sizes (depending on the size of the data)
        byte_len = seq.Sequence("bob", [
            fld.Field("id:", 1, constraints=[Equals(dt.Data("\x00", 7, 8))]),
            fld.Field("dog", 8, format=fld.Field.INTEGER)])
        word_len = seq.Sequence("bob", [
            fld.Field("id:", 1, constraints=[Equals(dt.Data("\x01", 7, 8))]),
            fld.Field("dog", 16, format=fld.Field.INTEGER)])
        choice = chc.Choice("blah", [byte_len, word_len])

        # First try encoding a number that will only fit in the 16 bit storage
        struct = {"bob" : {"dog" : 10023}}
        data = reduce(lambda a,b:a+b, choice.encode(query, struct))
        self.assertEqual(17, len(data))

        # Now try encoding a number that will fit in the 8 bit storage
        struct = {"bob" : {"dog" : 117}}
        data = reduce(lambda a,b:a+b, choice.encode(query, struct))
        self.assertEqual(9, len(data))

    def test_range(self):
        options = [fld.Field("bob", 4), fld.Field("cat", 8)]
        choice = chc.Choice("blah", options)
        self.assertEqual(4, choice.range().min)
        self.assertEqual(8, choice.range().max)

    def test_reference_common_child(self):
        byte = seq.Sequence('8 bit', [
            fld.Field('id', 8, constraints=[Equals(dt.Data('\x00'))]),
            fld.Field('length', 8)])
        word = seq.Sequence('16 bit', [
            fld.Field('id', 8, constraints=[Equals(dt.Data('\x01'))]),
            fld.Field('length', 16)])
        length = chc.Choice('variable integer', [byte, word])
        length_value = expr.ValueResult('variable integer.length')
        data = fld.Field('data', length_value, fld.Field.TEXT)
        spec = seq.Sequence('spec', [length, data])

        results = dict((entry, value)for is_starting, name, entry, entry_data, value in spec.decode(dt.Data('\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

        results = dict((entry, value)for is_starting, name, entry, entry_data, value in spec.decode(dt.Data('\x01\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

    def test_reference_choice(self):
        # Test that we can correctly reference a choice entry, where each of
        # its children have value types.
        byte = seq.Sequence('8 bit:', [
            fld.Field('id', 8, constraints=[Equals(dt.Data('\x00'))]),
            fld.Field('length', 8)],
            value=expr.compile('${length}'))
        word = seq.Sequence('16 bit:', [
            fld.Field('id', 8, constraints=[Equals(dt.Data('\x01'))]),
            fld.Field('length', 16)],
            value=expr.compile('${length}'))
        length = chc.Choice('variable integer', [byte, word])
        data = fld.Field('data', expr.compile('${variable integer}'), fld.Field.TEXT)
        spec = seq.Sequence('spec', [length, data])

        results = dict((entry, value)for is_starting, name, entry, entry_data, value in spec.decode(dt.Data('\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

        results = dict((entry, value)for is_starting, name, entry, entry_data, value in spec.decode(dt.Data('\x01\x00\x20abcde')) if not is_starting)
        self.assertEqual('abcd', results[data])

    def test_best_guess_number_of_entries(self):
        # A common pattern is to have a common type, then select on it using
        # sequences with an expected value. Even when a sequent field fails,
        # it should still report an error given the context of the failing
        # entry.
        a = seq.Sequence('a', [
            fld.Field('type:', length=8),
            chc.Choice('b', [
                seq.Sequence('c', [
                    seq.Sequence('c1', [], value=ValueResult('type:'), constraints=[Equals(0)]),
                    fld.Field('c2', length=8, constraints=[Equals(dt.Data('c'))])]),
                seq.Sequence('d', [
                    seq.Sequence('d1', [], value=ValueResult('type:'), constraints=[Equals(1)]),
                    fld.Field('d2', length=8, constraints=[Equals(dt.Data('d'))])])
                ])])

        self.assertEqual('c2', get_best_guess(a, dt.Data('\x00\x00'))[0].name)
        self.assertEqual('d2', get_best_guess(a, dt.Data('\x01\x00'))[0].name)

    def test_encoding_hidden_referenced_entry(self):
        # Test that we correctly encode a referenced instance that is only
        # used in one option of a choice.
        a = seq.Sequence('a', [
            fld.Field('is present:', length=8),
            chc.Choice('conditional', [
                seq.Sequence('not present:', [
                    seq.Sequence('check:', [],
                        value=ValueResult('is present:'), constraints=[Equals(0)])]),
                fld.Field('footer', length=32, format=fld.Field.TEXT)])])

        self.assertEqual(dt.Data('\x00'), reduce(operator.add, a.encode(query, {'a':{}})))
        self.assertEqual(dt.Data('\x01asdf'), reduce(operator.add, a.encode(query, {'a':{'footer':'asdf'}})))
