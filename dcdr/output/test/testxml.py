#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.output.xmlout as xml
import dcdr.sequence as seq

class TestXml(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", lambda: 8)
        text = xml.to_string(field, dt.Data.from_hex('8e'))
        self.assertEqual("<bob>\n    10001110\n</bob>\n", text)

    def test_hidden_entry(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", lambda: 8, fld.Field.INTEGER),
            fld.Field("dog", lambda: 24, fld.Field.TEXT)])
        text = xml.to_string(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertEqual("<bob>\n    <dog>\n        zip\n    </dog>\n</bob>\n", text)

if __name__ == "__main__":
    unittest.main()
