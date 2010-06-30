import unittest

from bdec.expression import parse
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

from bdec.output.instance import encode

class TestSequenceOf(unittest.TestCase):
    def test_encode_hidden_count(self):
        # Test that we correctly encode a hidden count
        a = Sequence('a', [
            Field('count:', length=8),
            SequenceOf('c', Field('d', length=8, format=Field.TEXT), count=parse("${count:}")),
            ])
        self.assertEqual('\x03abc', encode(a, {'c' : ['a', 'b', 'c']}).bytes())
