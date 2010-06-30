#   Copyright (C) 2008-2009 Henry Ludemann
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

from bdec.encode.entry import EntryEncoder

class FieldEncoder(EntryEncoder):
    def _encode(self, query, value, context):
        yield self.entry.encode_value(value)

    def _fixup_value(self, value):
        expected = self.entry.expected
        if expected is not None and value in [None, '']:
            # We handle strings as a prompt to use the expected value. This is
            # because the named item may be in the output, but not necessarily
            # the value (eg: in the xml representation, it is clearer to not
            # display the expected value).
            value = self.entry.decode_value(expected)
        return value
