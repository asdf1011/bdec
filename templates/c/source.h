## vim:set syntax=mako:
<%namespace file="/type.tmpl" name="ctype" />
<%namespace file="/decodeentry.tmpl" name="decodeentry" />

#ifndef ${entry.name}_HEADER_GUARD
#define ${entry.name}_HEADER_GUARD

#include "buffer.h"
%for common_entry in common:
  %if common_entry is not entry:
#include "${common_entry.name}.h"
  %endif
%endfor

${ctype.define(entry)}

// Decode a ${entry.name} instance.
// The data is decoded into the result argument. Return value is 0 for decode
// failure, non-zero for success.
// Note: Any values allready present in result will be ignored and overwritten.
int decode_${entry.name}( BitBuffer* buffer, ${entry.name}* result${decodeentry.define_params(entry)});

// Print an xml representation of a ${entry.name} object.
void print_xml_${entry.name}(${entry.name}* data);

#endif
