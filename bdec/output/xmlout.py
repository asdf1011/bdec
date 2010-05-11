#   Copyright (C) 2008 Henry Ludemann
#
#   This file is part of the bdec decoder library.
#
#   The bdec decoder library is free software; you can redistribute it
#   and/or modify it under the terms of the GNU Lesser General Public
#   License as published by the Free Software Foundation; either
#   version 2.1 of the License, or (at your option) any later version.
#
#   The bdec decoder library is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public
#   License along with this library; if not, see
#   <http://www.gnu.org/licenses/>.

import logging
import string
import StringIO
import xml.dom.minidom
import xml.sax.saxutils
import xml.sax.xmlreader

from bdec.constraints import Equals
import bdec.entry as ent
import bdec.choice as chc
import bdec.field as fld
import bdec.sequenceof as sof

def escape_name(name):
    if not name:
        return "_hidden"
    if '0' <= name[0] <= '9':
        name = '_' + name
    return name.replace(' ', '-').replace('(', '_').replace(')', '_').replace(':', '_').replace('/', '_')

class _XMLGenerator(xml.sax.saxutils.XMLGenerator):
    def comment(self, text):
        self._out.write('<!-- %s -->' % text)

def _escape_char(character):
    # The list of 'safe' xml characters is from http://www.w3.org/TR/REC-xml/#NT-Char
    ordinal = ord(character)
    if ordinal >= 0x20:
        return character
    if ordinal in [0x9, 0xa, 0xd]:
        return character
    return '?'

def xml_strip(text):
    """Replace chracters that cannot be represented in xml."""
    return ''.join(_escape_char(char) for char in text)

def _print_whitespace(handler, offset):
    handler.ignorableWhitespace('\n')
    handler.ignorableWhitespace(' ' * offset)

def _has_expected_value(entry):
    for constraint in entry.constraints:
        if isinstance(constraint, Equals):
            return True
    return False

def to_file(decoder, binary, output, encoding="utf-8", verbose=False):
    handler = _XMLGenerator(output, encoding)
    offset = 0
    is_first = True
    hidden_count = 0
    has_children = False
    for is_starting, name, entry, data, value in decoder.decode(binary):
        # If we have an entry that is hidden, all entries under that should
        # also be hidden.
        if is_starting:
            if hidden_count or ent.is_hidden(name):
                hidden_count += 1
        is_hidden = hidden_count != 0
        if not is_starting and hidden_count:
            hidden_count -= 1

        if not verbose and (is_hidden or isinstance(entry, chc.Choice)):
            # By default, we don't output hidden or choice entries.
            continue

        if is_starting:
            if not is_first:
                _print_whitespace(handler, offset)
            is_first = False

            handler.startElement(escape_name(name), xml.sax.xmlreader.AttributesImpl({}))
            offset = offset + 4
            has_children = False
        else:
            # An element is ending; we only include the surrounding whitespace
            # if the entry has visible children (otherwise we try an keep the
            # value compact with the entries). This means strings with leading
            # and trailing whitespace can be represented (and produces nicer
            # xml).
            if value is not None and not _has_expected_value(entry):
                if has_children:
                    _print_whitespace(handler, offset)

                text = xml_strip(unicode(value))
                handler.characters(text)

            if verbose and data:
                handler.comment(str(data))
            offset = offset - 4
            if has_children:
                _print_whitespace(handler, offset)
            handler.endElement(escape_name(name))

            has_children = True
    handler.ignorableWhitespace('\n')

def to_string(decoder, binary, verbose=False):
    buffer  = StringIO.StringIO()
    to_file(decoder, binary, buffer, verbose=verbose)
    return buffer.getvalue()

class _SequenceOfIter:
    """A class to iterate over xml children entries from a sequenceof. """
    def __init__(self, child_nodes, child):
        self._child_nodes = child_nodes
        self._child = child

    def __iter__(self):
        for node in self._child_nodes:
            if node.nodeType == xml.dom.Node.ELEMENT_NODE:
                yield _get_element_value(node, self._child)

def _query_element(obj, child):
    """
    Get a named child-element of a node.

    If the child has no sub-elements itself, return the element text contents.
    """
    try:
        childNodes = obj.childNodes
    except AttributeError:
        raise ent.MissingInstanceError(obj, child)

    name = escape_name(child.name)
    for child_node in childNodes:
        if child_node.nodeType == xml.dom.Node.ELEMENT_NODE and child_node.tagName == name:
            return _get_element_value(child_node, child)

    raise ent.MissingInstanceError(obj, child)

def _get_element_value(element, entry):
    """Get an instance that can be encoded for a given xml element node.

    element -- The xml element to be encoded.
    entry -- The entry this element represents.
    """
    if isinstance(entry, sof.SequenceOf):
        # This element represents a sequence of, so we'll return an
        # object to iterate over the children.
        return _SequenceOfIter(element.childNodes, entry.children[0].entry)

    text = ""
    for child in element.childNodes:
        if child.nodeType == xml.dom.Node.ELEMENT_NODE:
            # This element has sub-elements, so return the high-level element
            # itself.
            return element
        elif child.nodeType == xml.dom.Node.TEXT_NODE:
            text += child.data
    # No sub-elements; this element is a 'value' type.
    return text

def encode(protocol, xmldata):
    """
    Encode an xml string or file object to binary data.

    Returns an iterator to data objects representing the encoded structure.
    """
    if isinstance(xmldata, basestring):
        xmldata = StringIO.StringIO(xmldata)
    document = xml.dom.minidom.parse(xmldata)
    value = protocol.get_context(_query_element, document)
    return protocol.encode(_query_element, value)

