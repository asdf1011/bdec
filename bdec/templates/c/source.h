## vim:set syntax=mako:
<%! 
  from bdec.choice import Choice
  from bdec.field import Field
  from bdec.sequence import Sequence
  from bdec.sequenceof import SequenceOf
 %>

/*  Portions Copyright (C) 2008 Henry Ludemann

    This file is part of the bdec decoder library.

    The bdec decoder library is free software; you can redistribute it
    and/or modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    The bdec decoder library is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty
    of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, see
    <http://www.gnu.org/licenses/>. */

#ifndef ${entry.name + 'header guard' |constant}
#define ${entry.name + 'header guard' |constant}

#include "buffer.h"
%for e in iter_required_common(entry):
#include "${e.name |filename}.h"
%endfor

#ifdef __cplusplus
extern "C" {
#endif

<%def name="c_define(entry)" >
  %if isinstance(entry, Sequence) and settings.ctype(entry) is not 'int':
${settings.ctype(entry)}
{
  %for i, child in enumerate(entry.children):
    %if contains_data(child.entry):
    ${settings.ctype(child.entry)} ${var_name(i, entry.children)};
    %endif
  %endfor
  %if entry.value is not None:
    int value;
  %endif
};
  %elif isinstance(entry, Choice):
enum ${settings.enum_type_name(entry)}
{
    %for i, child in enumerate(entry.children):
      <% trailing_char = ',' if i + 1 != len(entry.children) else '' %>
    ${enum_value(entry, i)}${trailing_char}
    %endfor
};

${settings.ctype(entry)}
{
    enum ${settings.enum_type_name(entry)} option;
    union
    {
    %for i, child in enumerate(entry.children):
      %if contains_data(child.entry):
        %if is_recursive(entry, child.entry):
        ${settings.ctype(child.entry)}* ${var_name(i, entry.children)};
        %else:
        ${settings.ctype(child.entry)} ${var_name(i, entry.children)};
        %endif
      %endif
    %endfor
    }value;
};
  %elif isinstance(entry, SequenceOf):
${settings.ctype(entry)}
{
    ${settings.ctype(entry.children[0].entry)}* items;
    unsigned int count;
};
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
void ${settings.print_name(entry)}(${settings.ctype(entry)}* data, int offset, char* name);

#ifdef __cplusplus
}
#endif

#endif

