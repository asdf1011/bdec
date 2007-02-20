import StringIO
import xml.sax.saxutils
import xml.sax.xmlreader

import dcdr.field as fld

def _escape_name(name):
    return name.replace(' ', '-')

def to_file(decoder, binary, output, encoding="utf-8"):
    handler = xml.sax.saxutils.XMLGenerator(output, encoding)
    offset = 0
    for is_starting, entry in decoder.decode(binary):
        if is_starting:
            handler.ignorableWhitespace(' ' * offset)
            handler.startElement(_escape_name(entry.name), xml.sax.xmlreader.AttributesImpl({}))
            handler.ignorableWhitespace('\n')
            offset = offset + 4
        else:
            if isinstance(entry, fld.Field):
                handler.ignorableWhitespace(' ' * offset)
                handler.characters(unicode(entry.get_value()))
                handler.ignorableWhitespace('\n')
            offset = offset - 4
            handler.ignorableWhitespace(' ' * offset)
            handler.endElement(_escape_name(entry.name))
            handler.ignorableWhitespace('\n')

def to_string(decoder, binary):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer)
    return buffer.getvalue()
