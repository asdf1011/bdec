import logging
import string
import StringIO
import xml.dom.minidom
import xml.sax.saxutils
import xml.sax.xmlreader

import bdec
import bdec.field as fld

class MissingElementError(bdec.DecodeError):
    """
    Thrown when the xml we are encoding is missing an expected element.
    """
    pass

def _escape_name(name):
    return name.replace(' ', '-').replace('(', '_').replace(')', '_')

def to_file(decoder, binary, output, encoding="utf-8"):
    handler = xml.sax.saxutils.XMLGenerator(output, encoding)
    offset = 0
    for is_starting, entry in decoder.decode(binary):
        if entry.is_hidden():
            continue

        if is_starting:
            handler.ignorableWhitespace(' ' * offset)
            handler.startElement(_escape_name(entry.name), xml.sax.xmlreader.AttributesImpl({}))
            handler.ignorableWhitespace('\n')
            offset = offset + 4
        else:
            if isinstance(entry, fld.Field):
                handler.ignorableWhitespace(' ' * offset)
                text = unicode(entry.get_value())
                if len(text) > 0 and text[0] in string.whitespace or text[-1] in string.whitespace:
                    logging.warning('%s has leading/trailing whitespace (%s); it will not re-encode exactly. Consider changing the format to hex.', entry, text)
                handler.characters(text)
                handler.ignorableWhitespace('\n')
            offset = offset - 4
            handler.ignorableWhitespace(' ' * offset)
            handler.endElement(_escape_name(entry.name))
            handler.ignorableWhitespace('\n')

def to_string(decoder, binary):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer)
    return buffer.getvalue()


def _query_element(obj, name):
    """
    Get a named child-element of a node.

    If the child has no sub-elements itself, return the element text contents.
    """
    if name.endswith(':'):
        return obj

    name = _escape_name(name)
    for child in obj.childNodes:
        if child.nodeType == xml.dom.Node.ELEMENT_NODE and child.tagName == name:
            text = ""
            for subchild in child.childNodes:
                if subchild.nodeType == xml.dom.Node.ELEMENT_NODE:
                    # This element has sub-elements, so return the element itself.
                    return child
                elif subchild.nodeType == xml.dom.Node.TEXT_NODE:
                    # NOTE: We have to strip to avoid getting all of the extra whitespace,
                    # but if there was leading or trailing whitespace on the original
                    # data, it'll get lost (which can cause encoding to fail).
                    text = subchild.data.strip()
            # No sub-elements; just return the text of the element.
            return text
    raise MissingElementError(obj, name)

def encode(protocol, xmldata):
    """
    Encode an xml string or file object to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    if isinstance(xmldata, basestring):
        xmldata = StringIO.StringIO(xmldata)
    document = xml.dom.minidom.parse(xmldata)
    return protocol.encode(_query_element, document) 

