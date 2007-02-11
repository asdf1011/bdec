#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld

class TestField(unittest.TestCase):
    def test_decode(self):
        field = fld.Field("bob", lambda: 8)
        data = dt.Data.from_hex("0x017a")

        calls = []
        for is_starting, entry in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        self.assertEqual(field, calls[0])
        self.assertEqual(field, calls[1])
        self.assertEqual(1, int(calls[1].data))
        self.assertEqual(0x7a, int(data))

    def test_binary_type(self):
        field = fld.Field("bob", lambda: 12, fld.Field.BINARY)
        data = dt.Data.from_hex("0x017a")
        calls = []
        for is_starting, entry in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        self.assertEqual("0000 00010111", calls[1].get_value())

if __name__ == "__main__":
    unittest.main()
