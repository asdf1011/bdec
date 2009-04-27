#   Copyright (C) 2009 Henry Ludemann
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

from bdec import DecodeError

class ConstraintError(DecodeError):
    def __init__(self, entry, actual, comparison, limit):
        DecodeError.__init__(self, entry)
        self._error = '%s %s %s' % (repr(actual), comparison, repr(limit))

    def __str__(self):
        return '%s constaint error; %s' % (self.entry, self._error)


class Minimum:
    def __init__(self, limit):
        self.limit = limit
        self.type = '<'

    def check(self, entry, value):
        if isinstance(value, basestring):
            # It is useful to check the bounds of a text character...
            value = ord(value)
        if int(value) < self.limit:
            raise ConstraintError(entry, int(value), '<', self.limit)

class Maximum:
    def __init__(self, limit):
        self.limit = limit
        self.type = '>'

    def check(self, entry, value):
        if isinstance(value, basestring):
            # It is useful to check the bounds of a text character...
            value = ord(value)
        if int(value) > self.limit:
            raise ConstraintError(entry, int(value), '>', self.limit)

class Equals:
    def __init__(self, expected):
        self.limit = expected
        self.type = '!='

    def check(self, entry, value):
        if isinstance(self.limit, int):
            if int(value) !=  self.limit:
                raise ConstraintError(entry, int(value), '!=', self.limit)
        else:
            if value !=  self.limit:
                raise ConstraintError(entry, value, '!=', self.limit)

