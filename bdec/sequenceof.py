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
#  
# This file incorporates work covered by the following copyright and  
# permission notice:  
#  
#   Copyright (c) 2010, PRESENSE Technologies GmbH
#   All rights reserved.
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#       * Redistributions of source code must retain the above copyright
#         notice, this list of conditions and the following disclaimer.
#       * Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#       * Neither the name of the PRESENSE Technologies GmbH nor the
#         names of its contributors may be used to endorse or promote products
#         derived from this software without specific prior written permission.
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import bdec.data as dt
import bdec.entry
from bdec.expression import Constant, Expression

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

    def __init__(self, name, child, count=None, length=None, end_entries=[]):
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

    def _validate(self):
        bdec.entry.Entry._validate(self)
        for entry in self.end_entries:
            assert isinstance(entry, bdec.entry.Entry), "%s isn't an entry instance!" % str(entry)


