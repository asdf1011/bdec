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
from bdec.expression import parse
from bdec.field import Field
from bdec.inspect.param import ExpressionParameters
from bdec.inspect.solver import solve
from bdec.inspect.type import EntryValueType
from bdec.sequence import Sequence

def _solve(entry, child, value):
    result = solve(entry.children[child].entry.value, entry,
            ExpressionParameters([entry]), value)
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

