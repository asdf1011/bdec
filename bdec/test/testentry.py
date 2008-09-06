#   Copyright (C) 2008 Henry Ludemann
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

import bdec.entry


class TestRange(unittest.TestCase):
    def test_adding_zero_length_range(self):
        a = bdec.entry.Range(0, 0)
        b = bdec.entry.Range(0, 0)
        c = a + b
        self.assertEqual(0, c.min)
        self.assertEqual(0, c.max)
        
    def test_adding_max(self):
        a = bdec.entry.Range(10, 10)
        b = bdec.entry.Range()
        c = a + b
        self.assertEqual(10, c.min)
        self.assertEqual(c.MAX, c.max)

    def test_adding_ranges(self):
        a = bdec.entry.Range(10, 20)
        b = bdec.entry.Range(0, 5)
        c = a + b
        self.assertEqual(10, c.min)
        self.assertEqual(25, c.max)
