import logging
import string
import StringIO
import xml.dom.minidom
import xml.sax.saxutils
import xml.sax.xmlreader

import bdec.entry as ent
import bdec.field as fld

def _escape_name(name):
    return name.replace(' ', '-').replace('(', '_').replace(')', '_').replace(':', '_')

class _XMLGenerator(xml.sax.saxutils.XMLGenerator):
    def comment(self, text):
        self._out.write('<!-- %s -->' % text)

def to_file(decoder, binary, output, encoding="utf-8", verbose=False):
    handler = _XMLGenerator(output, encoding)
    offset = 0
    for is_starting, entry, data in decoder.decode(binary):
        if not verbose and entry.is_hidden():
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
                if len(text) > 0 and (text[0] in string.whitespace or text[-1] in string.whitespace):
                    logging.warning('%s has leading/trailing whitespace (%s); it will not re-encode exactly. Consider changing the format to hex.', entry, text)
                handler.characters(text)
                handler.ignorableWhitespace('\n')

                if verbose:
                    handler.ignorableWhitespace(' ' * offset)
                    if len(entry.data) % 8 == 0:
                        handler.comment('hex (%i bytes): %s' % (len(entry.data) / 8, entry.data.get_hex()))
                    else:
                        handler.comment('bin (%i bits): %s' % (len(entry.data), entry.data.get_binary_text()))
                    handler.ignorableWhitespace('\n')
                    
            offset = offset - 4
            handler.ignorableWhitespace(' ' * offset)
            handler.endElement(_escape_name(entry.name))
            handler.ignorableWhitespace('\n')

def to_string(decoder, binary, verbose=False):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer, verbose=verbose)
    return buffer.getvalue()


def _query_element(obj, child):
    """
    Get a named child-element of a node.

    If the child has no sub-elements itself, return the element text contents.
    """
    name = _escape_name(child.name)
    for child_node in obj.childNodes:
        if child_node.nodeType == xml.dom.Node.ELEMENT_NODE and child_node.tagName == name:
            text = ""
            for subchild in child_node.childNodes:
                if subchild.nodeType == xml.dom.Node.ELEMENT_NODE:
                    # This element has sub-elements, so return the element itself.
                    return child_node
                elif subchild.nodeType == xml.dom.Node.TEXT_NODE:
                    # NOTE: We have to strip to avoid getting all of the extra whitespace,
                    # but if there was leading or trailing whitespace on the original
                    # data, it'll get lost (which can cause encoding to fail).
                    text += subchild.data.strip()
            # No sub-elements; just return the text of the element.
            return text

    raise ent.MissingInstanceError(obj, child)

def encode(protocol, xmldata):
    """
    Encode an xml string or file object to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    if isinstance(xmldata, basestring):
        xmldata = StringIO.StringIO(xmldata)
    document = xml.dom.minidom.parse(xmldata)
    return protocol.encode(_query_element, document) 

