## vim:set syntax=mako:
<%namespace file="/type.tmpl" name="ctype" />
<%namespace file="/decodeentry.tmpl" name="decodeentry" />

#ifndef ${entry.name + 'header guard' |constant}
#define ${entry.name + 'header guard' |constant}

#include "buffer.h"
%for common_entry in common:
  %if common_entry is not entry:
#include "${common_entry.name |filename}.h"
  %endif
%endfor

${ctype.define(entry)}

// Decode a ${entry.name} instance.
// The data is decoded into the result argument. Return value is 0 for decode
// failure, non-zero for success.
// Note: Any values allready present in result will be ignored and overwritten.
int ${ctype.decode_name(entry)}( BitBuffer* buffer, ${ctype.ctype(entry)}* result${decodeentry.define_params(entry)});

// Print an xml representation of a ${entry.name} object.
void ${ctype.print_name(entry)}(${ctype.ctype(entry)}* data);

#endif
