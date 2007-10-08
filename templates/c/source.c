<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />
<%! 
  from bdec.field import Field
  from bdec.sequence import Sequence
 %>

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
