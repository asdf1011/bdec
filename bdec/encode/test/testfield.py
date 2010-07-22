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

from bdec.entry import Child
from bdec.expression import parse
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.output.instance import encode

class TestField(unittest.TestCase):
    def test_integer_with_fixed_length_reference(self):
        # This sort of a construct is used in the presense specifications
        a = Sequence('a', [
            Sequence('length:', [], value=parse('16')),
            Field('b:', format=Field.INTEGER, length=parse('${length:}'))],
            value=parse('${b:}'))
        self.assertEqual('\x00\x00', encode(a, 0).bytes())
        self.assertEqual('\x00\xff', encode(a, 255).bytes())
        self.assertEqual('\xff\xff', encode(a, 65535).bytes())

    def test_integer_with_variable_length(self):
        a = Sequence('a', [
            Field('length:', length=8 ),
            Field('b:', format=Field.INTEGER, length=parse('${length:} * 8'))],
            value=parse('${b:}'))
        self.assertEqual('\x01\x00', encode(a, 0).bytes())
        self.assertEqual('\x01\xff', encode(a, 255).bytes())
        self.assertEqual('\x02\xff\xff', encode(a, 65535).bytes())

    def test_sometimes_referenced_hidden_field(self):
        # Test encoding a field that is sometimes referenced (but not always).
        a = Field('a:', length=8, format=Field.INTEGER)
        b = Sequence('b', [a], value=parse('${a:}'))
        c = Sequence('c', [a, b])
        self.assertEqual('\x00\x07', encode(c, {'b':7}).bytes())

    def test_encode_zero_length_field(self):
        a = Sequence('a', [
                Field('b:', length=8),
                Field('c', format=Field.TEXT, length=parse('${b:} * 8'))
                ])
        self.assertEqual('\x02ab', encode(a, {'c':'ab'}).bytes())
        self.assertEqual('\x00', encode(a, {'c':''}).bytes())
