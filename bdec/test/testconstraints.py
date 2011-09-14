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

from bdec.constraints import Minimum, Maximum, Equals
from bdec.field import Field
from bdec import DecodeError

class TestConstraint(unittest.TestCase):
    def test_minimum(self):
        field = Field('a', 8)
        min = Minimum(8)
        min.check(field, 8, {})
        min.check(field, 9, {})
        try:
           min.check(field, 7, {})
           raise Exception('Minimum constraint failed!')
        except DecodeError, ex:
           expected = "Expected ${a} >= 8; got 7"
           self.assertEqual(expected, str(ex)) 

    def test_maximum(self):
        field = Field('a', 8)
        min = Maximum(8)
        min.check(field, 7, {})
        min.check(field, 8, {})
        try:
           min.check(field, 9, {})
           raise Exception('Maximum constraint failed!')
        except DecodeError, ex:
           expected = "Expected ${a} <= 8; got 9"
           self.assertEqual(expected, str(ex)) 

    def test_equals(self):
        field = Field('a', 8)
        min = Equals('cat')
        min.check(field, 'cat', {})
        try:
            min.check(field, 'dog', {})
            raise Exception('Maximum constraint failed!')
        except DecodeError, ex:
            expected = "Expected ${a} == cat; got dog"
            self.assertEqual(expected, str(ex)) 
