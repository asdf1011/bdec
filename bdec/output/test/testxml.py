#   Copyright (C) 2008 Henry Ludemann
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

import bdec.choice as chc
import bdec.data as dt
import bdec.entry as ent
import bdec.field as fld
import bdec.output.xmlout as xml
import bdec.sequence as seq
import bdec.sequenceof as sof
import bdec.expression as expr

class TestXml(unittest.TestCase):
    def test_field(self):
        field = fld.Field("bob", 8)
        text = xml.to_string(field, dt.Data.from_hex('8e'))
        self.assertEqual("<bob>10001110</bob>\n", text)

    def test_hidden_entry(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        text = xml.to_string(sequence, dt.Data.from_hex('6e7a6970'))
        self.assertEqual("<bob>\n    <dog>zip</dog>\n</bob>\n", text)

    def test_xml_encode(self):
        text = "<blah><cat>5</cat><dog>18</dog></blah>"
        sequence = seq.Sequence("blah", [
            fld.Field("cat", 8, fld.Field.INTEGER),
            fld.Field("dog", 8, fld.Field.INTEGER)])
        data = reduce(lambda a,b:a+b, xml.encode(sequence, text))
        self.assertEqual("\x05\x12", data.bytes())

    def test_choice_encode(self):
        a = fld.Field('a', 8, expected=dt.Data('a'))
        b = fld.Field('b', 8, expected=dt.Data('b'))
        choice = chc.Choice('blah', [a, b])
        text = "<b />"
        data = reduce(lambda a,b:a+b, xml.encode(choice, text))
        self.assertEqual("b", data.bytes())

    def test_verbose(self):
        sequence = seq.Sequence("bob", [
            fld.Field("cat:", 8, fld.Field.INTEGER),
            fld.Field("dog", 24, fld.Field.TEXT)])
        text = xml.to_string(sequence, dt.Data.from_hex('6d7a6970'), verbose=True)
        expected = """<bob>
    <cat_>109<!-- hex (1 bytes): 6d --></cat_>
    <dog>zip<!-- hex (3 bytes): 7a6970 --></dog>
</bob>
"""
        self.assertEqual(expected, text)

        # Now test that we can re-encode verbose generated xml...
        data = reduce(lambda a,b:a+b, xml.encode(sequence, text))
        self.assertEqual("mzip", data.bytes())

    def test_encode_sequenceof(self):
        spec = sof.SequenceOf('cat', fld.Field('dog', 8, fld.Field.TEXT), 4)
        text = "<cat> <dog>a</dog> <dog>b</dog> <dog>c</dog> <dog>d</dog> </cat>"
        data = reduce(lambda a,b:a+b, xml.encode(spec, text))
        self.assertEqual("abcd", data.bytes())

    def test_re_encoding_of_whitespace(self):
        spec = fld.Field('blah', 64, fld.Field.TEXT)
        text = xml.to_string(spec, dt.Data('  bob   '))
        data = reduce(lambda a,b:a+b, xml.encode(spec, text))
        self.assertEqual("  bob   ", data.bytes())

    def test_nameless_entry(self):
        hidden = fld.Field('', 8, fld.Field.INTEGER, expected=dt.Data('\x00'))
        spec = seq.Sequence('blah', [hidden])
        text = xml.to_string(spec, dt.Data('\x00'))
        self.assertEqual('<blah>\n</blah>\n', text)

    def test_verbose_nameless_entry(self):
        hidden = fld.Field('', 8, fld.Field.INTEGER, expected=dt.Data('\x00'))
        spec = seq.Sequence('blah', [hidden])
        text = xml.to_string(spec, dt.Data('\x00'), verbose=True)
        self.assertEqual('<blah>\n    <_hidden>0<!-- hex (1 bytes): 00 --></_hidden>\n</blah>\n', text)

    def test_different_child_name(self):
        digit = fld.Field('digit:', length=8)
        number = seq.Sequence('number', [digit], value=expr.compile("${digit:} - 48") )
        header = seq.Sequence('header', [ent.Child('length', number), fld.Field('data', length=expr.compile('${length} * 8'), format=fld.Field.TEXT)])
        text = xml.to_string(header, dt.Data('5abcde'))
        self.assertEqual('<header>\n    <length>5</length>\n    <data>abcde</data>\n</header>\n', text)

