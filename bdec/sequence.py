#   Copyright (C) 2008 Henry Ludemann
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

class Sequence(bdec.entry.Entry):
    """
    A sequence type protocol entry.

    A sequence protocol entry is made up of multiple other
    entry types, and they are decoded one after the other.
    All of the child protocol entries must be decoded for
    the sequence to successfully decode.

    A sequence object may be assigned a value, derived from
    the child elements. This allows techniques such as
    lookup tables, and alternate integer encoding methods.
    """

    def __init__(self, name, children, value=None, length=None, constraints=[]):
        bdec.entry.Entry.__init__(self, name, length, children, constraints)
        self.value = value

    def _encode(self, query, value):
        for child in self.children:
            child_value = child.entry.get_context(query, value)
            for data in child.entry.encode(query, child_value):
                yield data
            
    def _range(self, ignore_entries):
        return sum((child.entry.range(ignore_entries) for child in self.children), bdec.entry.Range(0, 0))
