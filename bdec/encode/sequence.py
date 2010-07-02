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

import operator

from bdec.data import Data
from bdec.encode.entry import EntryEncoder
from bdec.inspect.solver import solve

class SequenceEncoder(EntryEncoder):
    def _encode(self, query, value, context, is_hidden):
        # We encode sequences in reverse, as earlier hidden fields and
        # sequences cannot always be encoded without information from the later
        # encoded elements. For example, a length field cannot be encoded
        # without knowing the length of the field which it is to encode.
        #
        # FIXME: We should do a proper dependancy analysis, and only rearrage
        # entries as required (for example, this logic will fail if a later
        # entry requires the knowledge of the encoded length of an earlier
        # entry).
        if self.entry.value:
            # Update the context with the detected parameters
            self._solve(self.entry.value, value, context)

        sequence_data = []
        for child in reversed(self.children):
            data = reduce(operator.add, self._encode_child(child, query, value, 0, context, is_hidden), Data())
            sequence_data.append(data)
        for data in reversed(sequence_data):
            yield data

