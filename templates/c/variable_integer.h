
#ifndef VARIABLE_INTEGER_HEADER_FILE
#define VARIABLE_INTEGER_HEADER_FILE

#include "buffer.h"

// Convert a buffer to a big endian integer
int get_integer(BitBuffer* buffer);

// Both functions decode an integer from the buffer. There
// must be enough data available.
int decode_integer(BitBuffer* buffer, int num_bits);
int decode_little_endian_integer(BitBuffer* buffer, int num_bits);

#endif
