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
from bdec.encode.entry import Child, is_hidden
from bdec.encode.field import FieldEncoder
from bdec.encode.sequence import SequenceEncoder
from bdec.encode.sequenceof import SequenceOfEncoder
from bdec.choice import Choice
from bdec.field import Field
from bdec.inspect.param import EncodeExpressionParameters
from bdec.inspect.type import EntryLengthType, EntryValueType, MultiSourceType
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

_encoders = {
        Choice : ChoiceEncoder,
        Field : FieldEncoder,
        Sequence : SequenceEncoder,
        SequenceOf : SequenceOfEncoder,
        }

def _detect_common(entry, name, common, visited=None):
    """Detect any common entries.

    Common entries are those that have renamed names, or are referenced in
    multiple locations."""
    if visited is None:
        visited = set()
    if entry in visited or entry.name != name:
        common.add(entry)
    if entry not in visited:
        visited.add(entry)
        for child in entry.children:
            _detect_common(child.entry, child.name, common, visited)

def get_encoder(entry, params, entries=None):
    if entries is None:
        entries = {}
    try:
        encoder = entries[entry]
    except KeyError:
        # We haven't created an encoder for this entry yet.
        encoder = _encoders[type(entry)](entry, params, params.get_params(entry), params.is_hidden(entry))
        entries[entry] = encoder

        for child in entry.children:
            is_child_hidden = params.is_hidden(child.entry) or is_hidden(child.name)
            encoder.children.append(Child(child,
                get_encoder(child.entry, params, entries),
                params.get_passed_variables(entry, child), is_child_hidden))
    return encoder

def create_encoder(entry):
    common = set([entry])
    _detect_common(entry, entry.name, common)
    params = EncodeExpressionParameters(common)
    return get_encoder(entry, params)

