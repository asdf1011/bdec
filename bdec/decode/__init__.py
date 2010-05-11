
from bdec.choice import Choice
from bdec.decode.choice import ChoiceDecoder
from bdec.decode.entry import Child
from bdec.decode.field import FieldDecoder
from bdec.decode.sequence import SequenceDecoder
from bdec.decode.sequenceof import SequenceOfDecoder
from bdec.field import Field
from bdec.sequence import Sequence
from bdec.sequenceof import SequenceOf

_decoders = {
        Field : FieldDecoder,
        Sequence : SequenceDecoder,
        SequenceOf : SequenceOfDecoder,
        Choice : ChoiceDecoder,
        }

class Decoder:
    """ Decode instance data based on a specification. """
    def __init__(self, entry):
        """Construct a decoder instance.

        entry -- The entry that will be used for the decoding.
        """

        # Inspect the parameters for the entries to decode.
        import bdec.inspect.param
        end_entry_params = bdec.inspect.param.EndEntryParameters([entry])
        expression_params = bdec.inspect.param.ExpressionParameters([entry])
        params = bdec.inspect.param.CompoundParameters([end_entry_params, expression_params])

        self._entries = {}
        self._decoder = self._get_decoder(entry, params)

    def decode(self, data, context, name):
        return self._decoder.decode(data, context, name)

    def _get_decoder(self, entry, lookup):
        try:
            return self._entries[entry]
        except KeyError:
            # This entry hasn't been referenced yet; create a decoder for it.
            decoder = _decoders[type(entry)](entry, lookup.get_params(entry),
                    lookup.is_end_sequenceof(entry),
                    lookup.is_value_referenced(entry),
                    lookup.is_length_referenced(entry))

            self._entries[entry] = decoder

            # Construct the children decoders
            for child in entry.children:
                passed_params = zip(lookup.get_passed_variables(entry, child),
                        lookup.get_params(child.entry))
                decoder.children.append(Child(child.name,
                    self._get_decoder(child.entry, lookup), passed_params))

            return decoder
