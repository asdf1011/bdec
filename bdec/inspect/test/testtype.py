#   Copyright (C) 2009 Henry Ludemann
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


from bdec.choice import Choice
from bdec.constraints import Minimum, Maximum, Equals
from bdec.expression import compile
from bdec.field import Field
from bdec.inspect.param import ExpressionParameters
from bdec.inspect.type import expression_range, Range, EntryValueType, EntryLengthType, \
        MultiSourceType
from bdec.sequence import Sequence
import unittest


class TestExpressionRange(unittest.TestCase):

    def test_constant_range(self):
        a = compile('8')
        self.assertEqual(8, expression_range(a).min)
        self.assertEqual(8, expression_range(a).max)

    def test_multiple_range(self):
        a = compile('8 * 1 * 4')
        self.assertEqual(32, expression_range(a).min)
        self.assertEqual(32, expression_range(a).max)

    def test_divide_range(self):
        a = compile('16 / 2 / 4')
        self.assertEqual(2, expression_range(a).min)
        self.assertEqual(2, expression_range(a).max)

    def test_mod_range(self):
        a = compile('100 % 2')
        self.assertEqual(Range(0, 1), expression_range(a))

    def test_add_range(self):
        a = compile('(10 + 3) + 7')
        self.assertEqual(20, expression_range(a).min)
        self.assertEqual(20, expression_range(a).max)

    def test_subtract_range(self):
        a = compile('95 - (100 - 20)')
        self.assertEqual(15, expression_range(a).min)
        self.assertEqual(15, expression_range(a).max)


class TestTypeRange(unittest.TestCase):

    def test_field_range(self):
        a = Field('a', length=8)
        params = ExpressionParameters([a])
        range = EntryValueType(a).range(params)
        self.assertEqual(0, range.min)
        self.assertEqual(255, range.max)

    def test_constraints(self):
        a = Field('a', length=8, constraints=[Minimum(40), Maximum(48)])
        params = ExpressionParameters([a])
        range = EntryValueType(a).range(params)
        self.assertEqual(40, range.min)
        self.assertEqual(48, range.max)

    def test_length_range(self):
        a = Field('a', length=8)
        params = ExpressionParameters([a])
        range = EntryLengthType(a).range(params)
        self.assertEqual(8, range.min)
        self.assertEqual(8, range.max)

    def test_referenced_field_value(self):
        a = Field('a', length=4)
        b = Sequence('b', [], value=compile('${a} * 8'))
        c = Sequence('c', [a, b])
        params = ExpressionParameters([c])
        range = EntryValueType(b).range(params)
        self.assertEqual(0, range.min)
        self.assertEqual(15 * 8, range.max)

    def test_referenced_field_length(self):
        a = Field('a', length=4)
        b = Sequence('b', [], value=compile('len{a} * 8 + 4'))
        c = Sequence('c', [a, b])
        params = ExpressionParameters([c])
        range = EntryValueType(b).range(params)
        self.assertEqual(36, range.min)
        self.assertEqual(36, range.max)

    def test_multi_source_range(self):
        a = Field('a', length=8, constraints=[Minimum(5), Maximum(10)])
        b = Field('b', length=8, constraints=[Minimum(20), Maximum(30)])
        range = MultiSourceType([EntryValueType(a), EntryValueType(b)]).range(None)
        self.assertEqual(5, range.min)
        self.assertEqual(30, range.max)

    def test_choice_value_range(self):
        a = Field('a', length=8, constraints=[Minimum(5), Maximum(10)])
        b = Field('b', length=8, constraints=[Minimum(20), Maximum(30)])
        c = Choice('c', [a, b])
        range = EntryValueType(c).range(None)
        self.assertEqual(5, range.min)
        self.assertEqual(30, range.max)
