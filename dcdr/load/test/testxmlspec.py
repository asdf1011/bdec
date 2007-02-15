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

    def test_sequence(self):
        text = """
<protocol>
    <sequence name="bob">
        <field name="cat" length="8" type="hex" />
        <field name="dog" length="8" type="integer" />
    </sequence>
</protocol>"""
        decoder = xml.Importer().loads(text)
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.children[0].name)
        self.assertEqual("dog", decoder.children[1].name)
        items = list(decoder.decode(dt.Data.from_hex("0x7fac")))
        self.assertEqual(6, len(items))
        self.assertEqual("7f", decoder.children[0].get_value())
        self.assertEqual(172, decoder.children[1].get_value())

    def test_bad_expected_value(self):
        text = """<protocol><field name="bob" length="8" value="0xa0" /></protocol>"""
        decoder = xml.Importer().loads(text)
        self.assertEqual("bob", decoder.name)
        self.assertRaises(fld.BadDataError, lambda: list(decoder.decode(dt.Data.from_hex("0x7a"))))

    def test_choice(self):
        text = """
<protocol>
    <choice name="bob">
        <field name="cat" length="8" type="hex" />
        <field name="dog" length="8" type="integer" />
    </choice>
</protocol>"""
        decoder = xml.Importer().loads(text)
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.children[0].name)
        self.assertEqual("dog", decoder.children[1].name)
        items = list(decoder.decode(dt.Data.from_hex("0x7fac")))
        self.assertEqual(4, len(items))
        self.assertEqual("7f", decoder.children[0].get_value())

if __name__ == "__main__":
    unittest.main()
