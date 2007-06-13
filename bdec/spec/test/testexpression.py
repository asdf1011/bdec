import bdec.spec.expression as exp
import unittest

class TestExpression(unittest.TestCase):
    def test_simple_int(self):
        self.assertEqual(5, exp.compile('5'))

    def test_add(self):
        self.assertEqual(8, int(exp.compile('5 + 3')))

    def test_sub(self):
        self.assertEqual(2, int(exp.compile('8 - 6')))

    def test_compound(self):
        self.assertEqual(12, int(exp.compile('6 + 7 - 1')))

    def test_brackets(self):
        self.assertEqual(6, int(exp.compile('(6)')))
        self.assertEqual(7, int(exp.compile('(6 + 1)')))
        self.assertEqual(7, int(exp.compile('(6) + 1')))
        self.assertEqual(4, int(exp.compile('1 + (5 - 2)')))
