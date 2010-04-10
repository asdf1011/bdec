
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
