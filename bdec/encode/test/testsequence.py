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

from bdec.choice import Choice
from bdec.constraints import Minimum, Maximum, Equals
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
        # This tests that we get a good error when we are unable to encode due
        # to cyclic dependencies. In this case, we cannot encode 'payload' without
        # knowing the length of 'header:', but we cannot encode 'header:'
        # without knowing the length to put in 'header:.length'.
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
        c = Sequence('c', [
            a,
            Sequence('b', [Child('a:', a)], value=parse('${a:}'))])
        self.assertEqual('\x45\x23', encode(c, {'a':0x45, 'b':0x23}).bytes())

    def test_fixed_sequence_value(self):
        # We create an entry with a fixed / visible value, and reference it
        # within a choice when deciding how to encode. This is similar to how
        # the optional big/little endian fields work.
        optional_endian = Sequence('optional_endian', [
            Choice('number:', [
                Sequence('big endian:', [
                    Sequence('big check:', [], value=parse('${is big endian:}'), constraints=[Equals(1)]),
                    Field('internal:', length=16)],
                    value=parse('${internal:}')),
                Sequence('little endian:', [
                    Sequence('little check:', [], value=parse('${is big endian:}'), constraints=[Equals(0)]),
                    Sequence('internal:', [
                        Field('byte 1:', length=8),
                        Field('byte 2:', length=8)],
                        value=parse('(${byte 2:} << 8) + ${byte 1:}'))],
                    value=parse('${internal:}'))])],
            value=parse('${number:}'))

        # Check that we correctly encode when the 'is big endian' is a fixed value
        a = Sequence('a', [
            Sequence('is big endian:', [], value=parse('1')),
            Child('value', optional_endian)])
        self.assertEqual('\x00\x01', encode(a, {'value':1}).bytes())

        b = Sequence('b', [
            Sequence('is big endian:', [], value=parse('0')),
            Child('value', optional_endian)])
        self.assertEqual('\x01\x00', encode(b, {'value':1}).bytes())

        # FIXME: This fails, because the 'number:' decide that as 'is big endian:'
        # is hidden (and doesn't have an expected value) that it must be derived,
        # so changes the 'is big endian:' from an output to an input. See issue247.

        # Check that we correctly encode when the 'is big endian' is a field
        c = Sequence('c', [
            Field('is big endian', length=8, format=Field.INTEGER),
            Sequence('is big endian:', [], value=parse('${is big endian}')),
            Child('value', optional_endian)])
        #self.assertEqual('\x00\x00\x01', encode(c, {'is big endian':0, 'value':1}).bytes())
        #self.assertEqual('\x01\x01\x00', encode(c, {'is big endian':1, 'value':1}).bytes())

    def test_visible_common_entry_is_hidden(self):
        # When we have a visible common integer that is referenced elsewhere,
        # check to see what happens when we rename and hide it in another
        # entry. This happens when we do something like
        #
        #   <reference name="bob" type="int8" expected="5" />
        #
        # which loads to
        #
        #   <sequence name="bob" value="${bob:}" expected="5" >
        #      <reference name="bob:" type="int8" />
        #   </sequence>
        #
        # We test that references to the renamed entry work correctly, and also
        # that references to the originally named entry work too.

        a = Field('a', length=8, format=Field.INTEGER)
        b = Sequence('b', [
            Sequence('c', [Child('a:', a)], value=parse('${a:}')),
            Sequence('d', [a, Sequence('d1', [], value=parse('${a}'))])])
        self.assertEqual('\x05\x07', encode(b, {'c' : 5, 'd':{'a':7, 'd1':7}}).bytes())

    def test_param_from_hidden_entry_with_visible_child(self):
        a = Sequence('a', [
            Sequence('b:', [Field('c', length=8)])],
            value=parse('${b:.c}'))
        self.assertEqual('\x0a', encode(a, 10).bytes())

    def test_hidden_sequence_with_value(self):
        # Test encoding a hidden sequence with an unknown value
        a = Sequence('a', [Sequence('b', [], value=parse('${constant}'))])
        c = Sequence('c', [Field('constant', length=8), Child('a:', a)])
        self.assertEqual('\x07', encode(c, {'constant':7}).bytes())

    def test_hidden_sequence_with_input_param(self):
        # Here we have a hidden entry that will have to be mocked, but still
        # requires that data is passed in.
        c = Sequence('a', [
            Child('b:', Sequence('b', [Field('c', length=8)])),
            Sequence('d', [], value=parse('${b:.c}'))])
        self.assertEqual('\x09', encode(c, {'d':9}).bytes())

    def test_hidden_detection(self):
        # Test the parameter passing when the common entry is first found
        # in a hidden context. There was a bug if a common entry was initially
        # found 'hidden', it would always be treated as hidden. This tests it
        # by creating a common entry that is referenced in two places, once
        # hidden, once not. For the test to pass the code must be dealing
        # correctly with the parameters.
        a = Field('a', length=8, format=Field.INTEGER)
        b = Sequence('b', [
            Sequence('c:', [a]),
            Field('d', length=parse('${c:.a} * 8'), format=Field.TEXT),
            a,
            Field('e', length=parse('${a} * 8'), format=Field.TEXT)])
        self.assertEqual('\x02dd\x03eee', encode(b, {'d':'dd', 'a':3, 'e':'eee'}).bytes())

    def test_visible_param_passed_in(self):
        # Test that we correctly pass visible parameters into hidden entries.
        # This is commonly used in conditional entries.
        a = Sequence('a', [
            Field('b', length=8, format=Field.INTEGER),
            Sequence('c:', [Field('d:', length=parse('${b} * 8'))])])
        self.assertEqual('\x00', encode(a, {'b':0}).bytes())
        self.assertEqual('\x01\x00', encode(a, {'b':1}).bytes())
        self.assertEqual('\x03\x00\x00\x00', encode(a, {'b':3}).bytes())

    def test_reference_in_constraint(self):
        # Test that the code correctly encodes when constraints have references
        a = Sequence('a', [
            Sequence('b:', [
                Sequence('b1', [], value=parse('1')),
                Sequence('b2', [], value=parse('2')),
                Sequence('b3', [], value=parse('3')),
                ]),
            Choice('c', [
                Field('c1', length=8, constraints=[Equals(parse('${b:.b1}'))]),
                Field('c2', length=8, constraints=[Equals(parse('${b:.b2}'))]),
                Sequence('c3', [Field('uint8:', length=8)],
                    value=parse('${uint8:}'), constraints=[Equals(parse('${b:.b3}'))]),
                ])
            ])
        self.assertEqual('\x01', encode(a, {'c1':None}).bytes())
        self.assertEqual('\x02', encode(a, {'c2':None}).bytes())
        self.assertEqual('\x03', encode(a, {'c3':None}).bytes())

    def test_referencing_implicit_length(self):
        # There was a problem when encoding length references to entries that
        # didn't have an explicit length. Test this.
        a = Sequence('a', [
            Field('length:', length=8),
            Sequence('b', [
                Field('b1 length:', length=8),
                Field('b1', length=parse('${b1 length:} * 8'), format=Field.TEXT)]),
            Field('unused:', length=parse('${length:} * 8 - len{b}'))
            ])
        self.assertEqual('\x05\x04abcd', encode(a, {'b':{'b1':'abcd'}}).bytes())

    def test_secondary_dependency(self):
        # Test that when A depends on C, and B depends on A, we don't attempt
        # to encode B before A.
        blah = Sequence('blah', [
            Sequence('a', [
                Field('a1', 8, format=Field.INTEGER),
                Field('a2:', 8, format=Field.INTEGER)]),
            Field('b', parse('${a.a1} * 8'), format=Field.TEXT),
            Field('c', parse('${a.a2:} * 8'), format=Field.TEXT)])
        self.assertEqual('\x03\x02xyzst', encode(blah, {
            'a' : {'a1' : 3},
            'b' : 'xyz',
            'c' : 'st'}).bytes())
