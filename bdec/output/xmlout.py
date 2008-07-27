import logging
import string
import StringIO
import xml.dom.minidom
import xml.sax.saxutils
import xml.sax.xmlreader

import bdec.entry as ent
import bdec.field as fld
import bdec.sequenceof as sof

def escape_name(name):
    if not name:
        return "_hidden"
    return name.replace(' ', '-').replace('(', '_').replace(')', '_').replace(':', '_').replace('/', '_')

class _XMLGenerator(xml.sax.saxutils.XMLGenerator):
    def comment(self, text):
        self._out.write('<!-- %s -->' % text)

def to_file(decoder, binary, output, encoding="utf-8", verbose=False):
    handler = _XMLGenerator(output, encoding)
    offset = 0
    is_first = True
    for is_starting, entry, data, value in decoder.decode(binary):
        if not verbose and entry.is_hidden():
            continue

        if not is_starting:
            offset = offset - 4
        if value is None:
            if not is_first:
                handler.ignorableWhitespace('\n')
            handler.ignorableWhitespace(' ' * offset)
        is_first = False

        if is_starting:
            handler.startElement(escape_name(entry.name), xml.sax.xmlreader.AttributesImpl({}))
            offset = offset + 4

        if value is not None:
            text = unicode(value)
            handler.characters(text)

            if verbose and isinstance(entry, fld.Field):
                handler.comment(str(entry.data))

        if not is_starting:
            handler.endElement(escape_name(entry.name))
    handler.ignorableWhitespace('\n')

def to_string(decoder, binary, verbose=False):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer, verbose=verbose)
    return buffer.getvalue()

class _DummyElement:
    """Class to workaround the fact that entries of a sequenceof are asked for themselves. """
    def __init__(self, child):
        self.childNodes = [child]

class _SequenceOfIter:
    """A class to iterate over xml children entries from a sequenceof. """
    def __init__(self, child_nodes, child):
        self._child_nodes = child_nodes
        self._child = child

    def __iter__(self):
        for node in self._child_nodes:
            if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                # The object we return now will get asked for the child object,
                # but we allready have the child object. To work around this we
                # will create a 'dummy' element, with just this one node.
                yield _DummyElement(node)


def _query_element(obj, child):
    """
    Get a named child-element of a node.

    If the child has no sub-elements itself, return the element text contents.
    """
    name = escape_name(child.name)
    for child_node in obj.childNodes:
        if child_node.nodeType == xml.dom.Node.ELEMENT_NODE and child_node.tagName == name:
            if isinstance(child, sof.SequenceOf):
                # This element represents a sequence of, so we'll return an
                # object to iterate over the children.
                return _SequenceOfIter(child_node.childNodes, child.children[0])

            text = ""
            for subchild in child_node.childNodes:
                if subchild.nodeType == xml.dom.Node.ELEMENT_NODE:
                    # This element has sub-elements, so return the element itself.
                    return child_node
                elif subchild.nodeType == xml.dom.Node.TEXT_NODE:
                    text += subchild.data
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

