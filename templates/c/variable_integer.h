
#ifndef VARIABLE_INTEGER_HEADER_FILE
#define VARIABLE_INTEGER_HEADER_FILE

#include "buffer.h"

// Both functions decode an integer from the buffer. There
// must be enough data available.
int decode_integer(Buffer* buffer, int num_bits);
int decode_little_endian_integer(Buffer* buffer, int num_bits);

#endif
