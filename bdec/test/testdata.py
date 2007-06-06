#!/usr/bin/env python
import unittest

import bdec
import bdec.data as dt

class TestData(unittest.TestCase):
    def test_pop_empty_data(self):
        self.assertRaises(dt.NotEnoughDataError, dt.Data("").pop, 1)

    def test_integer(self):
        self.assertEqual(3, int(dt.Data(chr(3))))

    def test_little_endian_integer(self):
        data = dt.Data.from_hex("010203")
        self.assertEqual(0x030201, data.get_little_endian_integer())

    def test_string(self):
        self.assertEqual("Some text", str(dt.Data("Some text")))

    def test_unaligned_string(self):
        # The first 4 bits (the 'a') will be popped, then the 5 byte
        # string, then it'll be converted to text.
        data = dt.Data.from_hex("a68656c6c6fa")
        data.pop(4)
        text = data.pop(5 * 8)
        self.assertEqual('hello', str(text))
    
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
        self.assertEqual(chr(255), str(dt.Data.from_int_big_endian(255, 8)))
        self.assertRaises(dt.NotEnoughDataError, dt.Data.from_int_big_endian, 255, 7)

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
        self.assertEqual('blah blah', str(dt.Data.from_hex(hex)))

    def test_adding_data(self):
        self.assertEqual("chicken little", str(dt.Data("chicken ") + dt.Data("little")))

    def test_unaligned_bits(self):
        self.assertEqual(0x2d, int(dt.Data.from_binary_text("010") + dt.Data.from_binary_text("1101")))

if __name__ == "__main__":
    unittest.main()
