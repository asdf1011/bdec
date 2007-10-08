<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />
<%! from bdec.field import Field %>

#include <stdlib.h>

#include "${entry.name}.h"
#include "buffer.h"

<%def name="decodeChildren(entry)">
%for child in entry.children:
%if not isinstance(child, Field):
${child.name}* decode_${child.name}(Buffer* buffer)
{
    ${decodeentry.decode(child)}
}

${decodeChildren(child)}
%endif
%endfor
</%def>

${decodeChildren(entry)}

${entry.name}* decode_${entry.name}(Buffer* buffer)
{
    ${decodeentry.decode(entry)}
}
