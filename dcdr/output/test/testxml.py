#!/usr/bin/env python
import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.output.xml as xml

class TestXml(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", lambda: 8)
        text = xml.to_string(field, dt.Data.from_hex('0x8e'))
        self.assertEqual("<bob>\n    10001110\n</bob>\n", text)

if __name__ == "__main__":
    unittest.main()
