## vim:set syntax=mako:
<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/expression.tmpl" name="expr" />
<%namespace file="/type.tmpl" name="ctype" />
<%! 
  from bdec.choice import Choice
  from bdec.field import Field
  from bdec.sequence import Sequence
  from bdec.sequenceof import SequenceOf
 %>

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "${entry.name |filename}.h"
%for e in iter_optional_common(entry):
#include "${e.name |filename}.h"
%endfor
#include "variable_integer.h"

<%def name="success(entry)">
  %if is_length_referenced(entry):
    *${entry.name + ' length' |variable} = ${'initial length' |variable} - buffer->num_bits;
  %endif
    return 1;
</%def>

## Recursively create functions for decoding the entries contained within this protocol specification.
<%def name="recursiveDecode(entry, is_static=True)">
%for child in entry.children:
  %if child not in common:
${recursiveDecode(child)}
  %endif
%endfor

<% static = "static " if is_static else "" %>
${static}void ${ctype.free_name(entry)}(${ctype.ctype(entry)}* value)
{
  %if isinstance(entry, Field):
    %if entry.format == Field.TEXT:
    free(*value);
    %elif entry.format == Field.HEX:
    free(value->buffer);
    %elif entry.format == Field.BINARY:
    free(value->buffer);
    %endif
  %elif isinstance(entry, Sequence):
    %for i, child in enumerate(entry.children):
    ${ctype.free_name(child)}(&value->${ctype.var_name(i, entry.children)});
    %endfor
  %elif isinstance(entry, SequenceOf):
    int i;
    for (i = 0; i < value->count; ++i)
    {
        ${ctype.free_name(entry.children[0])}(&value->items[i]);
    }
    free(value->items);
  %elif isinstance(entry, Choice):
    %for i, child in enumerate(entry.children):
    if (value->${ctype.var_name(i, entry.children)} != 0)
    {
        ${ctype.free_name(child)}(value->${ctype.var_name(i, entry.children)});
        free(value->${ctype.var_name(i, entry.children)});
    }
    %endfor
  %else:
    <% raise Exception("Don't know how to free objects of type '%s'" % entry) %>
  %endif
}

${static}int ${ctype.decode_name(entry)}(BitBuffer* buffer, ${ctype.ctype(entry)}* result${decodeentry.define_params(entry)})
{
  %for local in local_vars(entry):
      int ${local} = 0;
  %endfor
  %if is_length_referenced(entry):
      int ${'initial length' |variable} = buffer->num_bits;
  %endif
  %if isinstance(entry, Field):
    ${decodeentry.decodeField(entry, "(*result)")}
    %if is_end_sequenceof(entry):
    *${'should end' |variable} = 1;
    %endif
    ${success(entry)}
  %elif isinstance(entry, Sequence):
    %for i, child in enumerate(entry.children):
    if (!${ctype.decode_name(child)}(buffer, &result->${ctype.var_name(i, entry.children)}${decodeentry.params(entry, child)}))
    {
        %for j, previous in enumerate(entry.children[:i]):
        ${ctype.free_name(previous)}(&result->${ctype.var_name(j, entry.children)});
        %endfor
        return 0;
    }
    %endfor
    %if is_end_sequenceof(entry):
    *${'should end' |variable} = 1;
    %endif
    %if entry.value is not None:
    result->value = ${expr.length(entry.value)};
      %if is_value_referenced(entry):
    *${entry.name |variable} = result->value;
      %endif
    %endif
    ${success(entry)}
  %elif isinstance(entry, SequenceOf):
    int i;
    %if entry.count is not None:
    result->count = ${expr.length(entry.count)};
    result->items = malloc(sizeof(${ctype.ctype(entry.children[0])}) * result->count);
    for (i = 0; i < result->count; ++i)
    {
    %else:
    result->items = 0;
    result->count = 0;
      %if entry.length is not None:
    while (buffer->num_bits > 0)
      %else:
    while (!${'should end' |variable})
      %endif
    {
        i = result->count;
        ++result->count;
        result->items = realloc(result->items, sizeof(${ctype.ctype(entry.children[0])}) * (result->count + 1));
    %endif
        if (!${ctype.decode_name(entry.children[0])}(buffer, &result->items[i]${decodeentry.params(entry, entry.children[0])}))
        {
            int j;
            for (j=0; j<i; ++j)
            {
                ${ctype.free_name(entry.children[0])}(&result->items[j]);
            }
            free(result->items);
            return 0;
        }
      %if is_end_sequenceof(entry):
      *${'should end' |variable} = 1;
      %endif
    }
    ${success(entry)}
  %elif isinstance(entry, Choice):
    memset(result, 0, sizeof(${ctype.ctype(entry)}));
    BitBuffer temp;
    %for i, child in enumerate(entry.children):
    temp = *buffer;
    <% temp_name = variable('temp ' + esc_name(i, entry.children)) %>
    ${ctype.ctype(child)}* ${temp_name} = malloc(sizeof(${ctype.ctype(child)}));
    if (${ctype.decode_name(child)}(&temp, ${temp_name}${decodeentry.params(entry, child)}))
    {
        *buffer = temp;
        result->${ctype.var_name(i, entry.children)} = ${temp_name};
        ${success(entry)}
    }
    free(${temp_name});
    %endfor
    // Decode failed, no options succeeded...
    return 0;
  %endif
}
</%def>

${recursiveDecode(entry, False)}

## Recursively create functions for printing the entries contained within this protocol specification.
<%def name="recursivePrint(item, varname, offset, iter_postfix)">
  %if item in common and item is not entry:
    ${ctype.print_name(item)}(&${varname}, offset + ${offset});
  %else:
    %if not item.is_hidden():
    printf("${' ' * offset}<${item.name |xmlname}>");
    %endif
    %if isinstance(item, Field):
      %if not item.is_hidden():
        %if item.format == Field.INTEGER:
    printf("%i", ${varname}); 
        %elif item.format == Field.TEXT:
    printf("%s", ${varname});
        %elif item.format == Field.HEX:
        <% iter_name = variable(item.name + ' counter' + str(iter_postfix.next())) %>
    int ${iter_name};
    for (${iter_name} = 0; ${iter_name} < ${varname}.length; ++${iter_name})
    {
        printf("%x", ${varname}.buffer[${iter_name}]);
    }
        %elif item.format == Field.BINARY:
        <% copy_name = variable('copy of ' + item.name + str(iter_postfix.next())) %>
        <% iter_name = variable(item.name + ' counter' + str(iter_postfix.next())) %>
    BitBuffer ${copy_name} = ${varname};
    int ${iter_name};
    for (${iter_name} = 0; ${iter_name} < ${varname}.num_bits; ++${iter_name})
    {
        printf("%i", decode_integer(&${copy_name}, 1));
    }
        %else:
    #error Don't know how to print ${item}
        %endif
      %endif
    %else:
    ## Print everything other than fields
      %if not item.is_hidden():
    printf("\n");
      %endif
      <% next_offset = (offset + 3) if not item.is_hidden() else offset %>
      %if isinstance(item, Sequence):
        %for i, child in enumerate(item.children):
    ${recursivePrint(child, '%s.%s' % (varname, variable(esc_name(i, item.children))), next_offset, iter_postfix)}
        %endfor
        %if item.value is not None and not item.is_hidden():
    printf("${' ' * (offset+3)}%i\n", ${varname}.value); 
        %endif
      %elif isinstance(item, SequenceOf):
        <% iter_name = variable(item.name + ' counter' + str(iter_postfix.next())) %>
    int ${iter_name};
    for (${iter_name} = 0; ${iter_name} < ${varname}.count; ++${iter_name})
    {
        ${recursivePrint(item.children[0], '%s.items[%s]' % (varname, iter_name), next_offset, iter_postfix)}
    }
      %elif isinstance(item, Choice):
        %for i, child in enumerate(item.children):
    if (${'%s.%s' % (varname, variable(esc_name(i, item.children)))} != 0)
    {
        ${recursivePrint(child, "(*%s.%s)" % (varname, variable(esc_name(i, item.children))), next_offset, iter_postfix)}
    }
        %endfor
      %else:
    #error Don't know how to print ${item}
      %endif
      %if not item.is_hidden():
    printf("${' ' * offset}");
      %endif
    %endif
    %if not item.is_hidden():
    printf("</${item.name |xmlname}>\n");
    %endif
  %endif
</%def>

void ${ctype.print_name(entry)}(${ctype.ctype(entry)}* data, int offset)
{
${recursivePrint(entry, '(*data)', 0, iter(xrange(100)))}
}
