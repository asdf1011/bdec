import StringIO
import dcdr.field as fld

def _escape_name(name):
    return name.replace(' ', '-')

def _escape_text(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def to_file(decoder, binary, output):
    offset = 0
    for is_starting, entry in decoder.decode(binary):
        if is_starting:
            output.write(' ' * offset)
            offset = offset + 4
            output.write('<%s>\n' % _escape_name(entry.name))
        else:
            if isinstance(entry, fld.Field):
                output.write(' ' * offset)
                output.write('%s\n' % _escape_text(str(entry.get_value())))
            offset = offset - 4
            output.write(' ' * offset)
            output.write('</%s>\n' % _escape_name(entry.name))

def to_string(decoder, binary):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer)
    return buffer.getvalue()
