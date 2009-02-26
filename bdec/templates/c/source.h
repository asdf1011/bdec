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
  %if not contains_data(entry):

  %elif isinstance(entry, Sequence) and not settings.is_numeric(settings.ctype(entry)):
${settings.ctype(entry)}
{
  %for i, child in enumerate(entry.children):
    %if child_contains_data(child):
    ${settings.ctype(child.entry)} ${var_name(entry, i)};
    %endif
  %endfor
  %if entry.value is not None:
    ${ctype(EntryValueType(entry))} value;
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

    %if settings.children_contain_data(entry):
${settings.ctype(entry)}
{
    enum ${settings.enum_type_name(entry)} option;
    union
    {
    %for i, child in enumerate(entry.children):
      %if child_contains_data(child):
        %if is_recursive(entry, child.entry):
        ${settings.ctype(child.entry)}* ${var_name(entry, i)};
        %else:
        ${settings.ctype(child.entry)} ${var_name(entry, i)};
        %endif
      %endif
    %endfor
    }value;
};
    %endif
  %elif isinstance(entry, SequenceOf):
${settings.ctype(entry)}
{
    %if child_contains_data(entry.children[0]):
    ${settings.ctype(entry.children[0].entry)}* items;
    %endif
    unsigned int count;
};
  %endif
</%def>

%for e in iter_inner_entries(entry):
  %if not isinstance(e, Field):
${c_define(e)}
  %endif
%endfor


/**
 * Decode a ${entry.name} instance.
 *
 *   buffer -- The data to decoded.
 *   result -- The decoded structured is stored in this argument. If the data
 *      has decoded successfully, to free any allocated memory you should
 *      call ${settings.free_name(entry)}.
 *   return -- 0 for decode failure, non-zero for success.
 */
int ${settings.decode_name(entry)}( BitBuffer* buffer${settings.define_params(entry)});

%if contains_data(entry):
/**
 * Free a decoded object.
 *
 * Do not attempt to free an object that has not been decoded.
 *
 *   value -- The entry whose contents is to be released. The pointer 'value'
 *     will not be freed.
 */
void ${settings.free_name(entry)}(${settings.ctype(entry)}* value);
%endif

/**
 * Print an xml representation of a ${entry.name} object.
 */
%if contains_data(entry):
void ${settings.print_name(entry)}(${settings.ctype(entry)}* data, unsigned int offset, const char* name);
%else:
void ${settings.print_name(entry)}(unsigned int offset, const char* name);
%endif

#ifdef __cplusplus
}
#endif

#endif

