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
from bdec.sequenceof import SequenceEndedEarlyError, NegativeSequenceofLoop, \
        SequenceofStoppedBeforeEndEntry

class SequenceOfDecoder(EntryDecoder):

    def _loop(self, context, data):
        context['should end'] = False
        if self.entry.count is not None:
            # We have a count of items; use that to determine how long we
            # should continue looping for.
            count = int(self.entry.count.evaluate(context))
            if count < 0:
                raise NegativeSequenceofLoop(self.entry, count)

            for i in xrange(count):
                yield None
        elif self.entry.end_entries:
            while not context['should end']:
                yield None
        else:
            while data:
                yield None

    def _decode(self, data, context, name):
        yield (True, name, self.entry, data, None)
        for i in self._loop(context, data):
            if self.entry.end_entries and context['should end']:
                raise SequenceEndedEarlyError(self.entry)
            for item in self._decode_child(self.children[0], data, context):
                yield item
        if self.entry.end_entries and not context['should end']:
            raise SequenceofStoppedBeforeEndEntry(self.entry)
        yield (False, name, self.entry, dt.Data(), None)
