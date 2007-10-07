<%namespace file="/decodeentry.tmpl" name="decodeentry" />
<%namespace file="/type.tmpl" name="ctype" />

#include <stdlib.h>

#include "${entry.name}.h"
#include "buffer.h"

${entry.name}* decode_${entry.name}(Buffer* buffer)
{
    ${decodeentry.decode(entry)}
}
