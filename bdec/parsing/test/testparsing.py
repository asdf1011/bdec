
import unittest

from bdec import DecodeError
from bdec.parsing import *
#from pyparsing import *

class TestParsing(unittest.TestCase):
    def test_word(self):
        a = Word('abcde')
        self.assertEqual(['ebad'], a.parseString('ebad'))

    def test_zero_or_more(self):
        a = ZeroOrMore(Word('abcd'))
        self.assertEqual(['ab', 'cd', 'dc'], a.parseString('  ab cd dc'))

    def test_one_or_more(self):
        a = OneOrMore(Word('abcd'))
        self.assertEqual(['ab', 'cd', 'dc'], a.parseString('  ab cd  dc  '))
        self.assertRaises(DecodeError, a.parseString, 'ebcd')

    def test_string_end(self):
        a = Word('abcd') + StringEnd()
        self.assertEqual(['aaaaa'], a.parseString(' aaaaa '))
        self.assertRaises(DecodeError, a.parseString, ' aaaaa b')
