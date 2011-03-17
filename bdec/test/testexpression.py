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

from bdec import DecodeError
from bdec.data import Data
import bdec.expression as exp
import bdec.sequence as sequence
import unittest

def eval(text):
    return exp.compile(text).evaluate({})

def bool(text,context={}):
    try:
        # If the object decodes, the conditional is false
        conditional = exp.parse_conditional_inverse(text)

        # If the expression needs context to decode, it'll need to be able to
        # reference other entries, so create them here...
        children = []
        for name, value in context.items():
            children.append(sequence.Sequence(name, [], value=exp.Constant(value)))
        children.append(conditional)
        list(sequence.Sequence('', children).decode(Data()))
        return False
    except DecodeError,ex:
        return True

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

    def test_shift_left(self):
        self.assertEqual(256, eval("2 - 1 << 8"))
        self.assertEqual(16, eval("1 << 4"))
        self.assertEqual(1, eval("1 << 0"))

    def test_shift_right(self):
        self.assertEqual(1, eval("200 + 56 >> 8"))
        self.assertEqual(8, eval("8 * 1 >> 0"))
        self.assertEqual(2, eval("8 / 1 >> 2"))

class TestBoolean(unittest.TestCase):
    def test_greater_equal(self):
        self.assertEqual(True, bool("5 >= 3"))
        self.assertEqual(True, bool("3 >= 3"))
        self.assertEqual(False, bool("2 >= 3"))

    def test_greater(self):
        self.assertEqual(True, bool("5 > 3"))
        self.assertEqual(False, bool("3 > 3"))
        self.assertEqual(False, bool("2 > 3"))

    def test_lesser(self):
        self.assertEqual(False, bool("5 < 3"))
        self.assertEqual(False, bool("3 < 3"))
        self.assertEqual(True, bool("2 < 3"))

    def test_lesser_equal(self):
        self.assertEqual(False, bool("5 <= 3"))
        self.assertEqual(True, bool("3 <= 3"))
        self.assertEqual(True, bool("2 <= 3"))

    def test_equals(self):
        self.assertEqual(True, bool('5 == 5'))
        self.assertEqual(False, bool('5 == 4'))
        self.assertEqual(True, bool('11 - 1 == 5 * 2'))

    def test_not_equals(self):
        self.assertEqual(False, bool('5 != 5'))
        self.assertEqual(True, bool('5 != 4'))
        self.assertEqual(True, bool('5 != 5 - 1'))

    def test_and(self):
        self.assertEqual(True, bool('5 == (1+4) && 3 > 2'))
        self.assertEqual(False, bool('5 != (1+4) && 3 > 2'))
        self.assertEqual(False, bool('5 == (1+4) && 3 > 4'))
        self.assertEqual(True, bool('1==1 && 1==1 && 1==1 && 1==1'))
        self.assertEqual(False, bool('1==1 && 1==1 && 1==1 && 0==1'))
        self.assertEqual(False, bool('5 == (1+4) and 3 > 4'))

    def test_or(self):
        self.assertEqual(True, bool('5 == (1+4) || 3 > 2'))
        self.assertEqual(True, bool('5 != (1+4) || 3 > 2'))
        self.assertEqual(True, bool('5 == (1+4) or 3 > 4'))
        self.assertEqual(False, bool('5 != (1+4) || 3 > 4'))
        self.assertEqual(True, bool('0==1 or 0==1 or 0==1 or 0==0'))
        self.assertEqual(False, bool('0==1 or 0==1 or 0==1 or 0>=1'))

    def test_implicit_conversion(self):
        self.assertEqual(True, bool('${bob}', {'bob':1}))
        self.assertEqual(True, bool('0 or ${bob}', {'bob':1}))
        self.assertEqual(False, bool('0 or ${bob}', {'bob':0}))

