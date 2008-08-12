import bdec.field as fld

keywords=['char', 'int', 'float', 'if', 'then', 'else', 'struct', 'for']

def ctype(entry):
    """Return the c type name for an entry"""
    if isinstance(entry, fld.Field):
        if entry.format == fld.Field.INTEGER:
            return 'int'
        if entry.format == fld.Field.TEXT:
            return 'char*'
        elif entry.format == fld.Field.HEX:
            return 'Buffer'
        elif entry.format == fld.Field.BINARY:
            return 'BitBuffer'
        else:
            raise Exception("Unhandled field format '%s'!" % entry)
    else:
        return "struct " + typename(esc_name(iter_entries().index(entry), iter_entries()))

