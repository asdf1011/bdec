import bdec.spec.expression as exp
import unittest

class TestExpression(unittest.TestCase):
    def test_simple_int(self):
        self.assertEqual(5, exp.compile('5'))

    def test_add(self):
        self.assertEqual(8, int(exp.compile('5 + 3')))
