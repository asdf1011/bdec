#   Copyright (C) 2010 Henry Ludemann
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
import StringIO
import unittest

import bdec
import bdec.data as dt

class NonSeekable(StringIO.StringIO):
    def seek(self, *args):
        raise IOError()
    def tell(self):
        raise IOError()

class TestData(unittest.TestCase):
    def test_pop_empty_data(self):
        self.assertRaises(dt.NotEnoughDataError, int, dt.Data("").pop(1))

    def test_pop_negative_number(self):
        self.assertEqual("abcd", dt.Data("abcd").pop(32).bytes())
        self.assertRaises(dt.NotEnoughDataError, int, dt.Data("abcd").pop(33))

    def test_integer(self):
        self.assertEqual(3, int(dt.Data(chr(3))))

    def test_little_endian_integer(self):
        data = dt.Data.from_hex("010203")
        self.assertEqual(0x030201, data.get_little_endian_integer())

    def test_string(self):
        self.assertEqual("Some text", dt.Data("Some text").bytes())
        self.assertEqual("", dt.Data().bytes())

    def test_unaligned_string(self):
        # The first 4 bits (the 'a') will be popped, then the 5 byte
        # string, then it'll be converted to text.
        data = dt.Data.from_hex("a68656c6c6fa")
        data.pop(4)
        text = data.pop(5 * 8)
        self.assertEqual('hello', text.bytes())
    
    def test_pop(self):
        data = dt.Data.from_hex("f0")
        self.assertEqual(0x7, int(data.pop(3)))
        self.assertEqual(0x10, int(data))

    def test_hex(self):
        data = dt.Data.from_hex("f0ee9601")
        self.assertEqual(0xf0, int(data.pop(8)))
        self.assertEqual(0xee, int(data.pop(8)))
        self.assertEqual(0x96, int(data.pop(8)))
        self.assertEqual(0x01, int(data.pop(8)))

    def test_hexstring(self):
        data = dt.Data.from_hex("f0ee9601")
        self.assertEqual("f0ee9601", data.get_hex())

    def test_encode_little_endian(self):
        data = dt.Data.from_int_little_endian(10000, 16)
        self.assertEqual(16, len(data))
        self.assertEqual(10000, data.get_little_endian_integer())

    def test_encode_big_endian(self):
        data = dt.Data.from_int_big_endian(10000, 16)
        self.assertEqual(16, len(data))
        self.assertEqual(10000, int(data))

    def test_integer_too_big(self):
        self.assertEqual(chr(255), dt.Data.from_int_big_endian(255, 8).bytes())
        self.assertRaises(dt.IntegerTooLongError, dt.Data.from_int_big_endian, 255, 7)
        self.assertRaises(dt.IntegerTooLongError, dt.Data.from_int_big_endian, 100000, 7)

    def test_encode_length(self):
        data = dt.Data.from_int_big_endian(0x3e, 7)
        self.assertEqual(7, len(data))
        self.assertEqual(0x3e, int(data))

    def test_convert_binary_text(self):
        self.assertEqual(3, int(dt.Data.from_binary_text('000011')))
        self.assertEqual(17, int(dt.Data.from_binary_text('010001')))
        self.assertEqual(255, int(dt.Data.from_binary_text('11111111')))
        self.assertEqual(256, int(dt.Data.from_binary_text('1 00000000')))
        data = dt.Data.from_hex('78f638fd')
        self.assertEqual('78f638fd', dt.Data.from_binary_text(data.get_binary_text()).get_hex())

    def test_to_and_from_hex(self):
        hex = dt.Data('blah blah').get_hex()
        self.assertEqual('blah blah', dt.Data.from_hex(hex).bytes())

    def test_adding_data(self):
        self.assertEqual("chicken little", (dt.Data("chicken ") + dt.Data("little")).bytes())
        self.assertEqual('1abcd', (dt.Data('1') + dt.Data('abcd')).bytes())
        self.assertEqual('1234a', (dt.Data('1234') + dt.Data('a')).bytes())
        self.assertEqual('\x7c', (dt.Data('\x70', 0, 4) + dt.Data('\x0c', 4, 8)).bytes())

    def test_add_data_with_unused(self):
        self.assertEqual('ab', (dt.Data('ax', 0, 8) + dt.Data('b')).bytes())

    def test_adding_empty_unaligned(self):
        self.assertEqual(dt.Data(), dt.Data('', 4, 4) + dt.Data('', 7, 7))

    def test_equality(self):
        self.assertEqual(dt.Data.from_binary_text('1110'), dt.Data.from_hex('e0').pop(4))

    def test_unaligned_bits(self):
        self.assertEqual(0x2d, int(dt.Data.from_binary_text("010") + dt.Data.from_binary_text("1101")))

    def test_hex_conversion(self):
        self.assertEqual("\x23\x45\x67", dt.Data.from_hex("23 45 67").bytes())

    def test_conversion_needs_bytes(self):
        self.assertRaises(dt.ConversionNeedsBytesError, dt.Data.bytes, dt.Data("00", 0, 4))
        data = dt.Data.from_hex('ab')
        self.assertRaises(dt.ConversionNeedsBytesError, dt.Data.bytes, data.pop(4))

    def test_empty(self):
        data = dt.Data()
        self.assertTrue(data.empty())

        # Now create some data that should have more data then it does
        data = dt.Data('', 0, 8)
        self.assertTrue(not data.empty())
        self.assertRaises(dt.NotEnoughDataError, int, data)
        
        # Now create data that has more buffer available, but we tell it
        # the length is at an end.
        data = dt.Data("1234").pop(8)
        self.assertTrue(not data.empty())
        data.pop(8)
        self.assertTrue(data.empty())

    def test_bad_encoding(self):
        data = dt.Data('\xb2')
        self.assertRaises(dt.BadTextEncodingError, dt.Data.text, data, "ascii")

    def test_file_buffer(self):
        buffer = StringIO.StringIO()
        buffer.write('\x04abcd')
        data = dt.Data(buffer)
        self.assertEqual(4, int(data.pop(8)))
        self.assertEqual('abcd', data.bytes())

    def test_not_enough_data(self):
        # There was a bug in the size of available data we were popping; check
        # the sizes reported in the exception.
        data = dt.Data('abcd', 8, 48)
        try:
            data.text('ascii')
            self.fail('NotEnoughDataError not thrown!')
        except dt.NotEnoughDataError, ex:
            pass
        self.assertEqual(40, ex.requested)
        self.assertEqual(24, ex.available)

    def test_non_seeking_file(self):
        file = NonSeekable('abcdef')
        data = dt.Data(file)
        self.assertEqual('abc', data.pop(24).text('ascii'))
        self.assertEqual(ord('d'), int(data.pop(8)))
        self.assertEqual('ef', data.pop(16).text('ascii'))

        self.assertRaises(dt.NotEnoughDataError, int, data.pop(1))

    def test_invalid_binary_text(self):
        try:
            dt.Data.from_binary_text('abcd')
            self.fail('Whoops, from_binary_test should have failed!')
        except dt.InvalidBinaryTextError, ex:
            self.assertEqual("Invalid binary text 'abcd'", str(ex))

    def test_large_add(self):
        self.assertEqual('a' * 10001, (dt.Data('a') + dt.Data('a' * 10000)).bytes())
        self.assertEqual('a' * 10001, (dt.Data('a' * 10000) + dt.Data('a')).bytes())

    def test_add_unknown_length(self):
        try:
            a = dt.Data('', 0, 4) + dt.Data('b')
            self.fail('Should have thrown NotEnoughDataError...')
        except dt.NotEnoughDataError, ex:
            self.assertEqual('Asked for 4 bits, but only have 0 bits available!', str(ex))

    def test_len_not_enough_data(self):
        self.assertRaises(dt.NotEnoughDataError, len, dt.Data('', 4))

    def test_add_not_from_start(self):
        # There was a bug where it didn't correctly adjust the left start when
        # creating a new data object.
        data = dt.Data('abcd\x01\x02\x03\x04')

        # Remove data from the from of the data
        data.pop(36)
        data = data + dt.Data('\x00', 0, 4)
        self.assertEqual('\x10\x20\x30\x40', data.bytes())

    def test_join_single_bit(self):
        data = dt.Data('\x01', 7, 8)
        self.assertEqual(1, int(data))
        joined = reduce(operator.add, [data], dt.Data())
        self.assertEqual(1, len(joined))
        self.assertEqual(1, int(joined))

    def test_add_single_bit_on_right(self):
        a = dt.Data('\x00', 5, 8)
        b = dt.Data('\x01', 7, 8)
        self.assertEqual('0001', (a + b).get_binary_text())

    def test_add_single_bit_on_left(self):
        a = dt.Data('\x01', 7, 8)
        b = dt.Data('\x00', 5, 8)
        self.assertEqual('1000', (a + b).get_binary_text())

    def test_add_single_bit_with_overflow(self):
        # This tests that when the left data shifts all data to the next byte
        # as part of the shift operation.
        a = dt.Data('\x01', 7, 8)
        b = dt.Data('\x0f\xff', 4, 16)
        self.assertEqual('11111 11111111', (a + b).get_binary_text())
