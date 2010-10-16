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

    def _range(self, ignore_entries):
        minimum = min(child.entry.range(ignore_entries).min for child in self.children)
        maximum = max(child.entry.range(ignore_entries).max for child in self.children)
        return bdec.entry.Range(minimum, maximum)
