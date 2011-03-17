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

import bdec.data as dt
from bdec.decode.entry import EntryDecoder

class SequenceDecoder (EntryDecoder):

    def _decode(self, data, context, name):
        yield (True, name, self.entry, data, None)
        for child in self.children:
            for embedded in self._decode_child(child, data, context):
                yield embedded
        value = None
        if self.entry.value is not None:
            value = self.entry.value.evaluate(context)
        yield (False, name, self.entry, dt.Data(), value)
