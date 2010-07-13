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
from bdec.inspect.param import ExpressionParameters
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

_encoders = {
        Choice : ChoiceEncoder,
        Field : FieldEncoder,
        Sequence : SequenceEncoder,
        SequenceOf : SequenceOfEncoder,
        }

def _populate_visible(entry, name, entries, visible=True):
    if entry in entries:
        return

    visible &= not is_hidden(name)
    if entry.name != name:
        # This is a renamed entry (so it's probably common). Reset the visible
        # flag.
        visible = True
    entries[entry] = not visible
    for child in entry.children:
        _populate_visible(child.entry, child.name, entries, visible)

def _get_encoder(entry, params, entries, hidden_map):
    try:
        encoder = entries[entry]
    except KeyError:
        # We haven't created an encoder for this entry yet.
        encoder = _encoders[type(entry)](entry, params, hidden_map[entry])
        entries[entry] = encoder

        for child in entry.children:
            encoder.children.append(Child(child.name,
                _get_encoder(child.entry, params, entries, hidden_map),
                list(params.get_passed_variables(entry, child)),
                hidden_map[child.entry] or is_hidden(child.name)))
    return encoder

def create_encoder(entry):
    params = ExpressionParameters([entry])
    hidden_map = {}
    _populate_visible(entry, entry.name, hidden_map)
    return _get_encoder(entry, params, {}, hidden_map)

