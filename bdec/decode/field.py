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
from bdec.field import FieldDataError
from bdec.decode.entry import EntryDecoder

class FieldDecoder(EntryDecoder):
    """ An instance to decode field entries to python objects. """

    def _decode(self, data, context, name):
        """ see bdec.entry.Entry._decode """
        yield (True, name, self.entry, data, None)

        field_data = data.pop(self.entry.length.evaluate(context))
        # As this popped data is not guaranteed to be available, we have to
        # wrap all access to it in an exception handler.
        try:
            value = self.entry.decode_value(field_data)
        except dt.DataError, ex:
            raise FieldDataError(self.entry, ex)

        yield (False, name, self.entry, field_data, value)
