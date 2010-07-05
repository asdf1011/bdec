import unittest

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
