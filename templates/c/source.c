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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "${entry.name |filename}.h"
#include "buffer.h"
#include "variable_integer.h"

## Recursively create functions for decoding the entries contained within this protocol specification.
<%def name="recursiveDecode(entry)">
%for child in entry.children:
  %if child not in common:
${recursiveDecode(child)}
  %endif
%endfor

int ${'decode ' + entry.name |function}(BitBuffer* buffer, ${ctype.ctype(entry)}* result${decodeentry.define_params(entry)})
{
  %for local in local_vars(entry):
      int ${local} = 0;
  %endfor
  %if isinstance(entry, Field):
    ${decodeentry.decodeField(entry, "(*result)")};
    %if is_end_sequenceof(entry):
    *should_end = 1;
    %endif
    return 1;
  %elif isinstance(entry, Sequence):
    %for child in entry.children:
    if (!${'decode ' + child.name |function}(buffer, &result->${child.name |variable}${decodeentry.params(entry, child)}))
    {
        return 0;
    }
    %endfor
    %if is_end_sequenceof(entry):
    *should_end = 1;
    %endif
    return 1;
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
    while (!should_end)
    {
        i = result->count;
        ++result->count;
        result->items = realloc(result->items, sizeof(${ctype.ctype(entry.children[0])}) * (result->count + 1));
    %endif
        if (!${'decode ' + entry.children[0].name |function}(buffer, &result->items[i]${decodeentry.params(entry, entry.children[0])}))
        {
            return 0;
        }
      %if is_end_sequenceof(entry):
      *should_end = 1;
      %endif
    }
    return 1;
  %elif isinstance(entry, Choice):
    memset(result, 0, sizeof(${ctype.ctype(entry)}));
    BitBuffer temp;
    %for child in entry.children:
    temp = *buffer;
    ${ctype.ctype(child)}* ${'temp ' + child.name |variable} = malloc(sizeof(${ctype.ctype(child)}));
    if (${'decode ' + child.name |function}(&temp, ${'temp ' + child.name |variable}${decodeentry.params(entry, child)}))
    {
        *buffer = temp;
        result->${child.name |variable} = ${'temp ' + child.name |variable};
        return 1;
    }
    %endfor
    // Decode failed, no options succeeded...
    return 0;
  %endif
}
</%def>

${recursiveDecode(entry)}


## Recursively create functions for printing the entries contained within this protocol specification.
<%def name="recursivePrint(item, varname)">
  %if item in common and item is not entry:
    ${'print xml ' + item.name |function}(&${varname});
  %else:
    printf("<${item.name |xmlname}>\n");
    %if isinstance(item, Field):
      %if item.format is Field.INTEGER:
    printf("  %i\n", ${varname}); 
      %elif item.format is Field.TEXT:
    printf("  %s\n", ${varname});
      %elif item.format is Field.HEX:
    int i;
    printf("  ");
    for (i = 0; i < ${varname}.length; ++i)
    {
        printf("%x", ${varname}.buffer[i]);
    }
    printf("\n");
      %elif item.format is Field.BINARY:
    BitBuffer temp = ${varname};
    int i;
    printf("  ");
    for (i = 0; i < ${varname}.num_bits; ++i)
    {
        printf("%i", decode_integer(&temp, 1));
    }
    printf("\n");
      %else:
    #error Don't know how to print ${item}
      %endif
    %elif isinstance(item, Sequence):
      %for child in item.children:
    ${recursivePrint(child, '%s.%s' % (varname, variable(child.name)))}
      %endfor
    %elif isinstance(item, SequenceOf):
    int i;
    for (i = 0; i < ${varname}.count; ++i)
    {
        ${recursivePrint(item.children[0], '%s.items[i]' % varname)}
    }
    %elif isinstance(item, Choice):
      %for child in item.children:
    if (${'%s.%s' % (varname, variable(child.name))} != 0)
    {
        ${recursivePrint(child, "(*%s.%s)" % (varname, variable(child.name)))}
    }
      %endfor
    %else:
    #error Don't know how to print ${item}
    %endif
    printf("</${item.name |xmlname}>\n");
  %endif
</%def>

void ${'print xml ' + entry.name |function}(${ctype.ctype(entry)}* data)
{
${recursivePrint(entry, '(*data)')}
}
