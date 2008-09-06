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

import bdec.spec.expression as exp
import unittest

def eval(text):
    return exp.compile(text).evaluate({})

class TestExpression(unittest.TestCase):
    def test_simple_int(self):
        self.assertEqual(5, eval('5'))

    def test_add(self):
        self.assertEqual(8, eval('5 + 3'))

    def test_sub(self):
        self.assertEqual(2, eval('8 - 6'))

    def test_compound(self):
        self.assertEqual(12, eval('6 + 7 - 1'))

    def test_brackets(self):
        self.assertEqual(6, eval('(6)'))
        self.assertEqual(7, eval('(6 + 1)'))
        self.assertEqual(7, eval('(6) + 1'))
        self.assertEqual(4, eval('1 + (5 - 2)'))

    def test_multiply(self):
        self.assertEqual(8, eval('4 * 2'))

    def test_divide(self):
        self.assertEqual(7, eval('14 / 2'))

    def test_mod(self):
        self.assertEqual(2, eval('8 % 3'))

    def test_bimdas(self):
        self.assertEqual(25, eval('5 + 2 * 10'))
        self.assertEqual(70, eval('(5 + 2) * 10'))

    def test_named_reference(self):
        a = exp.compile('${bob}')
        self.assertTrue(isinstance(a, exp.ValueResult))
        self.assertEquals('bob', a.name)

    def test_length_lookup(self):
        a = exp.compile('len{bob}')
        self.assertTrue(isinstance(a, exp.LengthResult))
        self.assertEquals('bob', a.name)

    def test_hex(self):
        self.assertEqual(5, eval("0x5"))
        self.assertEqual(255, eval("0xfF"))
