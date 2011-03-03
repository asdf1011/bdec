
import unittest

from bdec.parsing import *
#from pyparsing import *

class TestParsing(unittest.TestCase):
    def test_word(self):
        a = Word('abcde')
        self.assertEqual(['ebad'], list(a.parseString('ebad')))

    def test_multiple_words(self):
        a = Word('abcde') + Word('abcd')
        self.assertEqual(['ebad', 'bbbb'], list(a.parseString('ebad bbbb')))

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

    def test_ignore(self):
        comment = '//' + CharsNotIn('\n') + '\n'
        words = ZeroOrMore(Word(alphas)) + StringEnd()
        words.ignore(comment)
        self.assertEquals(['run', 'dog', 'run'], list(words.parseString('''run // Ignore me
            // Ignore me too
            dog run''')))

        # Test that an entry 'in the middle' can have an ignore entry
        a = Suppress('start:') + words
        self.assertEquals(['run', 'dog', 'run'], list(a.parseString('''start: run // Ignore me
            dog //ignore me
            // ignore me too
            run''')))

    def test_ignore_cpp_comments(self):
        comment = '/*' + SkipTo('*/')
        words = ZeroOrMore(Word(alphas)) + StringEnd()
        words.ignore(comment)
        self.assertEqual(['good', 'bad', 'ugly'], list(words.parseString('''
            good
            /* this should be ignored */
            bad /* this too */
            ugly /* and finally... */''')))

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

        a = Combine(Literal('a') + Literal('b'))
        self.assertEqual(['ab'], list(a.parseString('ab')))

    def test_srange(self):
        self.assertEqual('abcd', srange('[a-d]'))
        self.assertEqual('15678', srange('[15-8]'))

    def test_caseless_literal(self):
        a = CaselessLiteral('rabbit')
        self.assertEqual(['rabbit'], list(a.parseString('Rabbit')))
        self.assertEqual(['rabbit'], list(a.parseString('RABBIT')))
        self.assertEqual(['rabbit'], list(a.parseString('rAbbIt')))
        self.assertRaises(ParseException, a.parseString, 'rabbi')
        self.assertRaises(ParseException, a.parseString, 'rab bit')

    def test_add_parse_action_three_args(self):
        a = Word('abcd').addParseAction(lambda s,l,t:[t[0].upper()])
        self.assertEqual(['BAD'], list(a.parseString('bad')))

    def test_add_parse_action_two_args(self):
        a = Word('abcd').addParseAction(lambda l,t:[t[0].upper()])
        self.assertEqual(['BAD'], list(a.parseString('bad')))

    def test_add_parse_action_one_arg(self):
        a = Word('abcd').addParseAction(lambda t:[t[0].upper()])
        self.assertEqual(['BAD'], list(a.parseString('bad')))

    def test_action_returns_object(self):
        a = Word('abcd').addParseAction(lambda t:t[0].upper())
        self.assertEqual(['BAD'], list(a.parseString('bad')))

    def test_word_body_chars(self):
        a = Word(alphas, alphas + nums) + StringEnd()
        self.assertEquals(['Dab0c'], a.parseString(' Dab0c '))
        self.assertEquals(['Aabc123'], a.parseString(' Aabc123 '))
        self.assertRaises(ParseException, a.parseString, '0abcd')
        self.assertRaises(ParseException, a.parseString, '/AbCd')
        self.assertRaises(ParseException, a.parseString, 'AbCd/')

    def test_not_any(self):
        name = Word(alphas)
        keywords = MatchFirst([Literal(n) for n in ('if', 'then')])
        variable = NotAny(keywords) + name
        self.assertEqual(['abcd'], list(variable.parseString(' abcd')))
        self.assertEqual(['aif'], list(variable.parseString('aif')))
        self.assertRaises(ParseException, variable.parseString, 'if')
        self.assertRaises(ParseException, variable.parseString, 'then')

