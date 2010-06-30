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

from bdec import DecodeError
from bdec.encode.entry import EntryEncoder, MissingInstanceError

class ChoiceEncoder(EntryEncoder):
    def _get_context(self, query, parent, offset):
        try:
            return query(parent, self.entry, offset)
        except MissingInstanceError:
            # Choice entries can be completely hidden
            return parent

    def _encode(self, query, value, context):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it.
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_encoded = 0
                for data in self._encode_child(child, query, value, 0, context):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        return self._encode_child(best_guess, query, value, 0, context)
