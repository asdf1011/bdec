# Copyright (c) 2010, PRESENSE Technologies GmbH
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the PRESENSE Technologies GmbH nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from bdec.constraints import Minimum, Maximum
from bdec.entry import Child
from bdec.expression import parse
from bdec.field import Field
from bdec.inspect.param import ExpressionParameters
from bdec.inspect.solver import solve, SolverError
from bdec.inspect.type import EntryValueType
from bdec.sequence import Sequence

def _solve(entry, child, value, context=None):
    if context is None:
        context = {}
    ent = entry.children[child].entry if child is not None else entry
    result = solve(ent.value, entry,
            ExpressionParameters([entry]), context, value)
    return dict((str(c), v) for c,v in result.items())


class TestSolver (unittest.TestCase):
    def test_single_value(self):
        # Test when the expression is the value of an entry
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('${b}')),
            ])
        self.assertEqual({'${b}':5}, _solve(a, 1, 5))

    def test_single_value_addition(self):
        # Test that we correctly resolve the correct value when there is an
        # addition involved
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('${b} + 3')),
            ])
        self.assertEqual({'${b}':7}, _solve(a, 1, 10))

    def test_single_value_multiply(self):
        # Test when the expression is the value of an entry multipled by something
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('${b} * 2')),
            ])
        self.assertEqual({'${b}':4}, _solve(a, 1, 8))

    def test_single_value_bimdas(self):
        # Test that we correctly resolve the value when there are addition
        # and multiplication involved.
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('(${b} + 3) * 8')),
            ])
        self.assertEqual({'${b}':5}, _solve(a, 1, 64))

    def test_big_endian(self):
        # Test that we can break apart a big endian style number
        a = Sequence('a', [
            Field('b1', length=8),
            Field('b2', length=8),
            Sequence('c', [], value=parse('(${b1} << 8) + ${b2} ')),
            ])
        self.assertEqual({'${b1}':0x12, '${b2}':0x34}, _solve(a, 2, 0x1234))

    def test_little_endian(self):
        # Test that we can break apart a little endian style number
        a = Sequence('a', [
            Field('b1', length=8),
            Field('b2', length=8),
            Sequence('c', [], value=parse('(${b2} << 8) + ${b1} ')),
            ])
        self.assertEqual({'${b1}':0x34, '${b2}':0x12}, _solve(a, 2, 0x1234))

    def test_same_reference_multiple_times(self):
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('${b} + ${b}')),
            ])
        # TODO: We should correctly be able to invert 'c = b + b'. See issue245.
        #self.assertEqual({'${b}':7}, _solve(a, 1, 14))
        self.assertRaises(SolverError, _solve, a, 1, 14)

    def test_divide(self):
        a = Sequence('a', [
            Field('b', length=8),
            Sequence('c', [], value=parse('${b} / 2')),
            ])
        # TODO: What should we do in this case? This is a lossy conversion... See issue246.
        #self.assertEqual({'${b}':20}, _solve(a, 1, 10))
        self.assertRaises(SolverError, _solve, a, 1, 10)

    def test_digit(self):
        # Tests a common case of representing text digits
        digit = Sequence('digit', [Field('char:', length=8, constraints=[Minimum(48), Maximum(57)])],
                value = parse('${char:} - 48'))
        self.assertEqual({'${char:}':54}, _solve(digit, None, 6))

    def test_two_digits(self):
        # Tests a common case of representing text digits
        digit = Sequence('digit', [Field('char:', length=8, constraints=[Minimum(48), Maximum(57)])],
                value = parse('${char:} - 48'))
        two_digits = Sequence('two digits', [Child('digit 1:', digit),
            Child('digit 2:', digit)], value=parse('${digit 1:} * 10 + ${digit 2:}'))
        self.assertEqual({'${digit 1:}':6, '${digit 2:}' : 7},
                _solve(two_digits, None, 67))

    def test_length_reference(self):
        a = Sequence('a', [
            Field('data length:', length=8),
            Field('b', length=16),
            Sequence('footer length', [], value=parse('${data length:} * 8 - len{b}'))])
        # We now try to solve 'data length:' given that we know the value for 'b length'
        self.assertEqual({'${data length:}' : 5}, _solve(a, 2, 24, {'b length':16}))

    def test_subtract(self):
        a = Sequence('a', [
            Field('total length:', length=8),
            Field('partial length:', length=8),
            Field('data:', length=parse('${partial length:} * 8')),
            Sequence('unused', [], value=parse('${total length:} * 8 - len{data:}')),
            ])
        self.assertEqual({'len{data:}': 800}, _solve(a, 3, 0, {'total length:':100}))

    def test_signed_flag(self):
        a = Sequence('a', [
            Field('signed:', 1),
            Field('value:', 7),
            Sequence('signed char', [], value=parse('(${signed:} * ((0-1) * 128)) + ${value:}'))
            ])
        self.assertEqual({'${signed:}':1, '${value:}':0}, _solve(a, 2, -128))
        self.assertEqual({'${signed:}':1, '${value:}':0x7f}, _solve(a, 2, -1))
        self.assertEqual({'${signed:}':0, '${value:}':0}, _solve(a, 2, 0))
        self.assertEqual({'${signed:}':0, '${value:}':0x7f}, _solve(a, 2, 127))

