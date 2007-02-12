#!/usr/bin/env python
import unittest

import dcdr
import dcdr.data as dt

class TestData(unittest.TestCase):
    def test_pop_empty_data(self):
        self.assertRaises(dt.NotEnoughDataError, dt.Data("").pop, 1)

    def test_integer(self):
        self.assertEqual(3, int(dt.Data(chr(3))))

    def test_string(self):
        self.assertEqual("Some text", str(dt.Data("Some text")))
    
    def test_pop(self):
        data = dt.Data.from_hex("0xf0")
        self.assertEqual(0x7, int(data.pop(3)))
        self.assertEqual(0x10, int(data))

    def test_hex(self):
        data = dt.Data.from_hex("0xf0ee9601")
        self.assertEqual(0xf0, int(data.pop(8)))
        self.assertEqual(0xee, int(data.pop(8)))
        self.assertEqual(0x96, int(data.pop(8)))
        self.assertEqual(0x01, int(data.pop(8)))

    def test_hexstring(self):
        data = dt.Data.from_hex("0xf0ee9601")
        self.assertEqual("f0ee9601", data.get_hex())

if __name__ == "__main__":
    unittest.main()
