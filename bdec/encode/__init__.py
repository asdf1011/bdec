
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
