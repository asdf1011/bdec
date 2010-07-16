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
from bdec.inspect.type import EntryLengthType
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

_encoders = {
        Choice : ChoiceEncoder,
        Field : FieldEncoder,
        Sequence : SequenceEncoder,
        SequenceOf : SequenceOfEncoder,
        }

def _populate_visible(entry, common, entries, visible=True):
    if entry in entries:
        return

    if entry in common:
        # Common entries are visible if their name is public, regardless of
        # what their parents do.
        visible = not is_hidden(entry.name)
    else:
        # Entries that aren't common are visible if both they and their parents
        # are visible.
        visible &= not is_hidden(entry.name)

    entries[entry] = not visible
    for child in entry.children:
        _populate_visible(child.entry, common, entries, visible)

def _params(params, is_hidden):
    """Change the order of the parameters such that they are suitable for encoding.

    For example, EntryLengthType references require that the referenced
    item is always encoded first, so that the length is known. A hidden
    referenced value, on the other hand (used in the length of another
    field, for example) should be encoded after the variable length field
    (as the length will come from the field being encoded)."""
    params = list(params)
    result = []
    for p in params:
        if (not is_hidden and ':' not in p.name) or \
                p.type.has_expected_value() or \
                isinstance(p.type, EntryLengthType):
            # The entry is either visible or has a known value; we don't need
            # to swap the outputs. For EntryLengthTypes we cannot swap the
            # direction.
            result.append(p)
        else:
            if p.direction == p.IN:
                p.direction = p.OUT
            else:
                p.direction = p.IN
            result.append(p)
    return result

def _get_encoder(entry, params, entries, hidden_map):
    try:
        encoder = entries[entry]
    except KeyError:
        # We haven't created an encoder for this entry yet.
        entry_params = _params(params.get_params(entry), hidden_map[entry])
        encoder = _encoders[type(entry)](entry, params, entry_params, hidden_map[entry])
        entries[entry] = encoder

        for child in entry.children:
            is_child_hidden = hidden_map[child.entry] or is_hidden(child.name)
            passed_params = _params(params.get_passed_variables(entry, child), is_child_hidden)
            encoder.children.append(Child(child.name,
                _get_encoder(child.entry, params, entries, hidden_map),
                passed_params, is_child_hidden))
    return encoder

def _detect_common(entry, name, common, visited=None):
    """Detect any common entries.

    Common entries are those that have renamed names, or are referenced in
    multiple locations."""
    if visited is None:
        visited = set()
    if entry in visited or entry.name != name:
        common.add(entry)
        return
    visited.add(entry)
    for child in entry.children:
        _detect_common(child.entry, child.name, common, visited)

def create_encoder(entry):
    params = ExpressionParameters([entry])
    hidden_map = {}
    common = set()
    _detect_common(entry, entry.name, common)
    _populate_visible(entry, common, hidden_map)
    return _get_encoder(entry, params, {}, hidden_map)

