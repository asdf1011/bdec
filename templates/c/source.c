## vim:set syntax=mako:
<%namespace file="/decodeentry.tmpl" name="decodeentry" />
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

#include "${entry.name}.h"
#include "buffer.h"
#include "variable_integer.h"

## Recursively create functions for decoding the entries contained within this protocol specification.
<%def name="recursiveDecode(entry)">
%for child in entry.children:
  %if not isinstance(child, Field) and child not in common:
${recursiveDecode(child)}
  %endif
%endfor

int decode_${entry.name}(BitBuffer* buffer, ${entry.name}* result)
{
  %if isinstance(entry, Field):
    ${decodeField(entry, "*result")};
    return 1;
  %elif isinstance(entry, Sequence):
    ${decodeentry.decodeSequence(entry)}
    return 1;
  %elif isinstance(entry, SequenceOf):
    int i;
    result->count = ${entry.count};
    result->items = malloc(sizeof(${entry.children[0].name}) * result->count);
    for (i = 0; i < result->count; ++i)
    {
        if (!decode_${entry.children[0].name}(buffer, &result->items[i]))
        {
            return 0;
        }
    }
    return 1;
  %elif isinstance(entry, Choice):
    memset(result, 0, sizeof(${entry.name}));
    BitBuffer temp;
    %for child in entry.children:
    // Attempt to decode ${child}...
      %if isinstance(child, Field):
    #error Don't support decoding fields directly under a choice yet (${child})...
      %else:
    temp = *buffer;
    ${child.name}* temp_${child.name} = malloc(sizeof(${child.name}));
    if (decode_${child.name}(&temp, temp_${child.name}))
    {
        *buffer = temp;
        result->${child.name} = temp_${child.name};
        return 1;
    }
      %endif
    %endfor

    // Decode failed, no options succeeded...
    return 0;
  %endif
}
</%def>

${recursiveDecode(entry)}


## Recursively create functions for printing the entries contained within this protocol specification.
<%def name="recursivePrint(item, variable)">
  %if item in common and item is not entry:
    print_xml_${item.name}(&${variable});
  %else:
    printf("<${item.name}>\n");
    %if isinstance(item, Field):
      %if item.format is Field.INTEGER:
    printf("  %i\n", ${variable}); 
      %elif item.format is Field.TEXT:
    printf("  %s\n", ${variable});
      %elif item.format is Field.HEX:
    int i;
    printf("  ");
    for (i = 0; i < ${variable}.length; ++i)
    {
        printf("%x", ${variable}.buffer[i]);
    }
    printf("\n");
      %elif item.format is Field.BINARY:
    BitBuffer temp = ${variable};
    int i;
    printf("  ");
    for (i = 0; i < ${variable}.num_bits; ++i)
    {
        printf("%i", decode_integer(&temp, 1));
    }
    printf("\n");
      %else:
    #error Don't know how to print ${item}
      %endif
    %elif isinstance(item, Sequence):
      %for child in item.children:
    ${recursivePrint(child, '%s.%s' % (variable, child.name))}
      %endfor
    %elif isinstance(item, SequenceOf):
    int i;
    for (i = 0; i < ${variable}.count; ++i)
    {
        ${recursivePrint(item.children[0], '%s.items[i]' % variable)}
    }
    %elif isinstance(item, Choice):
      %for child in item.children:
    if (${'%s.%s' % (variable, child.name)} != 0)
    {
        ${recursivePrint(child, "(*%s.%s)" % (variable, child.name))}
    }
      %endfor
    %else:
    #error Don't know how to print ${item}
    %endif
    printf("</${item.name}>\n");
  %endif
</%def>

void print_xml_${entry.name}(${entry.name}* data)
{
${recursivePrint(entry, '(*data)')}
}
