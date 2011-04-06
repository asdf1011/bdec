#   Copyright (C) 2010 Henry Ludemann
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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#!/usr/bin/env python
import unittest

import bdec.choice as chc
from bdec.constraints import Equals
from bdec.encode.sequenceof import InvalidSequenceOfCount
import bdec.expression as expr
import bdec.data as dt
import bdec.field as fld
from bdec.output.instance import encode
import bdec.sequence as seq
import bdec.sequenceof as sof


class TestSequenceOf(unittest.TestCase):
    def test_sequence_of_field(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, fld.Field.INTEGER), 3)

        actual = []
        for is_starting, name, entry, entry_data, value in sequenceof.decode(dt.Data.from_hex("fb028c")):
            if not is_starting:
                data = value
                actual.append((entry.name, data))

        expected = [("cat", 0xfb),
            ("cat", 0x02),
            ("cat", 0x8c),
            ("blah", None)]
        self.assertEqual(expected, actual)

    def test_encode(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), 3)
        data = [5, 9, 0xf6]
        data = encode(sequenceof, data)
        self.assertEqual("\x05\x09\xf6", data.bytes())

    def test_invalid_encoding_count(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), 3)
        data = [5, 9]
        self.assertRaises(InvalidSequenceOfCount, encode, sequenceof, data)

    def test_greedy_decode(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.TEXT), None, length=None)
        rawdata = dt.Data("date")
        items = [value for is_starting, name, entry, data, value in sequenceof.decode(rawdata) if isinstance(entry, fld.Field) and not is_starting]
        self.assertEqual(4, len(items))
        self.assertEqual('date', ''.join(items))
        self.assertEqual('', rawdata.bytes())

    def test_length_decode(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.TEXT), None, length=32)
        rawdata = dt.Data("dateunused")
        items = [value for is_starting, name, entry, data, value in sequenceof.decode(rawdata) if isinstance(entry, fld.Field) and not is_starting]
        self.assertEqual(4, len(items))
        self.assertEqual('date', ''.join(items))
        self.assertEqual('unused', rawdata.bytes())

    def test_run_out_of_data_length(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.TEXT), None, length=32)
        rawdata = dt.Data("date")
        items = [value for is_starting, name, entry, data, value in sequenceof.decode(rawdata) if isinstance(entry, fld.Field) and not is_starting]
        self.assertEqual(4, len(items))
        self.assertEqual('date', ''.join(items))
        self.assertEqual('', rawdata.bytes())

    def test_encoding_greedy_sequenceof(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), None)
        data = [5, 9, 0xf6]
        data = encode(sequenceof, data)
        self.assertEqual("\x05\x09\xf6", data.bytes())

    def test_negative_count(self):
        sequenceof = sof.SequenceOf("blah", fld.Field("cat", 8, format=fld.Field.INTEGER), -1)
        self.assertRaises(sof.NegativeSequenceofLoop, list, sequenceof.decode(dt.Data("")))

    def test_end_entries(self):
        null = fld.Field("null", 8, constraints=[Equals(dt.Data('\x00'))])
        char = fld.Field("char", 8)
        sequenceof = sof.SequenceOf("null terminated string", chc.Choice('entry', [null, char]), None, end_entries=[null])
        actual = []
        data = dt.Data("hello\x00bob")
        result = ""
        for is_starting, name, entry, entry_data, value in sequenceof.decode(data):
            if not is_starting and entry.name == "char":
                result += entry_data.bytes()

        self.assertEqual("hello", result)
        self.assertEqual("bob", data.bytes())

    def test_sequenceof_ended_early(self):
        null = fld.Field("null", 8, constraints=[Equals(dt.Data('\x00'))])
        char = fld.Field("char", 8)
        a = sof.SequenceOf('a', chc.Choice('b', [null, char]), expr.parse('5'), end_entries=[null])

        # Make sure we decode correctly given sane values
        list(a.decode(dt.Data('abcd\x00')))
        # Check the exception when the null is found before the count runs out
        self.assertRaises(sof.SequenceEndedEarlyError, list, a.decode(dt.Data('abc\x00')))
        # Check the exception when the count is reached before the end
        self.assertRaises(sof.SequenceofStoppedBeforeEndEntry, list, a.decode(dt.Data('abcde')))
