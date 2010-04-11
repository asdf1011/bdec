
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

    def test_chars_not_in(self):
        a = CharsNotIn(alphas + ' ') + Word(alphas) + StringEnd()
        self.assertEqual(['123456', 'abcd'], list(a.parseString('123456 abcd')))
        self.assertRaises(ParseException, a.parseString, 'abc')

    def test_or(self):
        a = Word(alphas) | Word(nums)
        self.assertEqual(['1234'], list(a.parseString('1234')))
        self.assertEqual(['abcd'], list(a.parseString('abcd')))

    def test_suppress(self):
        a = Suppress(Word(alphas)) + Word(nums) + StringEnd()
        self.assertEqual(['1234'], list(a.parseString('abcd 1234')))

    def test_forward(self):
        expr = Forward()
        group = '(' + expr + ')'
        expr << (Word(nums) | group)
        self.assertEqual(['(', '5', ')'], list(expr.parseString('(5)')))
        self.assertEqual(['(', '(', '5', ')', ')'], list(expr.parseString('((5))')))
        self.assertRaises(ParseException, expr.parseString, '((5)')

    def test_combine(self):
        a = Combine(Suppress('0x') + Word(hexnums))
        self.assertEqual(['1234'], list(a.parseString('0x1234')))
        self.assertRaises(ParseException, a.parseString, '0x 1234')
