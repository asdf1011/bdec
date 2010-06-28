# Copyright (c) 2010, PRESENSE Technologies GmbH
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the PRESENSE Technologies GmbH nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from bdec.encode.choice import ChoiceEncoder
from bdec.encode.entry import Child
from bdec.encode.field import FieldEncoder
from bdec.encode.sequence import SequenceEncoder
from bdec.encode.sequenceof import SequenceOfEncoder
from bdec.choice import Choice
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

_encoders = {
        Choice : ChoiceEncoder,
        Field : FieldEncoder,
        Sequence : SequenceEncoder,
        SequenceOf : SequenceOfEncoder,
        }

class Encoder:
    def __init__(self, entry):
        self._entries = {}
        self._encoder = self._get_encoder(entry)

    def _get_encoder(self, entry):
        try:
            encoder = self._entries[entry]
        except KeyError:
            # We haven't created an encoder for this entry yet.
            encoder = _encoders[type(entry)](entry)
            self._entries[entry] = encoder

            for child in entry.children:
                encoder.children.append(Child(child.name, self._get_encoder(child.entry)))
        return encoder

    def encode(self, query, value):
        return self._encoder.encode(query, value, 0)
