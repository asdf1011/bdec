## vim:set syntax=mako:
<%namespace file="/type.tmpl" name="ctype" />
<%namespace file="/decodeentry.tmpl" name="decodeentry" />

#ifndef ${entry.name + 'header guard' |constant}
#define ${entry.name + 'header guard' |constant}

#include "buffer.h"
%for e in iter_required_common(entry):
#include "${e.name |filename}.h"
%endfor

${ctype.define(entry)}

// Decode a ${entry.name} instance.
// Any values already present in result will be ignored and overwritten.
//   buffer -- The data to decoded.
//   result -- The decoded structured is stored in this argument. If the data is
//      decoded successfully, to free any allocated structures you should call
//      the entry free function. Do not call for decode failures.
//   return -- 0 for decode failure, non-zero for success.
int ${ctype.decode_name(entry)}( BitBuffer* buffer, ${settings.ctype(entry)}* result${decodeentry.define_params(entry)});

// Free a previously decoded object.
// Do not attempt to free an object that has not been decoded, or was only
// partially decoded.
// Do not free an item multiple times.
//   value -- The entry whose contents is to be released. The pointer 'value'
//     will not be freed.
void ${ctype.free_name(entry)}(${settings.ctype(entry)}* value);

// Print an xml representation of a ${entry.name} object.
void ${ctype.print_name(entry)}(${settings.ctype(entry)}* data, int offset);

#endif
