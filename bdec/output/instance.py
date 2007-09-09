import bdec.entry as ent
import bdec.field as fld
import bdec.output
import bdec.sequenceof as sof

def escape(name):
    return name.replace(' ', '_')

class _Item:
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
        # We allready have the decoded values for fields; this function shouldn't
        # be used.
        assert not isinstance(self._entry, fld.Field)
        if isinstance(self._entry, sof.SequenceOf):
            result = list(value for name, value in self.children)
        else:
            result = _Item()
            for name, value in self.children:
                setattr(result, escape(name), value)
        return result

def decode(decoder, binary):
    """
    Create a python instance representing the decoded data.
    """
    stack = [_DecodedItem(None)]
    for is_starting, entry, data, value in decoder.decode(binary):
        if is_starting:
            stack.append(_DecodedItem(entry))
        else:
            item = stack.pop()
            if not entry.is_hidden():
                if not isinstance(entry, fld.Field):
                    value = item.get_value()
                stack[-1].add_entry(entry.name, value)
            else:
                # We want to ignore this item, but still add the childs items to the parent.
                if isinstance(entry, fld.Field):
                    # For ignored field items, we'll add the value to the parent. This allows
                    # us to have lists of numbers (eg: sequenceof with an ignored field)
                    stack[-1].add_entry("", value)
                else:
                    for name, value in item.children:
                        stack[-1].add_entry(name, value)

    assert len(stack) == 1
    return stack[0].get_value()

def _get_data(obj,child):
    name = child.name
    if name.endswith(':'):
        raise ent.MissingInstanceError(obj, child)

    name = escape(name)

    try: 
        return getattr(obj, name)
    except AttributeError:
        raise ent.MissingInstanceError(obj, child)

def encode(protocol, value):
    """
    Encode a python instance to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    return protocol.encode(_get_data, value)
