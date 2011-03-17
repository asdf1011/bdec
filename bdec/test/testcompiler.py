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

import bdec.compiler as comp
import bdec.field as fld
import bdec.sequence as seq

class _Settings:
    def __init__(self):
        self.keywords = []

class TestUtils(unittest.TestCase):
    def test_is_not_recursive(self):
        a = fld.Field('a', 8)
        b = fld.Field('b', 8)
        utils = comp._Utils([a, b], {})
        self.assertTrue(not utils.is_recursive(a, b))

    def test_is_recursive(self):
        a = seq.Sequence('a', [])
        b = seq.Sequence('b', [a])
        c = fld.Field('c', 8)
        d = seq.Sequence('d', [b, c])
        a.children = [d]
        utils = comp._Utils([a], {})
        self.assertTrue(utils.is_recursive(a, d))
        self.assertTrue(utils.is_recursive(b, a))
        self.assertTrue(utils.is_recursive(d, b))
        self.assertTrue(not utils.is_recursive(d, c))

    def test_name_escaping(self):
        names = ['a', 'a', 'a1', 'A', 'a:']
        utils = comp._Utils([], _Settings())
        escaped = utils.esc_names(names, utils.variable_name)
        self.assertEqual(['a0', 'a1', 'a10', 'a2', 'a3'], escaped)

    def test_constant_name_escaping(self):
        names = ['a', 'a', 'a 0', 'A', 'a:']
        utils = comp._Utils([], _Settings())
        escaped = utils.esc_names(names, utils.constant_name)
        self.assertEqual(['A_0', 'A_1', 'A_0_0', 'A_2', 'A_3'], escaped)

