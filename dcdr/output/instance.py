import dcdr.field as fld
import dcdr.sequenceof as sof

def _escape(name):
    return name.replace(' ', '_')

class _Item:
    pass

class _DecodedItem:
    """ Class to handle creating python instances from decoded entries """
    def __init__(self, entry):
        self._entry = entry
        self._children = []

    def add_entry(self, entry, value):
        self._children.append((entry, value))

    def get_value(self):
        if isinstance(self._entry, sof.SequenceOf):
            result = list(value for child, value in self._children)
        elif isinstance(self._entry, fld.Field):
            assert len(self._children) == 0
            result = self._entry.get_value()
        else:
            result = _Item()
            for child, value in self._children:
                setattr(result, _escape(child.name), value)
        return result

def decode(decoder, binary):
    """
    Create a python instance representing the decoded data.
    """
    stack = [_DecodedItem(None)]
    for is_starting, entry in decoder.decode(binary):
        if is_starting:
            stack.append(_DecodedItem(entry))
        else:
            child = stack.pop().get_value()
            stack[-1].add_entry(entry, child)

    assert len(stack) == 1
    return stack[0].get_value()
