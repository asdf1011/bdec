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

    def test_multiply(self):
        self.assertEqual(8, int(exp.compile('4 * 2')))

    def test_divide(self):
        self.assertEqual(7, int(exp.compile('14 / 2')))

    def test_mod(self):
        self.assertEqual(2, int(exp.compile('8 % 3')))

    def test_bimdas(self):
        self.assertEqual(25, int(exp.compile('5 + 2 * 10')))
        self.assertEqual(70, int(exp.compile('(5 + 2) * 10')))

    def test_named_reference(self):
        # Note that we'll use a few odd characters to see if the are valid...
        _lookup = {"bob":3, "cat :_":5}
        query = lambda name: _lookup[name]
        self.assertEqual(3, int(exp.compile('${bob}', query)))
        self.assertEqual(13, int(exp.compile('${bob} + 2 * ${cat :_}', query)))

    def test_length_lookup(self):
        query = lambda name: {"bob": 3}[name]
        self.assertEqual(3, int(exp.compile('len{bob}', length_lookup=query)))

