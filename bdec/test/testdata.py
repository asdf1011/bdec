#!/usr/bin/env python
import StringIO
import unittest

import bdec
import bdec.data as dt

class TestData(unittest.TestCase):
    def test_pop_empty_data(self):
        self.assertRaises(dt.NotEnoughDataError, int, dt.Data("").pop(1))

    def test_pop_negative_number(self):
        self.assertEqual("abcd", dt.Data("abcd").pop(32).bytes())
        self.assertRaises(dt.NotEnoughDataError, int, dt.Data("abcd").pop(33))

    def test_integer(self):
        self.assertEqual(3, int(dt.Data(chr(3))))

    def test_little_endian_integer(self):
        data = dt.Data.from_hex("010203")
        self.assertEqual(0x030201, data.get_little_endian_integer())

    def test_string(self):
        self.assertEqual("Some text", dt.Data("Some text").bytes())
        self.assertEqual("", dt.Data().bytes())

    def test_unaligned_string(self):
        # The first 4 bits (the 'a') will be popped, then the 5 byte
        # string, then it'll be converted to text.
        data = dt.Data.from_hex("a68656c6c6fa")
        data.pop(4)
        text = data.pop(5 * 8)
        self.assertEqual('hello', text.bytes())
    
    def test_pop(self):
        data = dt.Data.from_hex("f0")
        self.assertEqual(0x7, int(data.pop(3)))
        self.assertEqual(0x10, int(data))

    def test_hex(self):
        data = dt.Data.from_hex("f0ee9601")
        self.assertEqual(0xf0, int(data.pop(8)))
        self.assertEqual(0xee, int(data.pop(8)))
        self.assertEqual(0x96, int(data.pop(8)))
        self.assertEqual(0x01, int(data.pop(8)))

    def test_hexstring(self):
        data = dt.Data.from_hex("f0ee9601")
        self.assertEqual("f0ee9601", data.get_hex())

    def test_encode_little_endian(self):
        data = dt.Data.from_int_little_endian(10000, 16)
        self.assertEqual(16, len(data))
        self.assertEqual(10000, data.get_little_endian_integer())

    def test_encode_big_endian(self):
        data = dt.Data.from_int_big_endian(10000, 16)
        self.assertEqual(16, len(data))
        self.assertEqual(10000, int(data))

    def test_encode_not_enough_data(self):
        self.assertEqual(chr(255), dt.Data.from_int_big_endian(255, 8).bytes())
        self.assertRaises(dt.IntegerTooLongError, dt.Data.from_int_big_endian, 255, 7)

    def test_encode_length(self):
        data = dt.Data.from_int_big_endian(0x3e, 7)
        self.assertEqual(7, len(data))
        self.assertEqual(0x3e, int(data))

    def test_convert_binary_text(self):
        self.assertEqual(3, int(dt.Data.from_binary_text('000011')))
        self.assertEqual(17, int(dt.Data.from_binary_text('010001')))
        self.assertEqual(255, int(dt.Data.from_binary_text('11111111')))
        self.assertEqual(256, int(dt.Data.from_binary_text('1 00000000')))
        data = dt.Data.from_hex('78f638fd')
        self.assertEqual('78f638fd', dt.Data.from_binary_text(data.get_binary_text()).get_hex())

    def test_to_and_from_hex(self):
        hex = dt.Data('blah blah').get_hex()
        self.assertEqual('blah blah', dt.Data.from_hex(hex).bytes())

    def test_adding_data(self):
        self.assertEqual("chicken little", (dt.Data("chicken ") + dt.Data("little")).bytes())

    def test_equality(self):
        self.assertEqual(dt.Data.from_binary_text('1110'), dt.Data.from_hex('e0').pop(4))

    def test_unaligned_bits(self):
        self.assertEqual(0x2d, int(dt.Data.from_binary_text("010") + dt.Data.from_binary_text("1101")))

    def test_hex_conversion(self):
        self.assertEqual("\x23\x45\x67", dt.Data.from_hex("23 45 67").bytes())

    def test_conversion_needs_bytes(self):
        self.assertRaises(dt.ConversionNeedsBytesError, dt.Data.bytes, dt.Data("00", 0, 4))
        data = dt.Data.from_hex('ab')
        self.assertRaises(dt.ConversionNeedsBytesError, dt.Data.bytes, data.pop(4))

    def test_empty(self):
        data = dt.Data()
        self.assertTrue(data.empty())

        # Now create some data that should have more data then it does
        data = dt.Data('', 0, 8)
        self.assertTrue(not data.empty())
        self.assertRaises(dt.NotEnoughDataError, int, data)
        
        # Now create data that has more buffer available, but we tell it
        # the length is at an end.
        data = dt.Data("1234").pop(8)
        self.assertTrue(not data.empty())
        data.pop(8)
        self.assertTrue(data.empty())

    def test_bad_encoding(self):
        data = dt.Data('\xb2')
        self.assertRaises(dt.BadTextEncodingError, dt.Data.text, data, "ascii")

    def test_file_buffer(self):
        buffer = StringIO.StringIO()
        buffer.write('\x04abcd')
        data = dt.Data(buffer)
        self.assertEqual(4, int(data.pop(8)))
        self.assertEqual('abcd', data.bytes())
