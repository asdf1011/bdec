## vim:set syntax=mako:
<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />
<%! 
  from bdec.field import Field
  from bdec.sequence import Sequence
 %>

#include <stdio.h>
#include <stdlib.h>

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
<%def name="recursivePrint(entry)">
%for child in entry.children:
${recursivePrint(child)}
%endfor

void print_xml_${entry.name}(${ctype.ctype(entry)} data)
{
    printf("<${entry.name}>\n");
  %if isinstance(entry, Field):
    %if entry.format is Field.INTEGER:
    printf("  %i\n", data); 
    %endif
  %else:
    %for child in entry.children:
    print_xml_${child.name}(data->${child.name});
    %endfor
  %endif
    printf("</${entry.name}>\n");
}
</%def>

${recursivePrint(entry)}
