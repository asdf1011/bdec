#   Copyright (C) 2008-2010 Henry Ludemann
#   Copyright (C) 2010 PRESENSE Technologies GmbH
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
import operator
import unittest

from bdec.constraints import Equals, ConstraintError
from bdec.encode.entry import DataLengthError
import bdec.entry as ent
from bdec.expression import ValueResult
import bdec.data as dt
import bdec.field as fld

def query(context, entry, i, name):
    return context

class TestField(unittest.TestCase):
    def assertNearlyEqual(self, a, b):
        # Compare two numbers, checking for significant digits.
        if a == b:
            return True
        if b == 0:
            difference = a
        else:
            difference = (a-b) / (a+b)
        if abs(difference) > 1e-6:
            raise Exception('%s != %s (within 6 significant digits)' % (a, b))

    def test_decode(self):
        field = fld.Field("bob", 8)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, name, entry, entry_data, value in field.decode(data):
            calls.append((entry, entry_data))
        self.assertEqual(2, len(calls))
        self.assertEqual(field, calls[0][0])
        self.assertEqual(field, calls[1][0])
        self.assertEqual(1, int(calls[1][1]))
        self.assertEqual(0x7a, int(data))

    def _get_decode_value(self, hex, length, format, encoding=""):
        field = fld.Field("bob", length, format, encoding)
        data = dt.Data.from_hex(hex)
        calls = list(field.decode(data))
        return calls[1][4]

    def _get_encode_value(self, length, format, value, encoding="", constraints=[]):
        field = fld.Field("bob", length, format, encoding, constraints)
        result = field.encode(query, value)
        return reduce(operator.__add__, result)

    def test_binary_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.BINARY)
        self.assertEqual("0000 00010111", str(actual))

    def test_binary_type_to_unicode(self):
        actual = self._get_decode_value("017a", 12, fld.Field.BINARY)
        self.assertEqual(u"0000 00010111", unicode(actual))

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
        self.assertEqual("fe", result[1][3].get_hex())

    def test_encode(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        result = field.encode(query, 0x3f)
        self.assertEqual(0x3f, int(result.next()))

    def test_encoded_size_matches_expected_size(self):
        # When we specify a size for a field, what we actually encode should match it.
        text = fld.Field("bob", 48, format=fld.Field.TEXT)
        self.assertEqual("rabbit", text.encode(query, "rabbit").next().bytes())
        self.assertRaises(DataLengthError, list, text.encode(query, "boxfish"))

        binary = fld.Field("bob", 8, format=fld.Field.BINARY)
        self.assertEqual("\x39", binary.encode(query, "00111001").next().bytes())
        self.assertRaises(DataLengthError, list, binary.encode(query, "1011"))

        hex = fld.Field("bob", 8, format=fld.Field.HEX)
        self.assertEqual("\xe7", hex.encode(query, "e7").next().bytes())
        self.assertRaises(DataLengthError, list, hex.encode(query, "ecd"))

    def test_string_conversion(self):
        # Just test that we can convert fields to a string sanely... the actual format
        # doesn't matter.
        self.assertEqual("text 'bob' (ascii)", str(fld.Field("bob", 8, format=fld.Field.TEXT)))

    def test_bad_format_error(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        self.assertRaises(fld.BadFormatError, field.encode, lambda data, context, i, name: "rabbit", None)

    def test_encode_of_field_with_expected_value_fails_when_given_bad_data(self):
        field = fld.Field("bob", 8, constraints=[Equals(dt.Data('c'))])
        self.assertRaises(ConstraintError, field.encode(query, dt.Data("d")).next)

    def test_encode_of_field_with_expected_value_succeeds_with_missing_data(self):
        """
        Some outputs won't include expected data values.

        For example, xml-output may not display expected field values (to
        make for clearer output).
        """
        field = fld.Field("bob", 8, constraints=[Equals(dt.Data("c"))])
        def no_data_query(obj, entry, i, name):
            return ''
        self.assertEqual("c", field.encode(no_data_query, None).next().bytes())

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

    def test_float(self):
        actual = self._get_decode_value('00 00 a0 40', 32, fld.Field.FLOAT, fld.Field.LITTLE_ENDIAN)
        self.assertNearlyEqual(5.0, actual)

        actual = self._get_decode_value('66 66 82 c1', 32, fld.Field.FLOAT, fld.Field.LITTLE_ENDIAN)
        self.assertNearlyEqual(-16.3, actual)

    def test_big_endian_float(self):
        actual = self._get_decode_value('40 a0 00 00', 32, fld.Field.FLOAT, fld.Field.BIG_ENDIAN)
        self.assertNearlyEqual(5.0, actual)

        actual = self._get_decode_value('c1 82 66 66', 32, fld.Field.FLOAT, fld.Field.BIG_ENDIAN)
        self.assertNearlyEqual(-16.3, actual)

    def test_double(self):
        actual = self._get_decode_value('9a99 9999 9999 2040', 64, fld.Field.FLOAT, fld.Field.LITTLE_ENDIAN)
        self.assertEqual(8.3, actual)

        actual = self._get_decode_value('8e06 16f7 1022 e1c3', 64, fld.Field.FLOAT, fld.Field.LITTLE_ENDIAN)
        self.assertEqual(-9876543210123456789.0, actual)

    def test_float_encode(self):
        actual = self._get_encode_value(32, fld.Field.FLOAT, 5.0, fld.Field.LITTLE_ENDIAN)
        self.assertEqual('0000a040', actual.get_hex())

        actual = self._get_encode_value(32, fld.Field.FLOAT, -16.3, fld.Field.BIG_ENDIAN)
        self.assertNearlyEqual('c1826666', actual.get_hex())

    def test_double_encode(self):
        actual = self._get_encode_value(64, fld.Field.FLOAT, 8.3, fld.Field.LITTLE_ENDIAN)
        self.assertEqual('9a99999999992040', actual.get_hex())

        actual = self._get_encode_value(64, fld.Field.FLOAT, -9876543210123456789.0, fld.Field.LITTLE_ENDIAN)
        self.assertEqual('8e0616f71022e1c3', actual.get_hex())

    def test_data_is_available(self):
        a = fld.Field('a', length=8)
        self.assertRaises(fld.FieldDataError, list, a.decode(dt.Data()))

    def test_encode_binary_with_constraints(self):
        a = fld.Field('a', length=8, constraints=[Equals(5)])
        self.assertEqual(dt.Data('\x05'), reduce(operator.add, a.encode(query, '00000101')))
        self.assertRaises(ConstraintError, reduce, operator.add, a.encode(query, '00000111'))

