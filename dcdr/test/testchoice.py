#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.choice as chc

class TestChoice(unittest.TestCase):
    def test_first_successful(self):
        embedded = [fld.Field("bob", lambda: 8), fld.Field("cat", lambda: 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("0x017a")
        results = list(entry for is_starting, entry in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("bob", results[0].name)
        self.assertEqual(0x01, int(results[0]))
        self.assertEqual("blah", results[1].name)
        self.assertEqual(0x7a, int(data))

    def test_second_successful(self):
        embedded = [fld.Field("bob", lambda: 24), fld.Field("cat", lambda: 8)]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("0x7a")
        results = list(entry for is_starting, entry in choice.decode(data) if not is_starting)

        self.assertEqual(2, len(results))
        self.assertEqual("cat", results[0].name)
        self.assertEqual(0x7a, int(results[0]))
        self.assertEqual("blah", results[1].name)

if __name__ == "__main__":
    unittest.main()
