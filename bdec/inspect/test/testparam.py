#   Copyright (C) 2008-2009 Henry Ludemann
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

import operator
import unittest

import bdec
import bdec.choice as chc
from bdec.constraints import Equals, Maximum, Minimum
import bdec.data as dt
import bdec.entry as ent
import bdec.field as fld
import bdec.inspect.param as prm
from bdec.inspect.type import EntryType, IntegerType, EntryLengthType
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.expression as expr

class _Integer(IntegerType):
    """Test class that identifies an integer parameter."""
    def __eq__(self, other):
        return isinstance(other, IntegerType)


class TestExpressionParameters(unittest.TestCase):
    def test_direct_children(self):
        a = fld.Field('a', 8)
        value = expr.ValueResult('a')
        b = fld.Field('b', value)
        spec = seq.Sequence('blah', [a,b])

        vars = prm.ExpressionParameters([spec])
        self.assertEqual([prm.Local('a', _Integer())], vars.get_locals(spec))
        self.assertTrue(vars.is_value_referenced(a))
        self.assertFalse(vars.is_value_referenced(b))
        self.assertEqual([], vars.get_locals(a))

    def test_sub_children(self):
        a2 = fld.Field('a2', 8)
        a1 = seq.Sequence('a1', [a2])
        a = seq.Sequence('a', [a1])
        value = expr.ValueResult('a.a1.a2')
        b1 = fld.Field('b1', value)
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = prm.ExpressionParameters([spec])
        self.assertEqual([prm.Local('a.a1.a2', _Integer())], vars.get_locals(spec))
        # Note that despite containing a referenced entry, it isn't a local (as
        # it is passed up to the parent entry).
        self.assertEqual([], vars.get_locals(a))

        # Now check what parameters are passed in and out. Note that we check
        # that the name is correct for the context of the parameter.
        self.assertEqual([], vars.get_params(spec))
        self.assertEqual([prm.Param('a2', prm.Param.OUT, _Integer())], vars.get_params(a2))
        self.assertEqual([prm.Param('a2', prm.Param.OUT, _Integer())], vars.get_params(a1))
        self.assertEqual([prm.Param('a1.a2', prm.Param.OUT, _Integer())], vars.get_params(a))
        self.assertEqual([prm.Param('a1.a2', prm.Param.OUT, _Integer())], list(vars.get_passed_variables(a, a.children[0])))
        self.assertEqual([prm.Param('a.a1.a2', prm.Param.IN, _Integer())], vars.get_params(b))
        self.assertEqual([prm.Param('a.a1.a2', prm.Param.IN, _Integer())], vars.get_params(b1))
        self.assertEqual([prm.Param('a.a1.a2', prm.Param.IN, _Integer())], list(vars.get_passed_variables(b, b.children[0])))

    def test_length_reference(self):
        a1 = fld.Field('a1', 8)
        a = seq.Sequence('a', [a1])
        b1 = fld.Field('b1', expr.LengthResult('a'))
        b = seq.Sequence('b', [b1])
        spec = seq.Sequence('blah', [a,b])

        vars = prm.ExpressionParameters([spec])
        self.assertEqual([prm.Local('a length', _Integer())], vars.get_locals(spec))
        self.assertFalse(vars.is_length_referenced(a1))
        self.assertTrue(vars.is_length_referenced(a))
        self.assertEqual([prm.Param('a length', prm.Param.OUT, EntryLengthType(a))], vars.get_params(a))
        self.assertEqual([prm.Param('a length', prm.Param.IN, EntryLengthType(a))], vars.get_params(b))

    def test_sequence_value(self):
        # Define an integer with a custom byte ordering
        lower = fld.Field('lower byte', 8)
        lower_value = expr.ValueResult('lower byte')
        ignored = fld.Field('ignored', 8)
        upper = fld.Field('upper byte', 8)
        upper_value = expr.ValueResult('upper byte')
        value = expr.Delayed(operator.__add__, expr.Delayed(operator.__mul__, upper_value, expr.Constant(256)), lower_value)
        length = seq.Sequence('length', [lower, ignored, upper], value)
        header = seq.Sequence('header', [length])

        int_value = expr.ValueResult('length')
        data = fld.Field('data', int_value)
        spec = seq.Sequence('blah', [length, data])

        vars = prm.ExpressionParameters([spec])
        self.assertEquals([], vars.get_params(spec))
        self.assertTrue(vars.is_value_referenced(lower))
        self.assertFalse(vars.is_value_referenced(ignored))
        self.assertTrue(vars.is_value_referenced(upper))
        self.assertEqual([prm.Local('lower byte', _Integer()), prm.Local('upper byte', _Integer())], vars.get_locals(length))
        self.assertEqual([prm.Param('lower byte', prm.Param.OUT, _Integer())], vars.get_params(lower))
        self.assertEqual([prm.Param('upper byte', prm.Param.OUT, _Integer())], vars.get_params(upper))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], vars.get_params(length))

        self.assertEqual([prm.Local('length', _Integer())], vars.get_locals(spec))
        self.assertEqual([prm.Param('length', prm.Param.IN, _Integer())], vars.get_params(data))

    def test_choice_reference(self):
        """
        Test the parameter names when we have items selected under a choice.
        """
        byte = seq.Sequence('8 bit:', [fld.Field('id', 8, constraints=[Equals(dt.Data('\x00'))]), fld.Field('length', 8)])
        word = seq.Sequence('16 bit:', [fld.Field('id', 8, constraints=[Equals(dt.Data('\x01'))]), fld.Field('length', 16)])
        length = chc.Choice('variable integer', [byte, word])
        length_value = expr.ValueResult('variable integer.length')
        data = fld.Field('data', length_value)
        spec = seq.Sequence('spec', [length, data])
        vars = prm.ExpressionParameters([spec])

        self.assertFalse(vars.is_value_referenced(byte))
        self.assertTrue(vars.is_value_referenced(byte.children[1].entry))
        self.assertFalse(vars.is_value_referenced(word))
        self.assertTrue(vars.is_value_referenced(word.children[1].entry))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], vars.get_params(byte))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], vars.get_params(word))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], vars.get_params(length))
        self.assertEqual([], vars.get_locals(length))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], list(vars.get_passed_variables(length, length.children[0])))

        self.assertEqual([prm.Local('variable integer.length', _Integer())], vars.get_locals(spec))
        self.assertEqual([prm.Param('variable integer.length', prm.Param.IN, _Integer())], vars.get_params(data))

    def test_reference_outside_of_choice(self):
        """
        Test passing in a parameter into choice options.
        """
        # Note that the 'integer' option has a fixed length...
        length = fld.Field('length:', 8)
        length_value = expr.ValueResult('length:')
        text = seq.Sequence('text', [
            fld.Field('id:',  8, constraints=[Equals(dt.Data('\x00'))]),
            fld.Field('value', length_value, fld.Field.TEXT)])
        integer = seq.Sequence('integer', [
            fld.Field('id:',  8, constraints=[Equals(dt.Data('\x01'))]),
            fld.Field('value', 16, fld.Field.INTEGER)])
        spec = seq.Sequence('spec', [length, chc.Choice('data', [text, integer])])

        vars = prm.ExpressionParameters([spec])
        self.assertTrue(vars.is_value_referenced(length))
        self.assertEqual([], vars.get_params(spec))
        self.assertEqual([prm.Local('length:', _Integer())], vars.get_locals(spec))
        self.assertEqual([prm.Param('length:', prm.Param.OUT, _Integer())], vars.get_params(length))
        self.assertEqual([prm.Param('length:', prm.Param.OUT, _Integer())], list(vars.get_passed_variables(spec, spec.children[0])))

        self.assertEqual([prm.Param('length:', prm.Param.IN, _Integer())], vars.get_params(spec.children[1].entry))
        self.assertEqual([prm.Param('length:', prm.Param.IN, _Integer())], list(vars.get_passed_variables(spec, spec.children[1])))
        self.assertEqual([prm.Param('length:', prm.Param.IN, _Integer())], vars.get_params(text))
        self.assertEqual([prm.Param('length:', prm.Param.IN, _Integer())], list(vars.get_passed_variables(spec.children[1].entry, spec.children[1].entry.children[0])))
        self.assertEqual([prm.Param('length:', prm.Param.IN, _Integer())], vars.get_params(text.children[1].entry))
        self.assertEqual([], vars.get_params(integer))
        self.assertEqual([], list(vars.get_passed_variables(spec.children[1].entry, spec.children[1].entry.children[1])))

    def test_unused_parameters(self):
        # Test detection of re-use of a common entry, where not all output parameters are used.
        length = fld.Field('length', 8)
        shared = seq.Sequence('shared', [length])
        length_value = expr.ValueResult('shared.length')

        # Now we'll reference that common component twice, but only once
        # referencing an actual value. In 'b' we use it twice, to detect that
        # it only turns up in the locals list once.
        a = seq.Sequence('a', [shared, fld.Field('a data', length_value)])
        b = seq.Sequence('b', [shared, shared])
        spec = seq.Sequence('spec', [a,b])
        vars = prm.ExpressionParameters([spec])
        self.assertEqual([], list(vars.get_params(spec)))
        self.assertTrue(vars.is_value_referenced(length))
        self.assertFalse(vars.is_value_referenced(shared))
        self.assertEqual([], vars.get_locals(spec))

        # Test that the 'length' and 'shared' entries pass out their value
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], list(vars.get_params(length)))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], vars.get_params(shared))

        # First validate the passing of the length value within entry 'a'
        self.assertEqual([], vars.get_params(a))
        self.assertEqual([prm.Local('shared.length', _Integer())], vars.get_locals(a))
        self.assertEqual([prm.Param('shared.length', prm.Param.OUT, _Integer())], list(vars.get_passed_variables(a, a.children[0])))
        self.assertEqual([prm.Param('shared.length', prm.Param.IN, _Integer())], list(vars.get_passed_variables(a, a.children[1])))
        self.assertEqual([], list(vars.get_passed_variables(spec, spec.children[0])))

        # Now test the passing out (and ignoring) of the length value within 'b'
        self.assertEqual([], vars.get_params(b))
        self.assertEqual([prm.Local('length', _Integer())], vars.get_locals(b))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())], list(vars.get_passed_variables(b, b.children[0])))
        self.assertEqual([], list(vars.get_passed_variables(spec, spec.children[0])))

    def test_referencing_sequence_without_value(self):
        a = seq.Sequence('a', [])
        b = fld.Field('b', expr.compile('${a}'), fld.Field.INTEGER)
        c = seq.Sequence('c', [a, b])

        self.assertRaises(prm.BadReferenceError, prm.ExpressionParameters, [c])

    def test_name_ends_in_length(self):
        a = fld.Field('data length', 8, fld.Field.INTEGER)
        b = fld.Field('data', expr.compile('${data length} * 8'))
        c = seq.Sequence('c', [a, b])
        params = prm.ExpressionParameters([c])
        self.assertEqual([prm.Local('data length', _Integer())], params.get_locals(c))
        self.assertEqual([], params.get_params(c))
        self.assertEqual([prm.Param('data length', prm.Param.OUT, _Integer())], params.get_params(a))
        self.assertEqual([prm.Param('data length', prm.Param.IN, _Integer())], params.get_params(b))
        self.assertEqual(True, params.is_value_referenced(a))
        self.assertEqual(False, params.is_length_referenced(a))

    def test_param_ordering(self):
        # Test that we order the parameters consistently
        a = fld.Field('a', 8)
        b = fld.Field('b', 8)
        c = fld.Field('c', 8)
        d = seq.Sequence('d', [a,b,c])

        e = fld.Field('e', expr.compile('${d.a} + ${d.b} + ${d.c}'))
        f = seq.Sequence('f', [d, e])

        params = prm.ExpressionParameters([f])
        self.assertEqual([prm.Local('d.a', _Integer()),
            prm.Local('d.b', _Integer()),
            prm.Local('d.c', _Integer())], params.get_locals(f))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer()), 
            prm.Param('b', prm.Param.OUT, _Integer()),
            prm.Param('c', prm.Param.OUT, _Integer())],
            params.get_params(d))
        self.assertEqual([prm.Param('d.a', prm.Param.OUT, _Integer()),
            prm.Param('d.b', prm.Param.OUT, _Integer()),
            prm.Param('d.c', prm.Param.OUT, _Integer())],
            list(params.get_passed_variables(f, f.children[0])))

    def test_renamed_common_reference(self):
        text_digit = fld.Field('text digit', 8, constraints=[Minimum(48), Maximum(58)])

        digit = seq.Sequence('digit', [text_digit],
            value=expr.compile("${text digit} - 48"))
        b = seq.Sequence('b', [
            ent.Child('length', digit),
            fld.Field('data', length=expr.compile("${length} * 8"))])
        lookup = prm.ExpressionParameters([b])
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([prm.Param('digit', prm.Param.OUT, _Integer())],
                lookup.get_params(digit))
        self.assertEqual([prm.Param('length', prm.Param.OUT, _Integer())],
                list(lookup.get_passed_variables(b, b.children[0])))

    def test_choice_reference(self):
        # Test that we can correctly reference a choice (which in effect
        # references each of its children).
        #
        # We test this by creating a choice where each child has a value type,
        # and attempt to reference the top level choice.
        len = fld.Field('len', length=8)
        a = fld.Field('a', length=32)
        b = fld.Field('b', length=16)
        c = fld.Field('c', length=8)
        var_len = chc.Choice('var_len', [a, b, c], length=expr.compile('${len}'))
        data = fld.Field('data', length=expr.compile('${var_len}'))
        spec = seq.Sequence('spec', [len, var_len, data])

        # Check the parameters passed in and out of each entry
        lookup = prm.ExpressionParameters([spec])
        self.assertEqual([], lookup.get_params(spec))
        self.assertEqual([prm.Param('len', prm.Param.OUT, _Integer())],
                lookup.get_params(len))
        self.assertEqual([prm.Param('len', prm.Param.IN, _Integer()),
                    prm.Param('var_len', prm.Param.OUT, _Integer())],
                lookup.get_params(var_len))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())],
                lookup.get_params(a))
        self.assertEqual([prm.Param('b', prm.Param.OUT, _Integer())],
                lookup.get_params(b))
        self.assertEqual([prm.Param('var_len', prm.Param.IN, _Integer())],
                lookup.get_params(data))

        # Test the mapping of the parameters for the choice to the option
        # entries.
        self.assertEqual([prm.Param('var_len', prm.Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[0])))
        self.assertEqual([prm.Param('var_len', prm.Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[1])))
        self.assertEqual([prm.Param('var_len', prm.Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[2])))

        # And validate the locals...
        self.assertEqual([prm.Local('len', _Integer()), prm.Local('var_len', _Integer())], lookup.get_locals(spec))
        self.assertEqual([], lookup.get_locals(len))
        self.assertEqual([], lookup.get_locals(var_len))
        self.assertEqual([], lookup.get_locals(a))
        self.assertEqual([], lookup.get_locals(data))

    def test_in_and_out_parameters(self):
        # Test what happens when we have a parameter that is to be passed out
        # of an entry, but also into a child (issue122).
        #
        #        ___ e ___
        #   __c__         d(len=a)
        #  a   b(len=a)
        a = fld.Field('a', length=8)
        b = fld.Field('b', length=expr.compile('${a}'))
        c = seq.Sequence('c', [a, b])
        d = fld.Field('d', length=expr.compile('${c.a}'))
        e = seq.Sequence('e', [c, d])

        lookup = prm.ExpressionParameters([e])
        self.assertEqual([], lookup.get_params(e))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())], lookup.get_params(a))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())], lookup.get_params(c))
        self.assertEqual([prm.Param('a', prm.Param.IN, _Integer())], lookup.get_params(b))
        self.assertEqual([prm.Param('c.a', prm.Param.IN, _Integer())], lookup.get_params(d))
        self.assertEqual([prm.Local('c.a', _Integer())], lookup.get_locals(e))
        self.assertEqual([], lookup.get_locals(c))

        self.assertTrue(lookup.is_value_referenced(a))

        self.assertEqual([prm.Param('a', prm.Param.IN, _Integer())],
                list(lookup.get_passed_variables(c, c.children[1])))
        self.assertEqual([prm.Param('c.a', prm.Param.IN, _Integer())],
                list(lookup.get_passed_variables(e, e.children[1])))

    def test_length_and_value_reference(self):
        # Test a length reference and a value reference to the same entry.
        a = fld.Field('a', length=8)
        c = fld.Field('c', length=expr.compile('len{a}'))
        d = fld.Field('d', length=expr.compile('${a}'))
        b = seq.Sequence('b', [a, c, d])

        # Lets just try a quick decode to make sure we've specified it ok...
        #list(b.decode(dt.Data('\x08cd')))

        # Now test the parameters being passed around.
        lookup = prm.ExpressionParameters([b])
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer()),
            prm.Param('a length', prm.Param.OUT, _Integer())],
                lookup.get_params(a))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer()),
            prm.Param('a length', prm.Param.OUT, _Integer())],
                list(lookup.get_passed_variables(b, b.children[0])))
        self.assertEqual([prm.Param('a length', prm.Param.IN, _Integer())],
                list(lookup.get_passed_variables(b, b.children[1])))
        self.assertEqual([prm.Param('a length', prm.Param.IN, _Integer())],
                lookup.get_params(c))
        self.assertEqual([prm.Local('a', _Integer()), prm.Local('a length', _Integer())],
                lookup.get_locals(b))
        self.assertTrue(lookup.is_length_referenced(a))

    def test_common_entry_with_input_parameter(self):
        # Test that we correctly resolve a common entry that has an input
        # parameter that resolves to mulitiple (different) entries.
        a = fld.Field('a', length=expr.compile('${b}'))

        # Here the common entry 'a' is used into two locations, each time it
        # resolves to an entry with a different length.
        c = seq.Sequence('c', [fld.Field('b', 8), a])
        d = seq.Sequence('d', [fld.Field('b', 16), a])
        lookup = prm.ExpressionParameters([a, c, d])

        self.assertEqual([prm.Param('b', prm.Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[0])))
        self.assertEqual([prm.Param('b', prm.Param.OUT, _Integer())], list(lookup.get_passed_variables(d, d.children[0])))

    def test_unused_parameters_with_same_name(self):
        # Test that when we have multiple 'unused' parameters with the same
        # name we don't duplicate the same local variable. This happened with
        # the vfat specification (the different bootsector types all had the
        # same output parameters).
        a1 = fld.Field('a', length=16)
        a2 = fld.Field('a', length=8)
        # C doesn't use the outputs from a1 and a2, so should have a single
        # local variable.
        c = seq.Sequence('c', [a1, a2])
        # Now create a couple of other entries that actually use a1 & a2
        d1 = seq.Sequence('d1', [a1, fld.Field('e1', length=expr.compile('${a}'))])
        d2 = seq.Sequence('d2', [a2, fld.Field('e2', length=expr.compile('${a}'))])

        lookup = prm.ExpressionParameters([a1, a2, c, d1, d2])
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[0])))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[1])))
        self.assertEqual([prm.Local('a', _Integer())], lookup.get_locals(c))

    def test_sequence_with_referenced_value(self):
        a = fld.Field('a', length=8)
        b = seq.Sequence('b', [ent.Child('b:', a)], value=expr.compile('${b:}'))
        c = fld.Field('c', length=expr.compile('${b} * 8'))
        d = seq.Sequence('d', [a, b, c])
        lookup = prm.ExpressionParameters([a, d])
        self.assertEqual([prm.Local('b:', _Integer())], lookup.get_locals(b))
        self.assertEqual([prm.Param('a', prm.Param.OUT, _Integer())], lookup.get_params(a))
        self.assertEqual([prm.Param('b', prm.Param.OUT, _Integer())], lookup.get_params(b))
        self.assertEqual([prm.Param('b', prm.Param.IN, _Integer())], lookup.get_params(c))
        self.assertEqual([], lookup.get_params(d))

    def test_exception_when_referencing_text_field(self):
        a = seq.Sequence('a', [fld.Field('b', length=8, format=fld.Field.TEXT),
            fld.Field('c', length=expr.compile('${b}'))])
        self.assertRaises(prm.BadReferenceTypeError, prm.ExpressionParameters, [a])

class TestEndEntryParameters(unittest.TestCase):
    def test_end_entry_lookup(self):
        null = fld.Field("null", 8, constraints=[Equals(dt.Data('\x00'))])
        char = fld.Field("char", 8)
        entry = chc.Choice('entry', [null, char])
        string = sof.SequenceOf("null terminated string", entry, None, end_entries=[null])

        lookup = prm.EndEntryParameters([string])
        self.assertEqual(set([prm.Param('should end', prm.Param.OUT, prm.ShouldEndType())]), lookup.get_params(null))
        self.assertEqual(set([prm.Param('should end', prm.Param.OUT, prm.ShouldEndType())]), lookup.get_params(entry))
        self.assertEqual([prm.Local('should end', _Integer())], lookup.get_locals(string))
        self.assertTrue(lookup.is_end_sequenceof(null))

class TestResultParameters(unittest.TestCase):
    def test_field_output(self):
        a = fld.Field('a', 8)
        b = seq.Sequence('b', [a])
        lookup = prm.ResultParameters([b])
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(a))], lookup.get_params(a))
        self.assertEqual([prm.Param('unknown', prm.Param.OUT, EntryType(a))], lookup.get_passed_variables(b, b.children[0]))
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(b))], lookup.get_params(b))

    def test_hidden_field(self):
        a = fld.Field('', 8)
        lookup = prm.ResultParameters([a])
        self.assertEqual([], lookup.get_params(a))

    def test_hidden_entry_visible_child(self):
        # If an entry is hidden, but it has visible children, we want the entry
        # to be hidden regardless.
        a = fld.Field('a', 8)
        b = seq.Sequence('', [a])
        lookup = prm.ResultParameters([b])
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([], lookup.get_params(a))

    def test_recursive_common(self):
        # Test a recursive parser to decode xml style data

        embedded = seq.Sequence('embedded', [])
        digit = fld.Field('data', 8, constraints=[Minimum(ord('0')), Maximum(ord('9'))])
        item = chc.Choice('item', [embedded, digit])
        embedded.children = [
                fld.Field('', length=8, format=fld.Field.TEXT, constraints=[Equals('<')]),
                item,
                fld.Field('', length=8, format=fld.Field.TEXT, constraints=[Equals('>')])]

        # Lets just test that we can decode things correctly...
        list(item.decode(dt.Data('8')))
        list(item.decode(dt.Data('<5>')))
        list(item.decode(dt.Data('<<7>>')))
        self.assertRaises(bdec.DecodeError, list, item.decode(dt.Data('a')))
        self.assertRaises(bdec.DecodeError, list, item.decode(dt.Data('<5')))

        lookup = prm.ResultParameters([item])
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(item))], lookup.get_params(item))
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(embedded))], lookup.get_params(embedded))

    def test_hidden_reference(self):
        # Test a visible common reference that is hidden through its reference
        # name. This is common for integers defined at the common level.
        #
        # Note that in this case 'b' won't have an output, because all of the
        # fields it defines are hidden, and so doesn't have a type itself.
        a = fld.Field('a', 8, fld.Field.INTEGER)
        b = seq.Sequence('b', [ent.Child('a:', a)])
        lookup = prm.ResultParameters([a, b])
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(a))], lookup.get_params(a))
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(b))], lookup.get_params(b))
        self.assertEqual([prm.Local('unused a:', EntryType(a))], lookup.get_locals(b))
        self.assertEqual([prm.Param('unused a:', prm.Param.OUT, EntryType(a))], lookup.get_passed_variables(b, b.children[0]))

    def test_sequence_value(self):
        a = fld.Field('a:', 8, fld.Field.INTEGER)
        b = seq.Sequence('b', [a], expr.compile('${a:}'))
        lookup = prm.ResultParameters([b])
        self.assertEqual([], lookup.get_params(a))
        self.assertEqual([prm.Param('result', prm.Param.OUT, EntryType(b))],
                lookup.get_params(b))
        self.assertEqual([], lookup.get_locals(a))
        self.assertEqual([], lookup.get_locals(b))
        self.assertEqual([], lookup.get_passed_variables(b, b.children[0]))


class TestDataChecker(unittest.TestCase):
    def test_hidden_entry_visible_child(self):
        # Test that when the parent entry is hidden, the child entry is hidden
        # too.
        a = fld.Field('a', 8)
        b = seq.Sequence('b:', [a])
        checker = prm.DataChecker([b])
        self.assertFalse(checker.contains_data(a))
        self.assertFalse(checker.contains_data(b))
        self.assertFalse(checker.child_has_data(b.children[0]))

