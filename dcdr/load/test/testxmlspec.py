#!/usr/bin/env python

import unittest

import dcdr.data as dt
import dcdr.field as fld
import dcdr.load.xmlspec as xml

class TestXml(unittest.TestCase):
    def test_simple_field(self):
        text = """<protocol><field name="bob" length="8" /></protocol>"""
        decoder = xml.Importer().loads(text)
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex("0x7a")))
        self.assertEqual(2, len(items))
        self.assertEqual("01111010", decoder.get_value())

    def test_simple_text_field(self):
        text = """<protocol><field name="bob" length="8" type="text" /></protocol>"""
        decoder = xml.Importer().loads(text)
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex(hex(ord('?')))))
        self.assertEqual(2, len(items))
        self.assertEqual("?", decoder.get_value())

if __name__ == "__main__":
    unittest.main()
