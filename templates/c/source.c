## vim:set syntax=mako:
<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />
<%! 
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

${entry.name}* decode_${entry.name}(Buffer* buffer)
{
  %if isinstance(entry, Field):
    ${decodeField(entry, entry.name + " result")};
    return result;
  %elif isinstance(entry, Sequence):
    ${decodeentry.decodeSequence(entry)}
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
  %else:
    %for child in entry.children:
    ${recursivePrint(child, '%s->%s' % (variable, child.name))}
    %endfor
  %endif
    printf("</${entry.name}>\n");
</%def>

void print_xml_${entry.name}(${ctype.ctype(entry)} data)
{
${recursivePrint(entry, 'data')}
}
