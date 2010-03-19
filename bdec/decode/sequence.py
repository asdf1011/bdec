
import bdec.data as dt
from bdec.decode.entry import EntryDecoder

class SequenceDecoder (EntryDecoder):

    def _decode(self, data, context, name):
        yield (True, name, self.entry, data, None)
        for child in self.children:
            for embedded in self._decode_child(child, data, context):
                yield embedded
        value = None
        if self.entry.value is not None:
            value = self.entry.value.evaluate(context)
        yield (False, name, self.entry, dt.Data(), value)
