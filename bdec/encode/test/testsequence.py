import unittest

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

