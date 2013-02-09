
from bdec.data import Data
from bdec.spec import load_specs
from bdec.output.instance import decode
import unittest

class TestProtoBuffer(unittest.TestCase):
    #def test_string(self):
    #    text = '''
    #      message String {
    #        required string value = 1;
    #      } '''
    #    messages, common, lookup = loads(text)
    #    self.assertEqual(1, len(messages))
    #    data = decode(messages[0], Data('\x00'))
    #    self.assertEqual('abcd', data.String.value)

    def test_integer(self):
        text = '''
          message Integer {
            required int32 value = 1;
          } '''
        entry, common, lookup = load_specs([('test.proto', text, None)])
        data = decode(entry, Data('\x08\x96\x01'))
        self.assertEqual(150, data.value)
        self.assertEqual(Data('\x08\x96\x01'), encode(entry, data))

