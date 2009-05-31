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
from bdec.inspect.type import _range, Range, EntryValueType, EntryLengthType, \
        MultiSourceType
from bdec.sequence import Sequence
import unittest

class TestRange(unittest.TestCase):

    def test_union_with_none(self):
        a = Range(None, None)
        b = Range(0, 10)
        self.assertEqual(Range(None, None), a.union(b))

    def test_intersect_with_none(self):
        a = Range(None, None)
        b = Range(0, 10)
        self.assertEqual(Range(0, 10), a.intersect(b))

    def test_add(self):
        a = Range(10, 20)
        b = Range(-5, 10)
        self.assertEqual(Range(5, 30), a + b)
        self.assertEqual(Range(5, 30), b + a)

    def test_add_none(self):
        a = Range(10, 20)
        b = Range(-5, None)
        self.assertEqual(Range(5, None), a + b)
        self.assertEqual(Range(5, None), b + a)

    def test_subtract(self):
        a = Range(100, 150)
        b = Range(0, 10)
        self.assertEqual(Range(90, 150), a - b)
        self.assertEqual(Range(-150, -90), b - a)

    def test_subtract_none(self):
        a = Range(100, None)
        b = Range(5, 10)
        self.assertEqual(Range(90, None), a - b)
        self.assertEqual(Range(None, -90), b - a)

    def test_multiply(self):
        a = Range(2, 3)
        b = Range(10, 11)
        self.assertEqual(Range(20, 33), a * b)

    def test_multiply_no_max(self):
        a = Range(2, 3)
        b = Range(10, None)
        self.assertEqual(Range(20, None), a * b)

    def test_multiply_negative(self):
        a = Range(2, 3)
        b = Range(-7, -5)
        self.assertEqual(Range(-21, -10), a * b)
        self.assertEqual(Range(-21, -10), b * a)

    def test_multiply_two_negatives(self):
        a = Range(-2, -3)
        b = Range(-7, -5)
        self.assertEqual(Range(10, 21), a * b)
        self.assertEqual(Range(10, 21), b * a)

    def test_multiply_no_min(self):
        a = Range(2, 5)
        b = Range(None, 10)
        self.assertEqual(Range(None, 50), a * b)
        self.assertEqual(Range(None, 50), b * a)

    def test_divide(self):
        a = Range(40, 80)
        b = Range(1, 8)
        self.assertEqual(Range(5, 80), a / b)

    def test_divide_zero(self):
        a = Range(40, 80)
        b = Range(0, 8)
        self.assertEqual(Range(5, None), a / b)

    def test_divide_ininite_by_infite(self):
        a = Range(None, None)
        b = Range(None, None)
        self.assertEqual(Range(None, None), a / b)


class TestExpressionRange(unittest.TestCase):

    def test_constant_range(self):
        a = compile('8')
        self.assertEqual(8, _range(a).min)
        self.assertEqual(8, _range(a).max)

    def test_multiple_range(self):
        a = compile('8 * 1 * 4')
        self.assertEqual(32, _range(a).min)
        self.assertEqual(32, _range(a).max)

    def test_divide_range(self):
        a = compile('16 / 2 / 4')
        self.assertEqual(2, _range(a).min)
        self.assertEqual(2, _range(a).max)

    def test_mod_range(self):
        a = compile('100 % 2')
        self.assertEqual(0, _range(a).min)
        self.assertEqual(1, _range(a).max)

    def test_add_range(self):
        a = compile('(10 + 3) + 7')
        self.assertEqual(20, _range(a).min)
        self.assertEqual(20, _range(a).max)

    def test_subtract_range(self):
        a = compile('95 - (100 - 20)')
        self.assertEqual(15, _range(a).min)
        self.assertEqual(15, _range(a).max)


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
