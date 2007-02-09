#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld

class TestField(unittest.TestCase):
    def test_decode(self):
        field = fld.Field("bob", lambda: 8)
        data = dt.Data.from_hex("0x017a")

        calls = []
        start = lambda a: calls.append((a, None))
        end = lambda a, data: calls.append((a, data))
        field.decode(data, start, end)
        self.assertEqual(2, len(calls))
        self.assertEqual((field, None), calls[0])
        self.assertEqual(field, calls[1][0])
        self.assertEqual(1, int(calls[1][1]))
        self.assertEqual(0x7a, int(data))

if __name__ == "__main__":
    unittest.main()
