#!/usr/bin/env python
import unittest

import bdec.entry as ent
import bdec.data as dt
import bdec.field as fld

class TestField(unittest.TestCase):
    def test_decode(self):
        field = fld.Field("bob", 8)
        data = dt.Data.from_hex("017a")

        calls = []
        for is_starting, entry, entry_data, value in field.decode(data):
            calls.append(entry)
        self.assertEqual(2, len(calls))
        self.assertEqual(field, calls[0])
        self.assertEqual(field, calls[1])
        self.assertEqual(1, int(calls[1].data))
        self.assertEqual(0x7a, int(data))

    def test_must_decode_before_querying_value(self):
        field = fld.Field("bob", 8)
        self.assertRaises(fld.FieldNotDecodedError, field.get_value)

    def _get_decode_value(self, hex, length, format, encoding=""):
        field = fld.Field("bob", length, format, encoding)
        data = dt.Data.from_hex(hex)
        calls = list(field.decode(data))
        return calls[1][3]

    def test_binary_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.BINARY)
        self.assertEqual("0000 00010111", actual)

    def test_hexstring_type(self):
        actual = self._get_decode_value("017a", 12, fld.Field.HEX)
        self.assertEqual("017", actual)

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
        field = fld.Field("bob", 8, expected=dt.Data.from_hex('fe'))
        data = dt.Data.from_hex("f7")
        self.assertRaises(fld.BadDataError, lambda: list(field.decode(data)))

    def test_good_expected_data(self):
        field = fld.Field("bob", 8, expected=dt.Data.from_hex('fe'))
        data = dt.Data.from_hex("fe")
        result = list(field.decode(data))
        self.assertEqual(2, len(result))
        self.assertEqual("fe", result[1][1].data.get_hex())

    def test_encode(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        result = field.encode(lambda name, context: 0x3f, None)
        self.assertEqual(0x3f, int(result.next()))

    def test_encoded_size_matches_expected_size(self):
        """
        When we specify a size for a field, what we actually encode should match it.
        """
        text = fld.Field("bob", 48, format=fld.Field.TEXT)
        self.assertEqual("rabbit", str(text.encode(lambda name, context: "rabbit", None).next()))
        self.assertRaises(ent.DataLengthError, list, text.encode(lambda name, context: "boxfish", None))

        binary = fld.Field("bob", 8, format=fld.Field.BINARY)
        self.assertEqual("\x39", str(binary.encode(lambda name, context: "00111001", None).next()))
        self.assertRaises(ent.DataLengthError, list, binary.encode(lambda name, context: "1011", None))

        hex = fld.Field("bob", 8, format=fld.Field.HEX)
        self.assertEqual("\xe7", str(hex.encode(lambda name, context: "e7", None).next()))
        self.assertRaises(ent.DataLengthError, list, hex.encode(lambda name, context: "ecd", None))

    def test_string_conversion(self):
        # Just test that we can convert fields to a string sanely... the actual format
        # doesn't matter.
        self.assertEqual("text 'bob' (ascii)", str(fld.Field("bob", 8, format=fld.Field.TEXT)))

    def test_bad_format_error(self):
        field = fld.Field("bob", 8, format=fld.Field.INTEGER)
        self.assertRaises(fld.BadFormatError, field.encode(lambda name, context: "rabbit", None).next)

    def test_encode_of_missing_visible_field_with_expected_value_fails(self):
        field = fld.Field("bob", 8, expected=dt.Data("c"))
        class MissingField:
            pass
        def fail_query(obj, name):
            raise MissingField()
        self.assertRaises(MissingField, field.encode(fail_query, None).next)

    def test_encode_of_field_with_expected_value_fails_when_given_bad_data(self):
        field = fld.Field("bob", 8, fld.Field.TEXT, expected=dt.Data("c"))
        def bad_data_query(obj, name):
            return "d"
        self.assertRaises(fld.BadDataError, field.encode(bad_data_query, None).next)

    def test_encode_of_field_with_expected_value_succeeds_with_missing_data(self):
        """
        Some outputs won't include expected data values.

        For example, xml-output may not display expected field values (to
        make for clearer outptu).
        """
        field = fld.Field("bob", 8, expected=dt.Data("c"))
        def no_data_query(obj, name):
            return ""
        self.assertEqual("c", str(field.encode(no_data_query, None).next()))

    def test_listener(self):
        field = fld.Field("bob", 8)
        callbacks = []
        field.add_listener(lambda entry, length, context: callbacks.append((entry, length)))
        self.assertEqual(0, len(callbacks))
        list(field.decode(dt.Data('a')))
        self.assertEqual('a',  str(callbacks[0][0].data))
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

    def test_bad_expected_length(self):
        self.assertRaises(fld.FieldDataError, fld.Field, "bob", 8, expected=dt.Data('ab'))

if __name__ == "__main__":
    unittest.main()
