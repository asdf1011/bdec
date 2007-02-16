#!/usr/bin/env python
import unittest

import dcdr.choice as chc
import dcdr.data as dt
import dcdr.field as fld
import dcdr.sequence as seq

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

    def test_uses_best_guess_on_failure(self):
        # In this test both embedded choices will fail, but
        # we should get the 'chicken' entry being reported
        # because it managed to decode the most before failing.
        cat = fld.Field("cat", lambda: 8, expected=dt.Data.from_hex("0x9"))
        embedded = [
            seq.Sequence("chicken", [
                fld.Field("bob", lambda: 24), 
                cat]),
            fld.Field("nope", lambda: 8, expected=dt.Data.from_hex("0x7"))]
        choice = chc.Choice("blah", embedded)
        data = dt.Data.from_hex("0x01020304")

        ex = None
        results = []
        try:
            for is_starting, entry in choice.decode(data):
                results.append((is_starting, entry))
        except fld.BadDataError, ex:
            pass
        self.assertTrue(ex is not None)
        self.assertEqual(cat, ex.field)

        # The 'cat', 'chicken', and 'blah' entries should have
        # started decoding, and the 'bob' entry should have
        # fully decoded.
        self.assertEqual(5, len(results))
        self.assertEqual("blah", results[0][1].name)
        self.assertEqual("chicken", results[1][1].name)
        self.assertEqual("bob", results[2][1].name)
        self.assertEqual("bob", results[3][1].name)
        self.assertEqual("cat", results[4][1].name)
        self.assertEqual(4, int(data))
        

if __name__ == "__main__":
    unittest.main()
