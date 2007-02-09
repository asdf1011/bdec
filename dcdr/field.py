import dcdr.entry

class Field(dcdr.entry.Entry):
    def __init__(self, name, get_length):
        dcdr.entry.Entry.__init__(self, name)

        self._get_length = get_length

    def decode(self, data, start, end):
        """ see dcdr.entry.Entry.decode """
        start(self)

        length = self._get_length()
        field_data = data.pop(length)

        end(self, field_data)
