import dcdr.field as fld

def _escape(name):
    return name.replace(' ', '_')

class _Item:
    pass

def decode(decoder, binary):
    """
    Create a python instance representing the decoded data.
    """
    stack = [_Item()]
    for is_starting, entry in decoder.decode(binary):
        if isinstance(entry, fld.Field):
            if not is_starting:
                setattr(stack[-1], _escape(entry.name), entry.get_value())
        else:
            if is_starting:
                stack.append(_Item())
            else:
                child = stack.pop()
                setattr(stack[-1], _escape(entry.name), child)
    assert len(stack) == 1
    return stack[0]
