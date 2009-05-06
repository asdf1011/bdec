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

from bdec.constraints import Equals, ConstraintError
import bdec.entry as ent
import bdec.data as dt
import bdec.field as fld

class TestField(unittest.TestCase):
    def test_decode(self):
        field = fld.Field("bob", 8)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, name, entry, entry_data, value in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        self.assertEqual(field, calls[0])
        self.assertEqual(field, calls[1])
        self.assertEqual(1, int(calls[1].data))
        self.assertEqual(0x7a, int(data))

    def _get_decode_value(self, hex, length, format, encoding=""):
        field = fld.Field("bob", length, format, encoding)
        data = dt.Data.from_hex(hex)
        calls = list(field.decode(data))
        return calls[1][4]

    def test_binary_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.BINARY)
        self.assertEqual("0000 00010111", str(actual))

    def test_hexstring_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.HEX)
        self.assertEqual("017", str(actual))

    def test_string_type(self):
        raw = "chicken"
        encoded = "".join(hex(ord(char))[2:] for char in raw)
        actual = self._get_decode_value("" + encoded, 8 * len(raw), fld.Field.TEXT, "ascii")
        self.assertEqual("chicken", actual)

    def test_little_endian(self):
        actual = self._get_decode_value("0008", 16, fld.Field.INTEGER, fld.Field.LITTLE_ENDIAN)
        self.assertEqual(8 * 256, actual)

    def test_big_endian(self):
        actual = self._get_decode_value("0008", 16, fld.Field.INTEGER, fld.Field.BIG_ENDIAN)
        self.assertEqual(8, actual)

    def test_bad_expected_data(self):
        field = fld.Field("bob", 8, constraints=[Equals(0xf8)])
        data = dt.Data.from_hex("f7")
        self.assertRaises(ConstraintError, lambda: list(field.decode(data)))

    def test_good_expected_data(self):
        field = fld.Field("bob", 8, constraints=[Equals(0xfe)])
        data = dt.Data.from_hex("fe")
        result = list(field.decode(data))
        self.assertEqual(2, len(result))
        self.assertEqual("fe", result[1][2].data.get_hex())

    def test_encode(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        result = field.encode(None, 0x3f)
        self.assertEqual(0x3f, int(result.next()))

    def test_encoded_size_matches_expected_size(self):
        """
        When we specify a size for a field, what we actually encode should match it.
        """
        text = fld.Field("bob", 48, format=fld.Field.TEXT)
        self.assertEqual("rabbit", text.encode(None, "rabbit").next().bytes())
        self.assertRaises(ent.DataLengthError, list, text.encode(None, "boxfish"))

        binary = fld.Field("bob", 8, format=fld.Field.BINARY)
        self.assertEqual("\x39", binary.encode(None, "00111001").next().bytes())
        self.assertRaises(ent.DataLengthError, list, binary.encode(None, "1011"))

        hex = fld.Field("bob", 8, format=fld.Field.HEX)
        self.assertEqual("\xe7", hex.encode(None, "e7").next().bytes())
        self.assertRaises(ent.DataLengthError, list, hex.encode(None, "ecd"))

    def test_string_conversion(self):
        # Just test that we can convert fields to a string sanely... the actual format
        # doesn't matter.
        self.assertEqual("text 'bob' (ascii)", str(fld.Field("bob", 8, format=fld.Field.TEXT)))

    def test_bad_format_error(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        self.assertRaises(fld.BadFormatError, field.encode(lambda name, context: "rabbit", None).next)

    def test_encode_of_field_with_expected_value_fails_when_given_bad_data(self):
        field = fld.Field("bob", 8, constraints=[Equals(dt.Data('c'))])
        self.assertRaises(ConstraintError, field.encode(None, "d").next)

    def test_encode_of_field_with_expected_value_succeeds_with_missing_data(self):
        """
        Some outputs won't include expected data values.

        For example, xml-output may not display expected field values (to
        make for clearer output).
        """
        field = fld.Field("bob", 8, constraints=[Equals(dt.Data("c"))])
        def no_data_query(obj, name):
            return ''
        self.assertEqual("c", field.encode(no_data_query, None).next().bytes())

    def test_listener(self):
        field = fld.Field("bob", 8)
        callbacks = []
        field.add_listener(lambda entry, length, context: callbacks.append((entry, length)))
        self.assertEqual(0, len(callbacks))
        list(field.decode(dt.Data('a')))
        self.assertEqual('a',  callbacks[0][0].data.bytes())
        self.assertEqual(8,  callbacks[0][1])

    def test_range(self):
        field = fld.Field("bob", 8, min=8, max=15)
        self.assertRaises(fld.BadRangeError, list, field.decode(dt.Data("\x07")))
        self.assertRaises(fld.BadRangeError, list, field.decode(dt.Data("\x10")))
        list(field.decode(dt.Data("\x0F")))
        list(field.decode(dt.Data("\x08")))

        # Lets try printing that exception...
        try:
            list(field.decode(dt.Data("\x07")))
            self.fail("Exception not thrown!")
        except fld.BadRangeError, ex:
            text = str(ex)

    def test_range(self):
        field = fld.Field("bob", 8)
        self.assertEqual(8, field.range().min)
        self.assertEqual(8, field.range().max)
