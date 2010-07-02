import unittest

from bdec.constraints import Minimum, Maximum
from bdec.entry import Child
from bdec.encode.entry import MissingInstanceError
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

