
import bdec.data as dt
from bdec.field import FieldDataError
from bdec.decode.entry import EntryDecoder

class FieldDecoder(EntryDecoder):
    """ An instance to decode field entries to python objects. """

    def _decode(self, data, context, name):
        """ see bdec.entry.Entry._decode """
        yield (True, name, self.entry, data, None)

        field_data = data.pop(self.entry.length.evaluate(context))
        # As this popped data is not guaranteed to be available, we have to
        # wrap all access to it in an exception handler.
        try:
            value = self.entry.decode_value(field_data)
        except dt.DataError, ex:
            raise FieldDataError(self.entry, ex)

        yield (False, name, self.entry, field_data, value)
