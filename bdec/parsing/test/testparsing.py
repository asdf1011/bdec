
import unittest

from bdec.parsing import *
#from pyparsing import *

class TestParsing(unittest.TestCase):
    def test_word(self):
        a = Word('abcde')
        self.assertEqual(['ebad'], list(a.parseString('ebad')))
