#   Copyright (C) 2008-2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import operator
import unittest

import bdec
from bdec.choice import Choice
from bdec.constraints import Equals, Maximum, Minimum
from bdec.data import Data
from bdec.entry import Child
from bdec.field import Field
from bdec.inspect.param import EncodeExpressionParameters, Param, \
        ResultParameters, Local, ExpressionParameters, BadReferenceError, \
        BadReferenceTypeError, EndEntryParameters, ShouldEndType, DataChecker
from bdec.inspect.type import EntryType, IntegerType, EntryLengthType, EntryValueType
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf
from bdec.expression import parse, ValueResult, Constant, LengthResult, \
        ArithmeticExpression

class _Integer(IntegerType, object):
    """Test class that identifies an integer parameter."""
    def __eq__(self, other):
        return isinstance(other, IntegerType)

    def __str__(self):
        return 'integer'

class TestExpressionParameters(unittest.TestCase):
    def test_direct_children(self):
        a = Field('a', 8)
        value = ValueResult('a')
        b = Field('b', value)
        spec = Sequence('blah', [a,b])

        vars = ExpressionParameters([spec])
        self.assertEqual([Local('a', _Integer())], vars.get_locals(spec))
        self.assertTrue(vars.is_value_referenced(a))
        self.assertFalse(vars.is_value_referenced(b))
        self.assertEqual([], vars.get_locals(a))

    def test_sub_children(self):
        a2 = Field('a2', 8)
        a1 = Sequence('a1', [a2])
        a = Sequence('a', [a1])
        value = ValueResult('a.a1.a2')
        b1 = Field('b1', value)
        b = Sequence('b', [b1])
        spec = Sequence('blah', [a,b])

        vars = ExpressionParameters([spec])
        self.assertEqual([Local('a.a1.a2', _Integer())], vars.get_locals(spec))
        # Note that despite containing a referenced entry, it isn't a local (as
        # it is passed up to the parent entry).
        self.assertEqual([], vars.get_locals(a))

        # Now check what parameters are passed in and out. Note that we check
        # that the name is correct for the context of the parameter.
        self.assertEqual([], vars.get_params(spec))
        self.assertEqual([Param('a2', Param.OUT, _Integer())], vars.get_params(a2))
        self.assertEqual([Param('a2', Param.OUT, _Integer())], vars.get_params(a1))
        self.assertEqual([Param('a1.a2', Param.OUT, _Integer())], vars.get_params(a))
        self.assertEqual([Param('a1.a2', Param.OUT, _Integer())], list(vars.get_passed_variables(a, a.children[0])))
        self.assertEqual([Param('a.a1.a2', Param.IN, _Integer())], vars.get_params(b))
        self.assertEqual([Param('a.a1.a2', Param.IN, _Integer())], vars.get_params(b1))
        self.assertEqual([Param('a.a1.a2', Param.IN, _Integer())], list(vars.get_passed_variables(b, b.children[0])))

    def test_length_reference(self):
        a1 = Field('a1', 8)
        a = Sequence('a', [a1])
        b1 = Field('b1', LengthResult('a'))
        b = Sequence('b', [b1])
        spec = Sequence('blah', [a,b])

        vars = ExpressionParameters([spec])
        self.assertEqual([Local('a length', _Integer())], vars.get_locals(spec))
        self.assertFalse(vars.is_length_referenced(a1))
        self.assertTrue(vars.is_length_referenced(a))
        self.assertEqual([Param('a length', Param.OUT, EntryLengthType(a))], vars.get_params(a))
        self.assertEqual([Param('a length', Param.IN, EntryLengthType(a))], vars.get_params(b))

    def test_sequence_value(self):
        # Define an integer with a custom byte ordering
        lower = Field('lower byte', 8)
        lower_value = ValueResult('lower byte')
        ignored = Field('ignored', 8)
        upper = Field('upper byte', 8)
        upper_value = ValueResult('upper byte')
        value = ArithmeticExpression(operator.__add__, ArithmeticExpression(operator.__mul__, upper_value, Constant(256)), lower_value)
        length = Sequence('length', [lower, ignored, upper], value)
        header = Sequence('header', [length])

        int_value = ValueResult('length')
        data = Field('data', int_value)
        spec = Sequence('blah', [length, data])

        vars = ExpressionParameters([spec])
        self.assertEquals([], vars.get_params(spec))
        self.assertTrue(vars.is_value_referenced(lower))
        self.assertFalse(vars.is_value_referenced(ignored))
        self.assertTrue(vars.is_value_referenced(upper))
        self.assertEqual([Local('lower byte', _Integer()), Local('upper byte', _Integer())], vars.get_locals(length))
        self.assertEqual([Param('lower byte', Param.OUT, _Integer())], vars.get_params(lower))
        self.assertEqual([Param('upper byte', Param.OUT, _Integer())], vars.get_params(upper))
        self.assertEqual([Param('length', Param.OUT, _Integer())], vars.get_params(length))

        self.assertEqual([Local('length', _Integer())], vars.get_locals(spec))
        self.assertEqual([Param('length', Param.IN, _Integer())], vars.get_params(data))

    def test_choice_reference(self):
        """
        Test the parameter names when we have items selected under a choice.
        """
        byte = Sequence('8 bit:', [Field('id', 8, constraints=[Equals(Data('\x00'))]), Field('length', 8)])
        word = Sequence('16 bit:', [Field('id', 8, constraints=[Equals(Data('\x01'))]), Field('length', 16)])
        length = Choice('variable integer', [byte, word])
        length_value = ValueResult('variable integer.length')
        data = Field('data', length_value)
        spec = Sequence('spec', [length, data])
        vars = ExpressionParameters([spec])

        self.assertFalse(vars.is_value_referenced(byte))
        self.assertTrue(vars.is_value_referenced(byte.children[1].entry))
        self.assertFalse(vars.is_value_referenced(word))
        self.assertTrue(vars.is_value_referenced(word.children[1].entry))
        self.assertEqual([Param('length', Param.OUT, _Integer())], vars.get_params(byte))
        self.assertEqual([Param('length', Param.OUT, _Integer())], vars.get_params(word))
        self.assertEqual([Param('length', Param.OUT, _Integer())], vars.get_params(length))
        self.assertEqual([], vars.get_locals(length))
        self.assertEqual([Param('length', Param.OUT, _Integer())], list(vars.get_passed_variables(length, length.children[0])))

        self.assertEqual([Local('variable integer.length', _Integer())], vars.get_locals(spec))
        self.assertEqual([Param('variable integer.length', Param.IN, _Integer())], vars.get_params(data))

    def test_reference_outside_of_choice(self):
        """
        Test passing in a parameter into choice options.
        """
        # Note that the 'integer' option has a fixed length...
        length = Field('length:', 8)
        length_value = ValueResult('length:')
        text = Sequence('text', [
            Field('id:',  8, constraints=[Equals(Data('\x00'))]),
            Field('value', length_value, Field.TEXT)])
        integer = Sequence('integer', [
            Field('id:',  8, constraints=[Equals(Data('\x01'))]),
            Field('value', 16, Field.INTEGER)])
        spec = Sequence('spec', [length, Choice('data', [text, integer])])

        vars = ExpressionParameters([spec])
        self.assertTrue(vars.is_value_referenced(length))
        self.assertEqual([], vars.get_params(spec))
        self.assertEqual([Local('length:', _Integer())], vars.get_locals(spec))
        self.assertEqual([Param('length:', Param.OUT, _Integer())], vars.get_params(length))
        self.assertEqual([Param('length:', Param.OUT, _Integer())], list(vars.get_passed_variables(spec, spec.children[0])))

        self.assertEqual([Param('length:', Param.IN, _Integer())], vars.get_params(spec.children[1].entry))
        self.assertEqual([Param('length:', Param.IN, _Integer())], list(vars.get_passed_variables(spec, spec.children[1])))
        self.assertEqual([Param('length:', Param.IN, _Integer())], vars.get_params(text))
        self.assertEqual([Param('length:', Param.IN, _Integer())], list(vars.get_passed_variables(spec.children[1].entry, spec.children[1].entry.children[0])))
        self.assertEqual([Param('length:', Param.IN, _Integer())], vars.get_params(text.children[1].entry))
        self.assertEqual([], vars.get_params(integer))
        self.assertEqual([], list(vars.get_passed_variables(spec.children[1].entry, spec.children[1].entry.children[1])))

    def test_unused_parameters(self):
        # Test detection of re-use of a common entry, where not all output parameters are used.
        length = Field('length', 8)
        shared = Sequence('shared', [length])
        length_value = ValueResult('shared.length')

        # Now we'll reference that common component twice, but only once
        # referencing an actual value. In 'b' we use it twice, to detect that
        # it only turns up in the locals list once.
        a = Sequence('a', [shared, Field('a data', length_value)])
        b = Sequence('b', [shared, shared])
        spec = Sequence('spec', [a,b])
        vars = ExpressionParameters([spec])
        self.assertEqual([], list(vars.get_params(spec)))
        self.assertTrue(vars.is_value_referenced(length))
        self.assertFalse(vars.is_value_referenced(shared))
        self.assertEqual([], vars.get_locals(spec))

        # Test that the 'length' and 'shared' entries pass out their value
        self.assertEqual([Param('length', Param.OUT, _Integer())], list(vars.get_params(length)))
        self.assertEqual([Param('length', Param.OUT, _Integer())], vars.get_params(shared))

        # First validate the passing of the length value within entry 'a'
        self.assertEqual([], vars.get_params(a))
        self.assertEqual([Local('shared.length', _Integer())], vars.get_locals(a))
        self.assertEqual([Param('shared.length', Param.OUT, _Integer())], list(vars.get_passed_variables(a, a.children[0])))
        self.assertEqual([Param('shared.length', Param.IN, _Integer())], list(vars.get_passed_variables(a, a.children[1])))
        self.assertEqual([], list(vars.get_passed_variables(spec, spec.children[0])))

        # Now test the passing out (and ignoring) of the length value within 'b'
        self.assertEqual([], vars.get_params(b))
        self.assertEqual([Local('unused length', _Integer())], vars.get_locals(b))
        self.assertEqual([Param('unused length', Param.OUT, _Integer())], list(vars.get_passed_variables(b, b.children[0])))
        self.assertEqual([], list(vars.get_passed_variables(spec, spec.children[0])))

    def test_referencing_sequence_without_value(self):
        a = Sequence('a', [])
        b = Field('b', parse('${a}'), Field.INTEGER)
        c = Sequence('c', [a, b])

        self.assertRaises(BadReferenceError, ExpressionParameters, [c])

    def test_name_ends_in_length(self):
        a = Field('data length', 8, Field.INTEGER)
        b = Field('data', parse('${data length} * 8'))
        c = Sequence('c', [a, b])
        params = ExpressionParameters([c])
        self.assertEqual([Local('data length', _Integer())], params.get_locals(c))
        self.assertEqual([], params.get_params(c))
        self.assertEqual([Param('data length', Param.OUT, _Integer())], params.get_params(a))
        self.assertEqual([Param('data length', Param.IN, _Integer())], params.get_params(b))
        self.assertEqual(True, params.is_value_referenced(a))
        self.assertEqual(False, params.is_length_referenced(a))

    def test_param_ordering(self):
        # Test that we order the parameters consistently
        a = Field('a', 8)
        b = Field('b', 8)
        c = Field('c', 8)
        d = Sequence('d', [a,b,c])

        e = Field('e', parse('${d.a} + ${d.b} + ${d.c}'))
        f = Sequence('f', [d, e])

        params = ExpressionParameters([f])
        self.assertEqual([Local('d.a', _Integer()),
            Local('d.b', _Integer()),
            Local('d.c', _Integer())], params.get_locals(f))
        self.assertEqual([Param('a', Param.OUT, _Integer()), 
            Param('b', Param.OUT, _Integer()),
            Param('c', Param.OUT, _Integer())],
            params.get_params(d))
        self.assertEqual([Param('d.a', Param.OUT, _Integer()),
            Param('d.b', Param.OUT, _Integer()),
            Param('d.c', Param.OUT, _Integer())],
            list(params.get_passed_variables(f, f.children[0])))

    def test_renamed_common_reference(self):
        text_digit = Field('text digit', 8, constraints=[Minimum(48), Maximum(58)])

        digit = Sequence('digit', [text_digit],
            value=parse("${text digit} - 48"))
        b = Sequence('b', [
            Child('length', digit),
            Field('data', length=parse("${length} * 8"))])
        lookup = ExpressionParameters([b])
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([Param('digit', Param.OUT, _Integer())],
                lookup.get_params(digit))
        self.assertEqual([Param('length', Param.OUT, _Integer())],
                list(lookup.get_passed_variables(b, b.children[0])))

    def test_choice_reference(self):
        # Test that we can correctly reference a choice (which in effect
        # references each of its children).
        #
        # We test this by creating a choice where each child has a value type,
        # and attempt to reference the top level choice.
        len = Field('len', length=8)
        a = Field('a', length=32)
        b = Field('b', length=16)
        c = Field('c', length=8)
        var_len = Choice('var_len', [a, b, c], length=parse('${len}'))
        data = Field('data', length=parse('${var_len}'))
        spec = Sequence('spec', [len, var_len, data])

        # Check the parameters passed in and out of each entry
        lookup = ExpressionParameters([spec])
        self.assertEqual([], lookup.get_params(spec))
        self.assertEqual([Param('len', Param.OUT, _Integer())],
                lookup.get_params(len))
        self.assertEqual([Param('len', Param.IN, _Integer()),
                    Param('var_len', Param.OUT, _Integer())],
                lookup.get_params(var_len))
        self.assertEqual([Param('a', Param.OUT, _Integer())],
                lookup.get_params(a))
        self.assertEqual([Param('b', Param.OUT, _Integer())],
                lookup.get_params(b))
        self.assertEqual([Param('var_len', Param.IN, _Integer())],
                lookup.get_params(data))

        # Test the mapping of the parameters for the choice to the option
        # entries.
        self.assertEqual([Param('var_len', Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[0])))
        self.assertEqual([Param('var_len', Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[1])))
        self.assertEqual([Param('var_len', Param.OUT, _Integer())],
                list(lookup.get_passed_variables(var_len, var_len.children[2])))

        # And validate the locals...
        self.assertEqual([Local('len', _Integer()), Local('var_len', _Integer())], lookup.get_locals(spec))
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
        a = Field('a', length=8)
        b = Field('b', length=parse('${a}'))
        c = Sequence('c', [a, b])
        d = Field('d', length=parse('${c.a}'))
        e = Sequence('e', [c, d])

        lookup = ExpressionParameters([e])
        self.assertEqual([], lookup.get_params(e))
        self.assertEqual([Param('a', Param.OUT, _Integer())], lookup.get_params(a))
        self.assertEqual([Param('a', Param.OUT, _Integer())], lookup.get_params(c))
        self.assertEqual([Param('a', Param.IN, _Integer())], lookup.get_params(b))
        self.assertEqual([Param('c.a', Param.IN, _Integer())], lookup.get_params(d))
        self.assertEqual([Local('c.a', _Integer())], lookup.get_locals(e))
        self.assertEqual([], lookup.get_locals(c))

        self.assertTrue(lookup.is_value_referenced(a))

        self.assertEqual([Param('a', Param.IN, _Integer())],
                list(lookup.get_passed_variables(c, c.children[1])))
        self.assertEqual([Param('c.a', Param.IN, _Integer())],
                list(lookup.get_passed_variables(e, e.children[1])))

    def test_length_and_value_reference(self):
        # Test a length reference and a value reference to the same entry.
        a = Field('a', length=8)
        c = Field('c', length=parse('len{a}'))
        d = Field('d', length=parse('${a}'))
        b = Sequence('b', [a, c, d])

        # Lets just try a quick decode to make sure we've specified it ok...
        #list(b.decode(Data('\x08cd')))

        # Now test the parameters being passed around.
        lookup = ExpressionParameters([b])
        self.assertEqual([Param('a', Param.OUT, _Integer()),
            Param('a length', Param.OUT, _Integer())],
                lookup.get_params(a))
        self.assertEqual([Param('a', Param.OUT, _Integer()),
            Param('a length', Param.OUT, _Integer())],
                list(lookup.get_passed_variables(b, b.children[0])))
        self.assertEqual([Param('a length', Param.IN, _Integer())],
                list(lookup.get_passed_variables(b, b.children[1])))
        self.assertEqual([Param('a length', Param.IN, _Integer())],
                lookup.get_params(c))
        self.assertEqual([Local('a', _Integer()), Local('a length', _Integer())],
                lookup.get_locals(b))
        self.assertTrue(lookup.is_length_referenced(a))

    def test_common_entry_with_input_parameter(self):
        # Test that we correctly resolve a common entry that has an input
        # parameter that resolves to mulitiple (different) entries.
        a = Field('a', length=parse('${b}'))

        # Here the common entry 'a' is used into two locations, each time it
        # resolves to an entry with a different length.
        c = Sequence('c', [Field('b', 8), a])
        d = Sequence('d', [Field('b', 16), a])
        lookup = ExpressionParameters([a, c, d])

        self.assertEqual([Param('b', Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[0])))
        self.assertEqual([Param('b', Param.OUT, _Integer())], list(lookup.get_passed_variables(d, d.children[0])))

    def test_unused_parameters_with_same_name(self):
        # Test that when we have multiple 'unused' parameters with the same
        # name we don't duplicate the same local variable. This happened with
        # the vfat specification (the different bootsector types all had the
        # same output parameters).
        a1 = Field('a', length=16)
        a2 = Field('a', length=8)
        # C doesn't use the outputs from a1 and a2, so should have a single
        # local variable.
        c = Sequence('c', [a1, a2])
        # Now create a couple of other entries that actually use a1 & a2
        d1 = Sequence('d1', [a1, Field('e1', length=parse('${a}'))])
        d2 = Sequence('d2', [a2, Field('e2', length=parse('${a}'))])

        lookup = ExpressionParameters([a1, a2, c, d1, d2])
        self.assertEqual([Param('unused a', Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[0])))
        self.assertEqual([Param('unused a', Param.OUT, _Integer())], list(lookup.get_passed_variables(c, c.children[1])))
        self.assertEqual([Local('unused a', _Integer())], lookup.get_locals(c))

    def test_sequence_with_referenced_value(self):
        a = Field('a', length=8)
        b = Sequence('b', [Child('b:', a)], value=parse('${b:}'))
        c = Field('c', length=parse('${b} * 8'))
        d = Sequence('d', [a, b, c])
        lookup = ExpressionParameters([a, d])
        self.assertEqual([Local('b:', _Integer())], lookup.get_locals(b))
        self.assertEqual([Param('a', Param.OUT, _Integer())], lookup.get_params(a))
        self.assertEqual([Param('b', Param.OUT, _Integer())], lookup.get_params(b))
        self.assertEqual([Param('b', Param.IN, _Integer())], lookup.get_params(c))
        self.assertEqual([], lookup.get_params(d))

    def test_exception_when_referencing_text_field(self):
        a = Sequence('a', [Field('b', length=8, format=Field.TEXT),
            Field('c', length=parse('${b}'))])
        self.assertRaises(BadReferenceTypeError, ExpressionParameters, [a])

    def test_recursive_entry_with_input_param(self):
        # There was a bug with passing input parameters to recursive entries,
        # where the embedded (recursed) entry wouldn't have the parameter
        # correctly passed. This technique is used in the asn.1 decoder.
        a = Choice('a', [
            Field('not recursive', length=8, constraints=[Equals(ValueResult('zero'))]),
            Sequence('recursive', [
                Field('unused', length=8)
                ])
            ])
        a.children[1].entry.children.append(Child('a', a))
        b = Sequence('b', [
            Sequence('zero', [], value=Constant(0)),
            a
            ])

        lookup = ExpressionParameters([a, b])
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a, a.children[1])))
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a.children[1].entry, a.children[1].entry.children[1])))

    def test_two_recursive_entries_with_input_parameters(self):
        # The previous fix for recursive parameters didn't handle two
        # structures that were recursive using the same intermediate instance.
        #
        # In this case, 'a' is recursive through both 'recursive x' and
        # 'recursive y', and the bug was that any input parameters to
        # 'recursive y' weren't being correctly detected.
        a = Choice('a', [
            Field('not recursive', length=8, constraints=[Equals(ValueResult('zero'))]),
            Sequence('recursive x', [
                Field('unused', length=8, constraints=[Maximum(10)])
                ]),
            Sequence('recursive y', [
                Field('unused', length=8)
                ]),
            ])
        a.children[1].entry.children.append(Child('a1', a))
        a.children[2].entry.children.append(Child('a2', a))
        b = Sequence('b', [
            Sequence('zero', [], value=Constant(0)),
            a
            ])

        lookup = ExpressionParameters([a, b])
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a, a.children[1])))
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a.children[1].entry, a.children[1].entry.children[1])))
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a, a.children[2])))
        self.assertEqual([
            Param('zero', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a.children[2].entry, a.children[2].entry.children[1])))

    def test_same_param_from_parent_and_siblings(self):
        # Test that we ask the parent for a parameter even when there is a
        # child with the same name (but _after_ the entry that needs it).
        a = Sequence('a', [
            Sequence('expected', [], value=Constant(2)),
            Sequence('b', [
                # This should come from the parent (ie: a.expected)
                Field('c', length=8, constraints=[Equals(ValueResult('expected'))]),
                Sequence('expected', [], value=Constant(1)),
                # This should come from the sibling (ie: b.expected)
                Field('d', length=8, constraints=[Equals(ValueResult('expected'))]),
                ])
            ])
        b = a.children[1].entry
        lookup = ExpressionParameters([a])
        self.assertEqual([Param('expected', Param.IN, _Integer())],
            list(lookup.get_passed_variables(a, a.children[1])))
        self.assertEqual([Param('expected', Param.OUT, _Integer())],
            list(lookup.get_passed_variables(b, b.children[1])))
        self.assertEqual([Param('expected', Param.IN, _Integer())],
            list(lookup.get_passed_variables(b, b.children[2])))

        self.assertRaises(bdec.DecodeError, list, a.decode(Data('\x01\x01')))
        self.assertRaises(bdec.DecodeError, list, a.decode(Data('\x02\x00')))
        list(a.decode(Data('\x02\x01')))

    def test_param_length_postfix(self):
        # Test that a 'length:' postfix doesn't confuse the parameter
        # detection. There was a bug where the types would get confused if
        # both the length and value of an entry ending in ' length:' were
        # referenced.
        a = Sequence('a', [
            Field('b length:', 8),
            Field('b', length=parse('${b length:}'), format=Field.TEXT),
            Sequence('c', [], value=parse('len{b length:} + len{b}')),
            ])
        lookup = ExpressionParameters([a])
        self.assertEqual([
            Param('b length:', Param.OUT, EntryValueType(a.children[0].entry)),
            Param('b length: length', Param.OUT, EntryLengthType(a.children[0].entry))],
            list(lookup.get_passed_variables(a, a.children[0])))
        self.assertEqual([
            Param('b length', Param.OUT, EntryLengthType(a.children[1].entry)),
            Param('b length:', Param.IN, EntryValueType(a.children[0].entry))],
            list(lookup.get_passed_variables(a, a.children[1])))
        self.assertEqual([
            Param('b length', Param.IN, EntryLengthType(a.children[1].entry)),
            Param('b length: length', Param.IN, EntryLengthType(a.children[0].entry))],
            list(lookup.get_passed_variables(a, a.children[2])))


class TestEndEntryParameters(unittest.TestCase):
    def test_end_entry_lookup(self):
        null = Field("null", 8, constraints=[Equals(Data('\x00'))])
        char = Field("char", 8)
        entry = Choice('entry', [null, char])
        string = SequenceOf("null terminated string", entry, None, end_entries=[null])

        lookup = EndEntryParameters([string])
        self.assertEqual(set([Param('should end', Param.OUT, ShouldEndType())]), lookup.get_params(null))
        self.assertEqual(set([Param('should end', Param.OUT, ShouldEndType())]), lookup.get_params(entry))
        self.assertEqual([Local('should end', _Integer())], lookup.get_locals(string))
        self.assertTrue(lookup.is_end_sequenceof(null))

class TestResultParameters(unittest.TestCase):
    def test_field_output(self):
        a = Field('a', 8)
        b = Sequence('b', [a])
        lookup = ResultParameters([b])
        self.assertEqual([Param('result', Param.OUT, EntryType(a))], lookup.get_params(a))
        self.assertEqual([Param('magic unknown param', Param.OUT, EntryType(a))], lookup.get_passed_variables(b, b.children[0]))
        self.assertEqual([Param('result', Param.OUT, EntryType(b))], lookup.get_params(b))

    def test_hidden_field(self):
        a = Field('', 8)
        lookup = ResultParameters([a])
        self.assertEqual([], lookup.get_params(a))

    def test_hidden_entry_visible_child(self):
        # If an entry is hidden, but it has visible children, we want the entry
        # to be hidden regardless.
        a = Field('a', 8)
        b = Sequence('', [a])
        lookup = ResultParameters([b])
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([], lookup.get_params(a))

    def test_recursive_common(self):
        # Test a recursive parser to decode xml style data

        embedded = Sequence('embedded', [])
        digit = Field('data', 8, constraints=[Minimum(ord('0')), Maximum(ord('9'))])
        item = Choice('item', [embedded, digit])
        embedded.children = [
                Field('', length=8, format=Field.TEXT, constraints=[Equals('<')]),
                item,
                Field('', length=8, format=Field.TEXT, constraints=[Equals('>')])]

        # Lets just test that we can decode things correctly...
        list(item.decode(Data('8')))
        list(item.decode(Data('<5>')))
        list(item.decode(Data('<<7>>')))
        self.assertRaises(bdec.DecodeError, list, item.decode(Data('a')))
        self.assertRaises(bdec.DecodeError, list, item.decode(Data('<5')))

        lookup = ResultParameters([item])
        self.assertEqual([Param('result', Param.OUT, EntryType(item))], lookup.get_params(item))
        self.assertEqual([Param('result', Param.OUT, EntryType(embedded))], lookup.get_params(embedded))

    def test_hidden_reference(self):
        # Test a visible common reference that is hidden through its reference
        # name. This is common for integers defined at the common level.
        #
        # Note that in this case 'b' won't have an output, because all of the
        # fields it defines are hidden, and so doesn't have a type itself.
        a = Field('a', 8, Field.INTEGER)
        b = Sequence('b', [Child('a:', a)])
        lookup = ResultParameters([a, b])
        self.assertEqual([Param('result', Param.OUT, EntryType(a))], lookup.get_params(a))
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([Local('unused a:', EntryType(a))], lookup.get_locals(b))
        self.assertEqual([Param('unused a:', Param.OUT, EntryType(a))], lookup.get_passed_variables(b, b.children[0]))

    def test_sequence_value(self):
        a = Field('a:', 8, Field.INTEGER)
        b = Sequence('b', [a], parse('${a:}'))
        lookup = ResultParameters([b])
        self.assertEqual([], lookup.get_params(a))
        self.assertEqual([Param('result', Param.OUT, EntryType(b))],
                lookup.get_params(b))
        self.assertEqual([], lookup.get_locals(a))
        self.assertEqual([], lookup.get_locals(b))
        self.assertEqual([], lookup.get_passed_variables(b, b.children[0]))

    def test_visible_common_in_hidden_context(self):
        a = Field('a', 8)
        b = Sequence('b:', [a])
        lookup = ResultParameters([a, b])
        self.assertEqual([Param('result', Param.OUT, EntryType(a))],
                lookup.get_params(a))
        self.assertEqual([], lookup.get_params(b))
        self.assertEqual([Local('unused a', EntryType(a))], lookup.get_locals(b))
        self.assertEqual([Param('unused a', Param.OUT, EntryType(a))],
            lookup.get_passed_variables(b, b.children[0]))


class TestDataChecker(unittest.TestCase):
    def test_hidden_entry_visible_child(self):
        # Test that when the parent entry is hidden, the child entry is hidden
        # too.
        a = Field('a', 8)
        b = Sequence('b:', [a])
        checker = DataChecker([b])
        self.assertFalse(checker.contains_data(a))
        self.assertFalse(checker.contains_data(b))
        self.assertFalse(checker.child_has_data(b.children[0]))

    def test_visible_child_renamed_to_be_hidden(self):
        # Test that when a child is visible, but its name isn't, the parent
        # can be hidden.
        a = Field('a', 8)
        b = Sequence('b', [Child('a:', a)])
        checker = DataChecker([a, b])
        self.assertTrue(checker.contains_data(a))
        self.assertFalse(checker.contains_data(b))


class TestEncodeParameters(unittest.TestCase):
    def test_referenced_renamed_child(self):
        # Here 'a' is a common entry (as it has been renamed). The visible
        # 'a' entry should have an output parameter 'a', but 'c' should also
        # have it as an output; 'b' will be responsible for mocking the
        # parameter to pass into 'a:' during encoding.
        a = Field('a', 8)
        b = Sequence('b', [
            Child('a:', a),
            Sequence('c', [], value=parse('${a:}'))])
        params = EncodeExpressionParameters([a, b])
        self.assertEqual([Param('a', Param.OUT, _Integer())], params.get_params(a))
        self.assertEqual([Param('a:', Param.OUT, _Integer())], params.get_passed_variables(b, b.children[0]))
        self.assertEqual([Param('a:', Param.OUT, _Integer())], params.get_params(b.children[1].entry))
