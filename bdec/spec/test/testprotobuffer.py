
from bdec.data import Data
from bdec.spec import load_specs
from bdec.output.instance import decode, encode
import unittest


class TestProtoBuffer(unittest.TestCase):
    def assert_value(self, entry, data, value):
        # First try decoding...
        self.assertEqual(value, decode(entry, data.copy()).value)

        # Then encoding...
        self.assertEqual(data, encode(entry, {'value' : value}))

    def test_string(self):
         text = '''
           message String {
             required string value = 2;
           } '''
         entry, common, lookup = load_specs([('test.proto', text, None)])
         from bdec.spec.xmlspec import dumps
         self.assert_value(entry, Data('\x12\x07\x74\x65\x73\x74\x69\x6e\x67'), 'testing')

    def test_int32(self):
        text = '''
          message Integer {
            required int32 value = 1;
          } '''
        entry, common, lookup = load_specs([('test.proto', text, None)])
        self.assert_value(entry, Data('\x08\x96\x01'), 150)
        self.assert_value(entry, Data('\x08\xff\xff\xff\xff\x07'), (1 << 31) - 1)
        # Really bloody slow because of the choosing that goes on (at every
        # level it encodes twice).
        self.assert_value(entry, Data('\x08\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01'), -1)
