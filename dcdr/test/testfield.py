#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld

class TestField(unittest.TestCase):
    def test_decode(self):
        field = fld.Field("bob", 8)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, entry in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        self.assertEqual(field, calls[0])
        self.assertEqual(field, calls[1])
        self.assertEqual(1, int(calls[1].data))
        self.assertEqual(0x7a, int(data))

    def _get_decode_value(self, hex, length, format, encoding=""):
        field = fld.Field("bob", length, format, encoding)
        data = dt.Data.from_hex(hex)
        calls = []
        for is_starting, entry in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        return calls[1].get_value()

    def test_binary_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.BINARY)
        self.assertEqual("0000 00010111", actual)

    def test_hexstring_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.HEX)
        self.assertEqual("017", actual)

    def test_string_type(self):
        raw = "chicken"
        encoded = "".join(hex(ord(char))[2:] for char in raw)
        actual = self._get_decode_value("" + encoded, 8 * len(raw), fld.Field.TEXT, "ascii")
        self.assertEqual("chicken", actual)

    def test_little_endian(self):
        actual = self._get_decode_value("0008", 16, fld.Field.INTEGER, fld.Field.LITTLE_ENDIAN)
        self.assertEqual(8 * 256, actual)

    def test_big_endian(self):
        actual = self._get_decode_value("0008", 16, fld.Field.INTEGER, fld.Field.BIG_ENDIAN)
        self.assertEqual(8, actual)

    def test_bad_expected_data(self):
        field = fld.Field("bob", 8, expected=dt.Data.from_hex('fe'))
        data = dt.Data.from_hex("f7")
        self.assertRaises(fld.BadDataError, lambda: list(field.decode(data)))

    def test_good_expected_data(self):
        field = fld.Field("bob", 8, expected=dt.Data.from_hex('fe'))
        data = dt.Data.from_hex("fe")
        result = list(field.decode(data))
        self.assertEqual(2, len(result))
        self.assertEqual("fe", result[1][1].data.get_hex())

    def test_encode(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        result = field.encode(lambda name, context: 0x3f, None)
        self.assertEqual(0x3f, int(result.next()))

if __name__ == "__main__":
    unittest.main()
