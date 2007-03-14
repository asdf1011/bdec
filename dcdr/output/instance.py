import dcdr.field as fld
import dcdr.output
import dcdr.sequenceof as sof

def _escape(name):
    return name.replace(' ', '_')

class _Item:
    pass

class PythonInstanceError(dcdr.output.OutputError):
    """
    An error occurred trying to create the python instance from the decoded data
    """
    pass

class _DecodedItem:
    """ Class to handle creating python instances from decoded entries """
    def __init__(self, entry):
        self._entry = entry
        self._children = []

    def add_entry(self, name, value):
        self._children.append((name, value))

    def get_value(self):
        """
        Create a python object representing the decoded protocol entry.
        """
        if isinstance(self._entry, sof.SequenceOf):
            result = list(value for name, value in self._children)
        elif isinstance(self._entry, fld.Field):
            assert len(self._children) == 0
            result = self._entry.get_value()
        else:
            result = _Item()
            for name, value in self._children:
                setattr(result, _escape(name), value)
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
            value = stack.pop().get_value()
            if not entry.is_hidden():
                stack[-1].add_entry(entry.name, value)
            else:
                # We want to ignore this item (but still include
                # the child items)...
                if isinstance(value, list):
                    raise PythonInstanceError('Asked to hide a list entry (no way to show child entries!)')
                elif isinstance(value, _Item):
                    # We'll look at all of the objects instances, and
                    # reset them on the parent object.
                    for name in dir(value):
                        if not name.startswith('_'):
                            stack[-1].add_entry(name, getattr(value, name))
                else:
                    # This is a simple value type; we'll ignore it
                    # completely.
                    pass

    assert len(stack) == 1
    return stack[0].get_value()
