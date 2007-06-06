import bdec.field as fld
import bdec.output
import bdec.sequenceof as sof

def _escape(name):
    return name.replace(' ', '_')

class _Item:
    pass

class PythonInstanceError(bdec.output.OutputError):
    """
    An error occurred trying to create the python instance from the decoded data
    """
    pass

class _DecodedItem:
    """ Class to handle creating python instances from decoded entries """
    def __init__(self, entry):
        self._entry = entry
        self.children = []

    def add_entry(self, name, value):
        self.children.append((name, value))

    def get_value(self):
        """
        Create a python object representing the decoded protocol entry.
        """
        if isinstance(self._entry, sof.SequenceOf):
            result = list(value for name, value in self.children)
        elif isinstance(self._entry, fld.Field):
            assert len(self.children) == 0
            result = self._entry.get_value()
        else:
            result = _Item()
            for name, value in self.children:
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
            item = stack.pop()
            if not entry.is_hidden():
                stack[-1].add_entry(entry.name, item.get_value())
            else:
                # We want to ignore this item, but still add the childs items to the parent.
                if isinstance(entry, fld.Field):
                    # For ignored field items, we'll add the value to the parent. This allows
                    # us to have lists of numbers (eg: sequenceof with an ignored field)
                    stack[-1].add_entry("", item.get_value())
                else:
                    for name, value in item.children:
                        stack[-1].add_entry(name, value)

    assert len(stack) == 1
    return stack[0].get_value()

def _get_data(obj, name):
    if name.endswith(':'):
        # Hidden objects aren't included in the data
        return obj

    try: 
        return getattr(obj, name)
    except AttributeError:
        raise PythonInstanceError("Missing sub-object", obj, name)

def encode(protocol, value):
    """
    Encode a python instance to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    return protocol.encode(_get_data, value)
