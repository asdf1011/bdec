## vim:set syntax=mako:
<%! 
  from bdec.choice import Choice
  from bdec.field import Field
  from bdec.sequence import Sequence
  from bdec.sequenceof import SequenceOf
 %>

#ifndef ${entry.name + 'header guard' |constant}
#define ${entry.name + 'header guard' |constant}

#include "buffer.h"
%for e in iter_required_common(entry):
#include "${e.name |filename}.h"
%endfor

<%def name="c_define(entry)" >
  %if isinstance(entry, Sequence):
${settings.ctype(entry)}
{
  %for i, child in enumerate(entry.children):
    %if not is_structure_hidden(child):
    ${settings.ctype(child)} ${var_name(i, entry.children)};
    %endif
  %endfor
  %if entry.value is not None:
    int value;
  %endif
};
  %elif isinstance(entry, Field):
typedef ${settings.ctype(entry)} ${entry.name |typename};
  %elif isinstance(entry, Choice):
${settings.ctype(entry)}
{
    %for i, child in enumerate(entry.children):
      %if not is_structure_hidden(child):
    ${settings.ctype(child)}* ${var_name(i, entry.children)};
      %endif
    %endfor
};
  %elif isinstance(entry, SequenceOf):
${settings.ctype(entry)}
{
    ${settings.ctype(entry.children[0])}* items;
    unsigned int count;
};
  %else:
#error Unsupported entry ${entry}
  %endif
</%def>

%for e in iter_inner_entries(entry):
  %if not isinstance(e, Field):
${c_define(e)}
  %endif
%endfor


// Decode a ${entry.name} instance.
// Any values already present in result will be ignored and overwritten.
//   buffer -- The data to decoded.
//   result -- The decoded structured is stored in this argument. If the data is
//      decoded successfully, to free any allocated structures you should call
//      the entry free function. Do not call for decode failures.
//   return -- 0 for decode failure, non-zero for success.
int ${settings.decode_name(entry)}( BitBuffer* buffer${settings.define_params(entry)});

// Free a previously decoded object.
// Do not attempt to free an object that has not been decoded, or was only
// partially decoded.
// Do not free an item multiple times.
//   value -- The entry whose contents is to be released. The pointer 'value'
//     will not be freed.
void ${settings.free_name(entry)}(${settings.ctype(entry)}* value);

// Print an xml representation of a ${entry.name} object.
void ${settings.print_name(entry)}(${settings.ctype(entry)}* data, int offset);

#endif

