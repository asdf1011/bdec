
import unittest

from bdec.parsing import *
#from pyparsing import *

class TestParsing(unittest.TestCase):
    def test_word(self):
        a = Word('abcde')
        self.assertEqual(['ebad'], list(a.parseString('ebad')))

    def test_zero_or_more(self):
        a = ZeroOrMore(Word('abcd'))
        self.assertEqual(['ab', 'cd', 'dc'], list(a.parseString('  ab cd dc')))

    def test_one_or_more(self):
        a = OneOrMore(Word('abcd'))
        self.assertEqual(['ab', 'cd', 'dc'], list(a.parseString('  ab cd  dc  ')))
        self.assertRaises(ParseException, a.parseString, 'ebcd')

    def test_string_end(self):
        a = Word('abcd') + StringEnd()
        self.assertEqual(['aaaaa'], list(a.parseString(' aaaaa ')))
        self.assertRaises(ParseException, a.parseString, ' aaaaa b')

    def test_alphas(self):
        a = Word(alphas + '-')
        self.assertEqual(['abcd-efgh'], list(a.parseString('abcd-efgh')))
