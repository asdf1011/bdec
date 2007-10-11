## vim:set syntax=mako:
<%namespace file="/type.tmpl" name="ctype" />

#ifndef ${entry.name}_HEADER_GUARD
#define ${entry.name}_HEADER_GUARD

#include "buffer.h"

${ctype.define(entry)}

// Decode a ${entry.name} instance.
// The data is decoded into the result argument. Return value is 0 for decode
// failure, non-zero for success.
// Note: Any values allready present in result will be ignored and overwritten.
int decode_${entry.name}( Buffer* buffer, ${entry.name}* result);

// Print an xml representation of a ${entry.name} object.
void print_xml_${entry.name}(${entry.name}* data);

#endif
