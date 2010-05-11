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

import unittest

from bdec.entry import Entry
from bdec.spec.references import References

class TestReferences(unittest.TestCase):
    def test_common_references(self):
        # Test that we correctly resolve the case where common entries resolve
        # one another.
        references = References()
        a_ref = references.get_common('b', 'a')
        a = Entry('a', None, [])
        items = references.resolve([a_ref, a])
        self.assertEqual(2, len(items))
        # What should this be??
        self.assertEqual(a, items[0])
        self.assertEqual(a, items[1])
