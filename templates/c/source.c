## vim:set syntax=mako:
<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />
<%! 
  from bdec.choice import Choice
  from bdec.field import Field
  from bdec.sequence import Sequence
 %>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "${entry.name}.h"
#include "buffer.h"

## Recursively create functions for decoding the entries contained within this protocol specification.
<%def name="recursiveDecode(entry)">
%for child in entry.children:
  %if not isinstance(child, Field):
${recursiveDecode(child)}
  %endif
%endfor

int decode_${entry.name}(Buffer* buffer, ${entry.name}* result)
{
  %if isinstance(entry, Field):
    ${decodeField(entry, "*result")};
    return 1;
  %elif isinstance(entry, Sequence):
    ${decodeentry.decodeSequence(entry)}
    return 1;
  %elif isinstance(entry, Choice):
    memset(result, 0, sizeof(${entry.name}));
    Buffer temp;
    %for child in entry.children:
    // Attempt to decode ${child}...
      %if isinstance(child, Field):
    if (buffer->buffer + ${child.length / 8} <= buffer->end)
    {
        ${ctype.ctype(child)} ${decodeentry.decodeFieldValue(child, 'temp_' + child.name)}
        %if child.expected is not None:
        if (temp_${child.name} == ${int(child.expected)})
        {
            result->${child.name} = malloc(sizeof(${ctype.ctype(child)}));
            *result->${child.name} = temp_${child.name};
            buffer->buffer += ${child.length / 8};
            return 1;
        }
        %else:
        result->${child.name} = malloc(sizeof(${ctype.ctype(child)}));
        *result->${child.name} = *temp;
        buffer->buffer += ${entry.length / 8};
        return 1;
        %endif
    }
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
<%def name="recursivePrint(entry, variable)">
    printf("<${entry.name}>\n");
  %if isinstance(entry, Field):
    %if entry.format is Field.INTEGER:
    printf("  %i\n", ${variable}); 
    %elif entry.format is Field.TEXT:
    printf("  %s\n", ${variable});
    %endif
  %elif isinstance(entry, Sequence):
    %for child in entry.children:
    ${recursivePrint(child, '%s->%s' % (variable, child.name))}
    %endfor
  %elif isinstance(entry, Choice):
    %for child in entry.children:
    if (${'%s->%s' % (variable, child.name)} != 0)
    {
        %if isinstance(child, Field):
        ${recursivePrint(child, "*%s->%s" % (variable, child.name))}
        %else:
        ${recursivePrint(child, "%s->%s" % (variable, child.name))}
        %endif
    }
    %endfor
  %else:
    #error Don't know how to print ${entry}
  %endif
    printf("</${entry.name}>\n");
</%def>

void print_xml_${entry.name}(${ctype.ctype(entry)} data)
{
${recursivePrint(entry, 'data')}
}
