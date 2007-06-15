#!/usr/bin/env python

import unittest

import bdec.data as dt
import bdec.field as fld
import bdec.spec.xmlspec as xml

class TestXml(unittest.TestCase):
    def test_simple_field(self):
        text = """<protocol><field name="bob" length="8" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(items))
        self.assertEqual("01111010", decoder.get_value())

    def test_simple_text_field(self):
        text = """<protocol><field name="bob" length="8" type="text" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex(hex(ord('?'))[2:])))
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
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.children[0].name)
        self.assertEqual("dog", decoder.children[1].name)
        items = list(decoder.decode(dt.Data.from_hex("7fac")))
        self.assertEqual(6, len(items))
        self.assertEqual("7f", decoder.children[0].get_value())
        self.assertEqual(172, decoder.children[1].get_value())

    def test_bad_expected_value(self):
        text = """<protocol><field name="bob" length="8" value="0xa0" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertRaises(fld.BadDataError, lambda: list(decoder.decode(dt.Data.from_hex("7a"))))

    def test_choice(self):
        text = """
<protocol>
    <choice name="bob">
        <field name="cat" length="8" type="hex" />
        <field name="dog" length="8" type="integer" />
    </choice>
</protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.children[0].name)
        self.assertEqual("dog", decoder.children[1].name)
        items = list(decoder.decode(dt.Data.from_hex("7fac")))
        self.assertEqual(4, len(items))
        self.assertEqual("7f", decoder.children[0].get_value())

    def test_sequence_of(self):
        text = """
<protocol>
    <sequenceof name="bob" length="2">
        <field name="cat" length="8" type="hex" />
    </sequenceof>
</protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.child.name)
        items = list(decoder.decode(dt.Data.from_hex("7fac")))
        self.assertEqual(6, len(items))
        # We're being lazy; we're only checking the last decode value.
        self.assertEqual("ac", decoder.child.get_value())

    def test_non_whole_byte_expected_value(self):
        text = """<protocol><field name="bob" length="1" value="0x0" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(result))
        self.assertEqual(0, int(result[1][1]))

    def test_common(self):
        text = """<protocol> <common> <field name="bob" length="8" /> </common> <field name="bob" /> </protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual(8, decoder.length)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(result))
        self.assertEqual(0x7a, int(result[1][1]))

    def test_common_item_references_another(self):
        text = """
            <protocol>
                <common>
                    <field name="bob" length="8" />
                    <sequence name="rabbit">
                        <field name="bob" />
                    </sequence>
                </common>
                <sequence name="rabbit" />
            </protocol>"""

        decoder = xml.loads(text)[0]
        self.assertEqual("rabbit", decoder.name)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(4, len(result))
        self.assertEqual(0x7a, int(result[2][1]))

    def test_expression_references_field(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <field name="length:" length="8" type="integer" />
                    <field name="bob" length="${length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        decoder = xml.loads(text)[0]
        result = list(decoder.decode(dt.Data("\x05hello")))
        self.assertEqual(6, len(result))
        self.assertEqual("hello", result[4][1].get_value())

    def test_empty_sequence_error(self):
        text = """<protocol><sequence name="bob"></sequence></protocol>"""
        self.assertRaises(xml.EmptySequenceError, xml.loads, text)

    def test_expression_references_sub_field(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <sequence name="cat">
                        <field name="length:" length="8" type="integer" />
                    </sequence>
                    <field name="bob" length="${cat.length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        decoder = xml.loads(text)[0]
        result = list(decoder.decode(dt.Data("\x05hello")))
        self.assertEqual("hello", result[6][1].get_value())

    def _decode(self, protocol, data):
        """
        Return a dictionary of decoded fields.
        """
        result = {}
        for is_starting, entry in protocol.decode(dt.Data(data)):
            if not is_starting and isinstance(entry, fld.Field):
                result[entry.name] = entry.get_value()
        return result

    def test_expression_reference_choice_field(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <choice name="variable length:">
                        <sequence name="8 bit:">
                           <field name="id:" length="8" value="0x0" />
                           <field name="length:" length="8" type="integer" />
                        </sequence>
                        <sequence name="16 bit:">
                           <field name="id:" length="8" value="0x1" />
                           <field name="length:" length="16" type="integer" />
                       </sequence>
                    </choice>
                    <field name="bob" length="${variable length:.length:} * 8" type="text" />
                    <!-- Now try matching the length without specifying the hidden choice -->
                    <field name="sue" length="${length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        decoder = xml.loads(text)[0]

        # Try using the 8 bit length
        result = self._decode(decoder, "\x00\x05hellokitty")
        self.assertEqual("hello", result['bob'])
        self.assertEqual("kitty", result['sue'])

        # Try using the 16 bit length
        result = self._decode(decoder, "\x01\x00\x05hellokitty")
        self.assertEqual("hello", result['bob'])
        self.assertEqual("kitty", result['sue'])

    def test_not_all_choice_entries_match_error(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <choice name="variable length:">
                        <sequence name="8 bit:">
                           <field name="id:" length="8" value="0x0" />
                           <field name="length:" length="8" type="integer" />
                        </sequence>
                        <sequence name="16 bit:">
                           <field name="id:" length="8" value="0x1" />
                           <field name="longer length:" length="16" type="integer" />
                       </sequence>
                    </choice>
                    <!-- Not all options in the choice have 'length:', so this should fail. -->
                    <field name="bob" length="${variable length:.length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        try:
            xml.loads(text)
            self.fail("Exception not thrown!")
        except xml.XmlExpressionError, ex:
            self.assertTrue(isinstance(ex.ex, xml.ChoiceReferenceMatchError))

if __name__ == "__main__":
    unittest.main()
