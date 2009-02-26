#   Copyright (C) 2008-2009 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

#!/usr/bin/env python

import unittest

import bdec
import bdec.choice as chc
from bdec.constraints import ConstraintError, Equals
import bdec.data as dt
import bdec.entry as ent
import bdec.expression as expr
import bdec.field as fld
import bdec.output.instance as inst
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.spec.xmlspec as xml
from bdec.test.decoders import assert_xml_equivalent

class TestXml(unittest.TestCase):
    def test_simple_field(self):
        text = """<protocol><field name="bob" length="8" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(items))
        self.assertEqual("01111010", str(items[1][4]))

    def test_simple_text_field(self):
        text = """<protocol><field name="bob" length="8" type="text" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertTrue(isinstance(decoder, fld.Field)) 
        self.assertEqual("bob", decoder.name)
        items = list(decoder.decode(dt.Data.from_hex(hex(ord('?'))[2:])))
        self.assertEqual(2, len(items))
        self.assertEqual("?", items[1][4])

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
        items = list(value for is_starting, name, entry, data, value in decoder.decode(dt.Data.from_hex("7fac")) if not is_starting)
        self.assertEqual(3, len(items))
        self.assertEqual("7f", str(items[0]))
        self.assertEqual(172, items[1])

    def test_bad_expected_value(self):
        text = """<protocol><field name="bob" length="8" value="0xa0" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertRaises(ConstraintError, lambda: list(decoder.decode(dt.Data.from_hex("7a"))))

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
        items = list(value for is_starting, name, entry, data, value in decoder.decode(dt.Data.from_hex("7fac")) if not is_starting)
        self.assertEqual(2, len(items))
        self.assertEqual("7f", str(items[0]))

    def test_sequence_of(self):
        text = """
<protocol>
    <sequenceof name="bob" count="2">
        <field name="cat" length="8" type="hex" />
    </sequenceof>
</protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual("cat", decoder.children[0].name)
        items = list(value for is_starting, name, entry, data, value in decoder.decode(dt.Data.from_hex("7fac")) if not is_starting)
        self.assertEqual(3, len(items))
        self.assertEqual("7f", str(items[0]))
        self.assertEqual("ac", str(items[1]))

    def test_non_whole_byte_expected_value(self):
        text = """<protocol><field name="bob" length="1" value="0x0" /></protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(result))
        self.assertEqual(0, int(result[1][3]))

    def test_common(self):
        text = """<protocol> <common> <field name="bob" length="8" /> </common> <reference name="bob" /> </protocol>"""
        decoder = xml.loads(text)[0]
        self.assertEqual("bob", decoder.name)
        self.assertEqual(8, decoder.length.value)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(2, len(result))
        self.assertEqual(0x7a, int(result[1][3]))

    def test_common_item_references_another(self):
        text = """
            <protocol>
                <common>
                    <field name="bob" length="8" />
                    <sequence name="rabbit">
                        <reference name="bob" />
                    </sequence>
                </common>
                <reference name="rabbit" />
            </protocol>"""

        decoder = xml.loads(text)[0]
        self.assertEqual("rabbit", decoder.name)
        result = list(decoder.decode(dt.Data.from_hex("7a")))
        self.assertEqual(4, len(result))
        self.assertEqual(0x7a, int(result[2][3]))

    def test_expression_references_field(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <field name="length:" length="8" type="integer" />
                    <field name="bob" length="${length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        decoder = xml.loads(text)[0]
        result = list(value for is_starting, name, entry, data, value in decoder.decode(dt.Data("\x05hello")) if not is_starting)
        self.assertEqual(3, len(result))
        self.assertEqual("hello", result[1])

    def test_failure_when_referencing_sequenceof(self):
        text = """
            <protocol>
                <sequence name="rabbit">
                    <sequenceof name="length:" count="1" type="integer" >
                        <field name="cat" length="8" />
                    </sequenceof>
                    <field name="bob" length="${length:} * 8" type="text" />
                </sequence>
            </protocol>"""
        try:
            xml.loads(text)
            raise Exception('Exception not thrown!')
        except bdec.spec.LoadError, ex:
            print str(ex)
            self.assertTrue("Can't reference " in str(ex))

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
        result = list(value for is_starting, name, entry, data, value in decoder.decode(dt.Data("\x05hello")) if not is_starting)
        self.assertEqual("hello", result[2])

    def _decode(self, protocol, data):
        """
        Return a dictionary of decoded fields.
        """
        result = {}
        for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data(data)):
            if not is_starting and isinstance(entry, fld.Field):
                result[entry.name] = value
        return result

    def test_expression_references_choice_field(self):
        # FIXME: We cannot reference the variable length using multiple names. See issue 37.
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
                    <field name="sue" length="${variable length:.length:} * 8" type="text" />
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
        self.assertRaises(xml.XmlExpressionError, xml.loads, text)

    def test_sequenceof_break(self):
        text = """
            <protocol>
                <sequenceof name="bob">
                    <choice name="char:">
                        <field name="null:" length="8" value="0x0"> <end-sequenceof /></field>
                        <field name="char" length="8" type="text" />
                    </choice>
                </sequenceof>
            </protocol>"""

        protocol = xml.loads(text)[0]
        result = ""
        for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data("hello world\x00")):
            if not is_starting and entry.name == "char":
                result += value
        self.assertEqual("hello world", result)

    def test_length_reference(self):
        text = """
           <protocol>
               <sequence name="bob">
                   <field name="length" length="8" type="integer" />
                   <sequenceof name="null terminated string">
                       <choice name="entry:">
                           <field name="null" length="8" value="0x0" ><end-sequenceof /></field>
                           <field name="char" length="8" type="text" />
                       </choice>
                   </sequenceof>
                   <field name="unused" length="${length} * 8 - len{null terminated string}" type="text" />
               </sequence>
           </protocol>
           """
        protocol = xml.loads(text)[0]
        result = ""
        unused = ""
        for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data("\x0fhello world\x00afd")):
            if not is_starting:
                if entry.name == "char":
                    result += value
                elif entry.name == "unused":
                    unused = value
        self.assertEqual("hello world", result)
        self.assertEqual("afd", unused)

    def test_field_range(self):
        text = """
            <protocol>
                <field name="bob" type="integer" length="8" min="4" max="0xf" />
           </protocol>
           """
        protocol = xml.loads(text)[0]
        self.assertRaises(ConstraintError, list, protocol.decode(dt.Data('\x03')))
        self.assertRaises(ConstraintError, list, protocol.decode(dt.Data('\x10')))
        self.assertEqual(4, list(protocol.decode(dt.Data('\x04')))[1][4])
        self.assertEqual(15, list(protocol.decode(dt.Data('\x0f')))[1][4])

    def test_parent_sequenceof_ends(self):
        text = """
            <protocol>
                <sequenceof name="bob">
                    <choice name="char:">
                        <field name="null:" length="8" value="0x0"> <end-sequenceof /></field>
                        <sequenceof name="dont get me" count="1">
                            <field name="char" length="8" type="text" />
                        </sequenceof>
                    </choice>
                </sequenceof>
            </protocol>"""
        protocol = xml.loads(text)[0]
        result = ""
        data = dt.Data("hello world\x00boo")
        for is_starting, name, entry, entry_data, value in protocol.decode(data):
            if not is_starting and entry.name == "char":
                result += value
        self.assertEqual("hello world", result)
        self.assertEqual("boo", data.bytes())

    def test_sequence_value(self):
        text = """
            <protocol>
                <sequence name="buffer">
                    <sequence name="middle endian" value="${byte 1:} * 16777216 + ${byte 2:} * 65536 + ${byte 3:} * 256 + ${byte 4:}" >
                        <field name="byte 2:" length="8" />
                        <field name="byte 1:" length="8" />
                        <field name="byte 4:" length="8" />
                        <field name="byte 3:" length="8" />
                    </sequence>
                    <field name="data" length="${middle endian} * 8" type="text" />
                </sequence>
            </protocol> """
        protocol = xml.loads(text)[0]
        result = ""
        data = dt.Data("\x00\x00\x13\x00run for your lives!boo")
        for is_starting, name, entry, entry_data, value in protocol.decode(data):
            if not is_starting and entry.name == "data":
                result = value
        self.assertEqual("run for your lives!", result)
        self.assertEqual("boo", data.bytes())

    def test_match_choice_entry(self):
        text = """
            <protocol>
                <sequence name="bob">
                    <choice name="valid items:">
                        <sequence name="option a:"><field name="length:" length="8" value="0x5" /></sequence>
                        <sequence name="option b:"><field name="length:" length="8" value="0x7" /></sequence>
                    </choice>
                    <field name="data" length="${valid items:.length:} * 8" type="text" />
                </sequence>
            </protocol>
            """
        protocol = xml.loads(text)[0]
        result = ""
        data = dt.Data("\x07chicken")
        for is_starting, name, entry, entry_data, value in protocol.decode(data):
            if not is_starting and entry.name == "data":
                result = value
        self.assertEqual("chicken", result)

    def test_length_validation(self):
        text = """
            <protocol>
                <sequence name="bob" length="15">
                    <field name="a" length="8" type="text" />
                    <field name="b" length="8" type="text" />
                </sequence>
            </protocol>
            """
        protocol = xml.loads(text)[0]
        result = ""
        self.assertRaises(ent.EntryDataError, list, protocol.decode(dt.Data('ab')))

    def test_common_elements_are_independant(self):
        """
        Test that decode references to common fields are used out of context.
        """
        # In this case, we want 'data a' to use the length item embedded in
        # 'length a', and not the item in 'length b'.
        text = """
            <protocol>
                <common>
                    <field name="length:" length="8" type="integer" />
                </common>
                <sequence name="bob">
                    <sequence name="length a">
                        <reference name="length:" />
                    </sequence>
                    <sequence name="length b">
                        <reference name="length:" />
                    </sequence>
                    <field name="data a" length="${length a.length:} * 8" type="text" />
                    <field name="data b" length="${length b.length:} * 8" type="text" />
                </sequence>
            </protocol>
            """
        protocol = xml.loads(text)[0]
        a = b = ""
        for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data("\x03\x06catrabbit")):
            if not is_starting:
                if entry.name == "data a":
                    a = value
                elif entry.name == "data b":
                    b = value
        self.assertEqual("cat", a)
        self.assertEqual("rabbit", b)

    def test_delayed_referenced_common_elements_are_independant(self):
        # Here we test that so called 'delayed referenced' objects are
        # independant (ie: that an embedded referenced object doesn't
        # affect an outer object).
        text = """
            <protocol>
                <common>
                    <field name="integer" length="8" min="48" max="57" type="text" />

                    <sequence name="array">
                        <field name="opener" length="8" value="0x5b" />
                        <sequenceof name="values">
                            <choice name="entry">
                                <field name="closer" length="8" value="0x5d"><end-sequenceof /></field>
                                <reference name="object" />
                            </choice>
                        </sequenceof>
                    </sequence>

                    <choice name="object">
                        <reference name="integer" />
                        <reference name="array" />
                    </choice>
                </common>
                <reference name="object" />
            </protocol>
            """
        protocol = xml.loads(text)[0]
        data = dt.Data("[12[34[56]7]8]unused")
        result = inst.decode(protocol, data)
        self.assertEqual("1", result.array.values[0].object.integer)
        self.assertEqual("2", result.array.values[1].object.integer)
        self.assertEqual("3", result.array.values[2].object.array.values[0].object.integer)
        self.assertEqual("4", result.array.values[2].object.array.values[1].object.integer)
        self.assertEqual("5", result.array.values[2].object.array.values[2].object.array.values[0].object.integer)
        self.assertEqual("6", result.array.values[2].object.array.values[2].object.array.values[1].object.integer)
        self.assertEqual("7", result.array.values[2].object.array.values[3].object.integer)
        self.assertEqual("8", result.array.values[3].object.integer)
        self.assertEqual("unused", data.bytes())

    def test_all_entries_in_lookup_tree(self):
        text = """
            <protocol>
                <common>
                    <choice name="dog">
                        <sequenceof name="rabbit" length="1">
                            <field name="hole" length="8" />
                        </sequenceof>
                    </choice>
                    <sequence name="length a">
                        <field name="length:" length="8" type="integer" />
                        <reference name="dog" />
                    </sequence>
                </common>
                <sequence name="bob">
                    <reference name="length a" />
                    <field name="data a" length="${length a.length:} * 8" type="text" />
                </sequence>
            </protocol>
            """
        protocol, common, lookup = xml.loads(text)
        entries = [protocol]
        names = set()
        while entries:
            entry = entries.pop()
            names.add(entry.name)
            self.assertTrue(entry in lookup, "%s isn't in the lookup tree!" % entry)
            entries.extend(child.entry for child in entry.children)
        self.assertEqual(set(['dog', 'rabbit', 'hole', 'length a', 'length:', 'bob', 'data a']), names)

    def test_referenced_common_entry(self):
        text = """
          <protocol>
             <common>
                 <field name="a" type="integer" length="8" />
             </common>
             <sequence name="b">
                <reference name="a" />
                <field name="b value" length="${a} * 8" type="integer" />
             </sequence>
          </protocol> """
        protocol, common, lookup = xml.loads(text)
        items = [value for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data("\x01\x07"))]
        self.assertEqual(1, items[2])
        self.assertEqual(7, items[4])

    def test_out_of_order_references(self):
        text = """
            <protocol>
                <common>
                    <sequence name="dog">
                        <reference name="foo" />
                    </sequence>

                    <sequence name="foo">
                        <reference name="cat" />
                    </sequence>

                    <sequence name="cat" >
                        <field name="length" length="8" type="integer" />
                    </sequence>
                </common>
                <reference name="dog" />
            </protocol>
            """
        protocol, common, lookup = xml.loads(text)
        for is_starting, name, entry, entry_data, value in protocol.decode(dt.Data('a')):
            if not is_starting and entry.name == "length":
                result = value
        self.assertEqual(ord('a'), result)

    def test_recursive_entry(self):
        text = """
            <protocol>
                <common>
                    <choice name="null terminating string:">
                        <field name="null:" length="8" value="0x0" />
                        <sequence name="non null:">
                            <field name="char" length="8" type="text" />
                            <reference name="null terminating string:" />
                        </sequence>
                    </choice>
                </common>
                <reference name="null terminating string:" />
            </protocol>
            """
        protocol, common, lookup = xml.loads(text)
        data = dt.Data('rabbit\0legs')
        result = ""
        for is_starting, name, entry, entry_data, value in protocol.decode(data):
            if not is_starting and entry.name == "char":
                result += value
        self.assertEqual("rabbit", result)
        self.assertEqual("legs", data.bytes())

    def test_string_constants(self):
        text = """
            <protocol>
              <sequence name="cat">
                <field name="bob" length="56" type="text" value="chicken" />
                <field name="bob" length="8" type="integer" value="73" />
              </sequence>
            </protocol>"""
        decoder = xml.loads(text)[0]
        items = list(decoder.decode(dt.Data("chicken\x49")))
        self.assertRaises(bdec.DecodeError, list, decoder.decode(dt.Data("chickan\x49")))
        self.assertRaises(bdec.DecodeError, list, decoder.decode(dt.Data("chicken\x48")))

    def test_expected_data_is_too_big(self):
        text = """
            <protocol>
              <field name="bob" length="8" value="0xFFFF" />
            </protocol>"""
        self.assertRaises(xml.XmlError, xml.loads, text)

    def test_cannot_use_end_sequenceof_in_reference(self):
        # There was a problem with using 'end-sequenceof' with common items...
        text = """
            <protocol>
               <common>
                  <field name="a" type="text" length="8" value="a" />
               </common>
               <sequenceof name="c">
                  <choice name="entry">
                     <reference name="a"><end-sequenceof /></reference>
                     <field name="data" length="8" />
                  </choice>
               </sequenceof>
           </protocol>
               """
        try:
            xml.loads(text)
        except xml.XmlError, ex:
            self.assertTrue("end-sequenceof cannot be used within a referenced item" in str(ex))

    def test_break_in_break(self):
        # There was a bug in the xml loader when an end-sequenceof was under two sequenceofs.
        text = """
           <protocol>
               <sequenceof name="strings">
                  <choice name="entry">
                     <field name="null" length="8" value="0x0" ><end-sequenceof/></field>
                     <sequenceof name="null terminated string">
                        <choice name="text char">
                            <field name="null" length="8" value="0x0"><end-sequenceof/></field>
                            <field name="char" length="8" type="text" />
                        </choice>
                     </sequenceof>
                  </choice>
               </sequenceof>
            </protocol> """
        decoder = xml.loads(text)[0]

        data = dt.Data("chicken\x00bob\x00\00")
        list(decoder.decode(data))
        self.assertEquals(0, len(data))

        data = dt.Data("chicken\x00bob\x00")
        try:
            list(decoder.decode(dt.Data("chicken\x00bob\x00")))
        except fld.FieldDataError, ex:
            self.assertEquals(dt.NotEnoughDataError, type(ex.error))

    def test_nameless_entry(self):
        text = """
           <protocol>
             <sequence name="a">
               <sequence> 
                 <field name="b" length="8" type="integer" />
                 <field length="8" value="0x3" type="integer" />
               </sequence>
             </sequence>
           </protocol>"""
        spec = xml.loads(text)[0]
        self.assertEqual("", spec.children[0].name)
        data = dt.Data("f\x03")
        items = list(value for is_starting, name, entry, data, value in spec.decode(data) if not is_starting)
        self.assertEqual(4, len(items))
        self.assertEqual(ord('f'), items[0])
        self.assertEqual(3, items[1])

    def test_different_name_of_reference_type(self):
        text = """
           <protocol>
             <common>
               <sequence name="digit" value="${number} - 48">
                 <field name="number" length="8" type="integer" min="48" max="57" />
               </sequence>
               <sequence name="2 digit text" value="${digit 1} * 10 + ${digit 2}">
                 <reference name="digit 1" type="digit" />
                 <reference name="digit 2" type="digit" />
               </sequence>
             </common>
             <sequence name="header">
               <field name="id" length="16" value="0x1234" />
               <reference name="length" type="2 digit text" />
             </sequence>
           </protocol>"""
        spec = xml.loads(text)[0]
        data = dt.Data("\x12\x3498")
        items = list((name, value) for is_starting, name, entry, data, value in spec.decode(data) if not is_starting)
        self.assertEqual(7, len(items))
        self.assertEqual('number', items[1][0])
        self.assertEqual(ord('9'), items[1][1])
        self.assertEqual('digit 1', items[2][0])
        self.assertEqual(9, items[2][1])

        self.assertEqual('number', items[3][0])
        self.assertEqual(ord('8'), items[3][1])
        self.assertEqual('digit 2', items[4][0])
        self.assertEqual(8, items[4][1])

        self.assertEqual('length', items[5][0])
        self.assertEqual(98, items[5][1])

    def test_sequence_expected_value(self):
        text = '''
           <protocol>
               <sequence name="a" value="${b} + ${c}" expected="7" >
                   <field name="b" length="8" />
                   <field name="c" length="8" />
               </sequence>
           </protocol>
           '''
        a = xml.loads(text)[0]
        list(a.decode(dt.Data('\x02\x05')))
        list(a.decode(dt.Data('\x07\x00')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x05\x01')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x02\x06')))

    def test_sequence_minimum_value(self):
        text = '''
           <protocol>
               <sequence name="a" value="${b} + ${c}" min="7" >
                   <field name="b" length="8" />
                   <field name="c" length="8" />
               </sequence>
           </protocol>
           '''
        a = xml.loads(text)[0]
        list(a.decode(dt.Data('\x06\x02')))
        list(a.decode(dt.Data('\x03\x04')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x03\x03')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x00\x06')))

    def test_sequence_maximum_value(self):
        text = '''
           <protocol>
               <sequence name="a" value="${b} + ${c}" max="7" >
                   <field name="b" length="8" />
                   <field name="c" length="8" />
               </sequence>
           </protocol>
           '''
        a = xml.loads(text)[0]
        list(a.decode(dt.Data('\x06\x01')))
        list(a.decode(dt.Data('\x01\x01')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x08\x00')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x03\x09')))

    def test_reference_expected_value(self):
        text = '''
            <protocol>
                <sequence name="a">
                   <reference name="id" type="dword" expected="18" />
                   <reference name="length" type="dword" />
                   <field name="data" length="${length} * 8" type="hex" />
                </sequence>

                <common>
                    <field name="dword" type="integer" length="32" />
                </common>
            </protocol>
            '''
        a = xml.loads(text)[0]
        list(a.decode(dt.Data('\x00\x00\x00\x12\x00\x00\x00\x04data')))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x00\x00\x00\x13\x00\x00\x00\x04data')))

    def test_signed_char(self):
        text = '''
            <protocol>
              <field name="a" length="8" type="signed integer" />
            </protocol>
            '''
        a = xml.loads(text)[0]
        data = dt.Data('\xff')
        items = list((name, value) for is_starting, name, entry, data, value in a.decode(data) if not is_starting)
        self.assertEqual(3, len(items))
        self.assertEqual(-1, items[-1][1])

    def test_error_when_little_endian_non_multiple_of_eight(self):
        text = '''
            <protocol>
              <field name="a" length="10" type="signed integer" encoding="little endian" />
            </protocol>
            '''
        self.assertRaises(xml.XmlError, xml.loads, text)

    def test_signed_litte_endian(self):
        text = '''
            <protocol>
              <field name="a" length="16" type="signed integer" encoding="little endian" />
            </protocol>
            '''
        a = xml.loads(text)[0]
        items = list((name, value) for is_starting, name, entry, data, value in a.decode(dt.Data('\xff\xff')) if not is_starting)
        self.assertEqual(-1, items[-1][1])

        items = list((name, value) for is_starting, name, entry, data, value in a.decode(dt.Data('\x01\x00')) if not is_starting)
        self.assertEqual(1, items[-1][1])

    def test_variable_length_signed_little_endian(self):
        text = '''
            <protocol>
              <sequence name="a">
                  <field name="length:" length="8" />
                  <field name="b" length="${length:} * 8" type="signed integer" encoding="little endian" />
              </sequence>
            </protocol>
            '''
        a = xml.loads(text)[0]
        data = dt.Data('\x02\xff\xff')
        items = list((name, value) for is_starting, name, entry, data, value in a.decode(data) if not is_starting)
        self.assertEqual(0, len(data))
        self.assertEqual(-1, items[-2][1])

        data = dt.Data('\x04\x01\x00\x00\x00')
        items = list((name, value) for is_starting, name, entry, data, value in a.decode(data) if not is_starting)
        self.assertEqual(0, len(data))
        self.assertEqual(1, items[-2][1])

    def test_optional_entry(self):
        # Test loading an optional entry
        text = '''
            <protocol>
                <sequence name="a">
                    <field name="has footer" length="8" />
                    <field name="data" length="8" />
                    <field name="footer" length="8" if="${has footer} > 0" />
                </sequence>
            </protocol>'''
        a = xml.loads(text)[0]

        print xml.save(a)
        # Test decoding without a footer
        list(a.decode(dt.Data('\x00\x00')))

        # Test decoding with a footer
        data = dt.Data('\x01\x00\x00')
        list(a.decode(data))
        self.assertEqual(0, len(data))
        self.assertRaises(ConstraintError, list, a.decode(dt.Data('\x01\x00')))

    def test_references_in_optional_entry(self):
        # Test that references are correctly resolved when they are in an
        # optional entry (issue196).
        text = '''
            <protocol>
                <sequence name="a">
                   <field name="exists:" length="8" />
                   <sequence name="b" if="${exists:}" >
                       <reference name="value" type="int32" />
                   </sequence>
                </sequence>

                <common>
                   <field name="int32" length="32" type="signed integer" />
                </common>
            </protocol>'''
        a = xml.loads(text)[0]

        # Test decoding when it isn't present
        data = dt.Data('\x00')
        list(a.decode(data))
        self.assertEqual(0, len(data))

        # Test decoding when it is present
        data = dt.Data('\x01\x00\x00\x00\x01')
        list(a.decode(data))
        self.assertEqual(0, len(data))

    def test_expression_references_unknown_entry(self):
        text = '''
            <protocol>
                <sequence name="a">
                    <field name="b" length="${c}" />
                </sequence>
            </protocol>'''
        try:
            xml.loads(text)
        except xml.XmlExpressionError, ex:
            self.assertEqual("<string>[4]: Expression error - binary 'b' " \
                    "(big endian) references unknown entry 'c'!" , str(ex))

    def test_conditional_reference(self):
        text = '''
            <protocol>
                <sequence name="a">
                    <field name="footer present:" length="8" />
                    <reference name="footer" if="${footer present:}" />
                </sequence>

                <common>
                    <sequence name="footer">
                        <field name="b" length="8" type="integer" />
                    </sequence>
                </common>
            </protocol>'''
        spec = xml.loads(text)[0]
        data = dt.Data('\x00')
        list(spec.decode(data))
        self.assertEquals(0, len(data))
        self.assertRaises(bdec.DecodeError, list, spec.decode(dt.Data('\x01')))
        data = dt.Data('\x01a')
        list(spec.decode(data))

    def test_correct_error_location(self):
        text = '''
            <protocol>
                <sequence name="a">
                    <field name="footer present:" length="8" />
                    <reference name="footer" if="${footer present:}" />
                </sequence>

                <common>
                    <sequence name="footer">
                        <field name="b" length="8" type="integer" />
                    </sequence>
                </common>
            </protocol>'''
        spec, common, lookup = xml.loads(text)
        self.assertEqual(3, lookup[spec][1])
        self.assertEqual(9, lookup[common['footer']][1])


class TestSave(unittest.TestCase):
    """Test decoding of the xml save functionality.

    This is the functionality that can create an xml specification from an
    in-memory representation."""

    def test_simple_field(self):
        a = fld.Field('a', length=8)
        assert_xml_equivalent('<protocol><field name="a" length="8" /></protocol>', xml.save(a))

    def test_field_expected_value(self):
        a = fld.Field('a', length=8, constraints=[Equals(dt.Data('\x63'))])
        assert_xml_equivalent('<protocol><field name="a" length="8" value="0x63" /></protocol>', xml.save(a))

    def test_text_field(self):
        a = fld.Field('a', format=fld.Field.TEXT, length=32)
        assert_xml_equivalent('<protocol><field name="a" type="text" length="4 * 8" /></protocol>', xml.save(a))

    def test_text_field_with_expected_value(self):
        a = fld.Field('a', format=fld.Field.TEXT, length=32, constraints=[Equals('abcd')])
        assert_xml_equivalent('<protocol><field name="a" type="text" length="4 * 8" value="abcd" /></protocol>', xml.save(a))

    def test_sequence(self):
        a = seq.Sequence('a', [fld.Field('b', length=8)])
        c = seq.Sequence('c', [a, fld.Field('d', length=16)])
        expected = """<protocol>
                        <sequence name="c">
                          <sequence name="a">
                             <field name="b" length="8" />
                          </sequence>
                          <field name="d" length="2 * 8" />
                        </sequence>
                      </protocol>"""
        assert_xml_equivalent(expected, xml.save(c))

    def test_sequenceof_with_count(self):
        a = sof.SequenceOf('a', fld.Field('b', length=8), count=4)
        expected = '<protocol><sequenceof name="a" count="4"><field name="b" length="8" /></sequenceof></protocol>'
        assert_xml_equivalent(expected, xml.save(a))

    def test_sequenceof_with_end_entry(self):
        a = fld.Field('a', length=8)
        b = sof.SequenceOf('b', seq.Sequence('c', [a]), count=None, end_entries=[a])
        expected = """<protocol>
                        <sequenceof name="b">
                          <sequence name="c">
                            <field name="a" length="8"><end-sequenceof/></field>
                          </sequence>
                        </sequenceof>
                      </protocol>"""
        assert_xml_equivalent(expected, xml.save(b))

    def test_choice(self):
        a = chc.Choice('a', [
            fld.Field('b', length=8, constraints=[Equals(dt.Data('\x01'))]),
            fld.Field('c', length=8, constraints=[Equals(dt.Data('\x02'))])])
        expected = """<protocol>
                        <choice name="a">
                          <field name="b" length="8" value="0x01" />
                          <field name="c" length="8" value="0x02" />
                        </choice>
                      </protocol>"""
        assert_xml_equivalent(expected, xml.save(a))

    def test_common_entries(self):
        a = fld.Field('a', length=8)
        b = seq.Sequence('b', [a, a])
        expected = """<protocol>
                        <sequence name="b">
                          <reference name="a" />
                          <reference name="a" />
                        </sequence>
                        <common>
                          <field name="a" length="8" />
                        </common>
                      </protocol>"""
        assert_xml_equivalent(expected, xml.save(b, [a, b]))

    def test_expression(self):
        a = seq.Sequence('a', [
            fld.Field('b', format=fld.Field.INTEGER, length=8),
            fld.Field('c', length=expr.compile('${a} * 8'))])
        expected = """<protocol>
                        <sequence name="a">
                          <field name="b" length="8" type="integer" />
                          <field name="c" length="(${a} * 8)" />
                        </sequence>
                      </protocol>"""
        assert_xml_equivalent(expected, xml.save(a))

    def test_small_field_with_expected_value(self):
        # Test saving a small field with length that isn't a multiple of
        # either...
        a = fld.Field('a', length=3, constraints=[Equals(dt.Data('\x02', 5))])
        expected = """
          <protocol>
            <field name="a" length="3" value="0x02" />
          </protocol>"""
        assert_xml_equivalent(expected, xml.save(a))

