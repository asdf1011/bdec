## vim:set syntax=mako:
<%namespace file="/type.tmpl" name="ctype" />

#ifndef ${entry.name}_HEADER_GUARD
#define ${entry.name}_HEADER_GUARD

#include "buffer.h"

${ctype.define(entry)}

// Decode a ${entry.name} from a bit aligned buffer
${entry.name}* decode_${entry.name}( Buffer* buffer);

// Print an xml representation of a ${entry.name} object.
void print_xml_${entry.name}(${entry.name}* data);

#endif
