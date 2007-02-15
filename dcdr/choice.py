
import dcdr.entry

class ChoiceDecodeError(dcdr.DecodeError):
    """
    One of the entries under the choice failed to decode.

    Ideally we should raise the decode error of the one 
    that decoded the most, but this is easier for now.
    """
    pass

class Choice(dcdr.entry.Entry):
    """
    Implement an entry that can be one of many entries.

    The first entry to decode correctly will be used.
    """

    def __init__(self, name, children):
        dcdr.entry.Entry.__init__(self, name)

        self.children = children

    def _decode(self, data):
        for child in self.children:
            try:
                # Note that we have to use 'list', as the function
                # may be a generator.
                list(child.decode(data.copy()))
                break
            except dcdr.DecodeError:
                pass
        else:
            raise ChoiceDecodeError(self)

        assert child is not None
        return child.decode(data)
