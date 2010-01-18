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
from bdec.expression import Constant, Expression

class InvalidSequenceOfCount(bdec.DecodeError):
    """Raised during encoding when an invalid length is found."""
    def __init__(self, seq, expected, actual):
        bdec.DecodeError.__init__(self, seq)
        self.sequenceof = seq
        self.expected = expected
        self.actual = actual

    def __str__(self):
        return "%s expected count of %i, got %i" % (self.sequenceof, self.expected, self.actual)

class NegativeSequenceofLoop(bdec.DecodeError):
    """Error when a sequenceof is asked to loop a negative amount."""
    def __init__(self, seq, count):
        bdec.DecodeError.__init__(self, seq)
        self.count = count

    def __str__(self):
        return "%s asked to loop %i times!" % (self.entry, self.count)


class SequenceEndedEarlyError(bdec.DecodeError):
    def __str__(self):
        return "%s got an end-sequenceof while still looping!" % (self.entry)

class SequenceofStoppedBeforeEndEntry(bdec.DecodeError):
    def __str__(self):
        return "%s stopped without receiving an end-sequenceof!" % (self.entry)


class SequenceOf(bdec.entry.Entry):
    """
    A protocol entry representing a sequence of another protocol entry.

    The number of times the child entry will loop can be set in one of three
    ways;
     
     * It can loop for a specified amount of times
     * It can loop until a buffer is empty
     * It can loop until a child entry decodes
    """
    STOPPED = "stopped"
    ITERATING = "iterating"
    STOPPING = "stopping"

    def __init__(self, name, child, count, length=None, end_entries=[]):
        """
        count -- The number of times the child will repeat. If this value is
          None, the count will not be used.
        length -- The size of the buffer in bits. When the buffer is empty, the
          looping will stop. If None, the length will not be used.
        end_entries -- A list of child entries whose successful decode
          indicates the loop should stop.

        If neither count, length, or end_entries are used, the SequenceOf will
        fail to decode after using all of the available buffer.
        """
        bdec.entry.Entry.__init__(self, name, length, [child])
        if isinstance(count, int):
            count = Constant(count)
        assert count is None or isinstance(count, Expression)
        self.count = count
        self.end_entries = end_entries

    def validate(self):
        bdec.entry.Entry.validate(self)
        for entry in self.end_entries:
            assert isinstance(entry, bdec.entry.Entry), "%s isn't an entry instance!" % str(entry)

    def _loop(self, context, data):
        context['should end'] = False
        if self.count is not None:
            # We have a count of items; use that to determine how long we
            # should continue looping for.
            count = int(self.count.evaluate(context))
            if count < 0:
                raise NegativeSequenceofLoop(self, count)

            for i in xrange(count):
                yield None
        elif self.end_entries:
            while not context['should end']:
                yield None
        else:
            while data:
                yield None

    def _decode(self, data, context, name):
        yield (True, name, self, data, None)
        for i in self._loop(context, data):
            if self.end_entries and context['should end']:
                raise SequenceEndedEarlyError(self)
            for item in self._decode_child(self.children[0], data, context):
                yield item
        if self.end_entries and not context['should end']:
            raise SequenceofStoppedBeforeEndEntry(self)
        yield (False, name, self, dt.Data(), None)

    def _encode(self, query, value):
        count = 0
        for child in value:
            count += 1
            for data in self.children[0].entry.encode(query, child):
                yield data

        if self.count is not None and self.count.evaluate({}) != count:
            raise InvalidSequenceOfCount(self, self.count.evaluate({}), count)

