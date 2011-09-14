#   Copyright (C) 2010 Henry Ludemann
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

import unittest
from bdec.inspect.range import Range, Ranges

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

    def test_mod(self):
        a = Range(10, 20)
        b = Range(1, 8)
        self.assertEqual(Range(0, 7), a % b)

    def test_mod_none(self):
        a = Range(10, 20)
        b = Range(0, None)
        self.assertEqual(Range(0, 20), a % b)

    def test_shift_left(self):
        a = Range(0, 8)
        b = Range(5, 5)
        self.assertEqual(Range(0, 256), a << b)

    def test_shift_right(self):
        a = Range(256, 256)
        b = Range(5, 5)
        self.assertEqual(Range(8, 8), a >> b)

        a = Range(256, 256)
        c = Range(0, 5)
        self.assertEqual(Range(8, 256), a >> c)

    def test_large_multiply(self):
        a = Range(0, 999999999)
        b = Range(100, 100)
        self.assertEqual(Range(0, 99999999900), a * b)


class TestRanges(unittest.TestCase):
    def test_initialise(self):
        r = Ranges([Range(0, 10), Range(5, 15)])
        self.assertEqual([Range(0, 15)], r.get_ranges())

    def test_add_at_end(self):
        r = Ranges([Range(0, 10)])
        r.add(Range(15, 20))
        self.assertEqual([Range(0, 10), Range(15, 20)], r.get_ranges())

    def test_add_at_start(self):
        r = Ranges([Range(15, 20)])
        r.add(Range(5, 10))
        self.assertEqual([Range(5, 10), Range(15, 20)], r.get_ranges())

    def test_add_overlapping_in_middle(self):
        r = Ranges([Range(0, 10), Range(15, 20)])
        r.add(Range(10, 15))
        self.assertEqual([Range(0, 20)], r.get_ranges())

    def test_add_middle_no_overlap(self):
        r = Ranges([Range(0, 10), Range(15, 20)])
        r.add(Range(12, 13))
        self.assertEqual([Range(0, 10), Range(12, 13), Range(15, 20)], r.get_ranges())

    def test_add_infinite_right(self):
        r = Ranges([Range(0, 10), Range(15, 20)])
        r.add(Range(5, None))
        self.assertEqual([Range(0, None)], r.get_ranges())

    def test_add_infinite_left(self):
        r = Ranges([Range(0, 10), Range(15, 20)])
        r.add(Range(None, 16))
        self.assertEqual([Range(None, 20)], r.get_ranges())

    def test_remove_from_left(self):
        r = Ranges([Range(10, 20)])
        r.remove(Range(5, 15))
        self.assertEqual([Range(16, 20)], r.get_ranges())

    def test_remove_from_right(self):
        r = Ranges([Range(10, 20)])
        r.remove(Range(15, 25))
        self.assertEqual([Range(10, 14)], r.get_ranges())

    def test_remove_past_max(self):
        r = Ranges([Range(10, 20)])
        r.remove(Range(25, 30))
        self.assertEqual([Range(10, 20)], r.get_ranges())

    def test_remove_before_min(self):
        r = Ranges([Range(10, 20)])
        r.remove(Range(0, 8))
        self.assertEqual([Range(10, 20)], r.get_ranges())

    def test_remove_from_middle(self):
        r = Ranges([Range(10, 20)])
        r.remove(Range(15, 15))
        self.assertEqual([Range(10, 14), Range(16, 20)], r.get_ranges())

    def test_remove_all(self):
        r = Ranges([Range(5, 10), Range(20, 25)])
        r.remove(Range(None, None))
        self.assertEqual([], r.get_ranges())

