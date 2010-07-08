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
from bdec.encode.entry import MissingInstanceError
from bdec.encode.sequence import CyclicEncodingError
from bdec.expression import parse
from bdec.field import Field
from bdec.sequence import Sequence

from bdec.output.instance import encode

class TestSequence(unittest.TestCase):
    def test_encode_reference(self):
        # Test that we correctly encode a reference
        a = Sequence('a', [
            Field("b:", 8, format=Field.INTEGER),
            Sequence('c', [], value=parse('${b:}'))])

        self.assertEqual("\x01", encode(a, {"c" : 0x01}).bytes())

    def test_encode_length_reference(self):
        a = Sequence('a', [
            Field('length:', 8),
            Sequence('payload', [
                Field('data', length=32, format=Field.TEXT)
                ], length=parse("${length:} * 8"))])
        data = {
                'payload':{'data':'abcd'}
                }
        self.assertEqual('\x04abcd', encode(a, data).bytes())

    def test_full_names(self):
        a = Sequence('a', [
            Sequence('b', [Field('length:', length=8)]),
            Sequence('c', [Field('data', length=parse('${b.length:} * 8'), format=Field.TEXT)])])
        self.assertEqual('\x03abc', encode(a, {'b':{}, 'c':{'data':'abc'}}).bytes())

    def test_multi_digit_encode(self):
        # Test encoding a multiple text digit entry
        digit = Sequence('digit',
                [Field('char:', length=8, constraints=[Minimum(48), Maximum(57)])],
                value=parse('${char:} - 48'))
        two_digits = Sequence('two digits', [
            Child('digit 1:', digit), Child('digit 2:', digit)],
            value=parse('${digit 1:} * 10 + ${digit 2:}'))
        four_digits = Sequence('four digits', [
            Child('digits 1:', two_digits), Child('digits 2:', two_digits)],
            value=parse('${digits 1:} * 100 + ${digits 2:}'))

        self.assertEqual('12', encode(two_digits, 12).bytes())
        self.assertEqual('1234', encode(four_digits, 1234).bytes())
        self.assertEqual('7632', encode(four_digits, 7632).bytes())

    def test_encode_hidden_sequence(self):
        # When encoding an item that is hidden, we should use null characters.
        a = Sequence('a', [Sequence('b:', [Field('c', length=8)])])
        self.assertEqual('\x00', encode(a, None).bytes())

    def test_cyclic_dependency_error(self):
        a = Sequence('a', [
            Sequence('header:', [Field('length', length=8)]),
            Field('payload', length=parse('${header:.length} * 8 - len{header:}'), format=Field.TEXT)])
        try:
            encode(a, {'payload':'boom'})
        except CyclicEncodingError, ex:
            self.assertTrue("'header:' -> 'payload' -> 'header:'" in str(ex), str(ex))

    def test_length_reference(self):
        # Test that we can correctly encode entries that use length references
        a = Sequence('a', [
            Field('packet length:', length=8),
            Field('data length:', length=8),
            Field('data', length=parse('${data length:} * 8'), format=Field.TEXT),
            Field('unused', length=parse('${packet length:} * 8 - len{data}'), format=Field.TEXT)])
        self.assertEqual('\x05\x03aaabb', encode(a, {'data':'aaa', 'unused':'bb'}).bytes())

    def test_complex_length_reference(self):
        # Here we try to encode a complex length reference that includes a
        # length reference
        a = Sequence('a', [
            Field('packet length:', length=8, format=Field.INTEGER),
            Field('header length:', length=8, format=Field.INTEGER),
            Field('header', length=parse('${header length:} * 8'), format=Field.TEXT),
            Field('packet', length=parse('${packet length:} * 8 - len{header}'), format=Field.TEXT)])
        self.assertEqual('\x06\x02hhpppp', encode(a, {'header':'hh', 'packet':'pppp'}).bytes())

    def test_common_entry_with_referenced_value(self):
        # Just because an entry is sometimes referenced doesn't mean it always
        # has to be... here we create an element 'a' whose value is only
        # sometimes referenced elsewhere.
        a = Field('a', length=8)
        b = Sequence('b', [Child('a:', a)], value=parse('${a:}'))
        c = Sequence('c', [a, b])
        self.assertEqual('\x45\x23', encode(c, {'a':0x45, 'b':0x23}).bytes())

