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


import bdec.data as dt
import bdec.entry

class Choice(bdec.entry.Entry):
    """
    An entry that can be one of many entries.

    The first entry to decode correctly will be used.
    """

    def __init__(self, name, children, length=None):
        bdec.entry.Entry.__init__(self, name, length, children)

        assert len(children) > 0

    def _get_context(self, query, parent):
        try:
            return query(parent, self)
        except bdec.entry.MissingInstanceError:
            # Choice entries can be completely hidden
            return parent

    def _encode(self, query, value):
        # We attempt to encode all of the embedded items, until we find
        # an encoder capable of doing it.
        best_guess = None
        best_guess_bits = 0
        for child in self.children:
            try:
                bits_encoded = 0
                child_value = child.entry.get_context(query, value)
                for data in child.entry.encode(query, child_value):
                    bits_encoded += len(data)

                # We successfully encoded the entry!
                best_guess = child
                break
            except bdec.DecodeError:
                if best_guess is None or bits_encoded > best_guess_bits:
                    best_guess = child
                    best_guess_bits = bits_encoded

        child_value = best_guess.entry.get_context(query, value)
        return best_guess.entry.encode(query, child_value)

    def _range(self, ignore_entries):
        minimum = min(child.entry.range(ignore_entries).min for child in self.children)
        maximum = max(child.entry.range(ignore_entries).max for child in self.children)
        return bdec.entry.Range(minimum, maximum)
