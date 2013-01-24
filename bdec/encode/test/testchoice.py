#   Copyright (C) 2012 Henry Ludemann
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
from bdec.constraints import Equals
from bdec.data import Data
from bdec.entry import Entry, Child
from bdec.expression import ValueResult, Constant
from bdec.field import Field
from bdec.output.instance import encode
from bdec.sequence import Sequence
import unittest

class TestChoice(unittest.TestCase):

    def test_default_value_of_variable_length_field(self):
        # When encoding 'd' we should choose a suitable value for the unknown
        # output reference 'number'. As we know it's not zero (as that was
        # used by the 'c' option), we expect the next digit (one).
        number = Sequence('number', [
                Field('integer length:', length=8),
                Field('value:', format=Field.INTEGER, length=ValueResult('integer length:') * Constant(8)) ],
                value=ValueResult('value:'))
        a = Sequence('a', [
            Child('number:', number),
            Choice('data', [
                Sequence('c', [], value=ValueResult('number:'), constraints=[Equals(0)]),
                Sequence('d', [])])
            ])
        self.assertEqual(Data('\x01\x00'), encode(a, {'c':0}))
        self.assertEqual(Data('\x01\x01'), encode(a, {'d':None}))
