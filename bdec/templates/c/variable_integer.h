/*  Copyright (C) 2008 Henry Ludemann

    This file is part of the bdec decoder library.

    The bdec decoder library is free software; you can redistribute it
    and/or modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    The bdec decoder library is distributed in the hope that it will be
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty
    of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, see
    <http://www.gnu.org/licenses/>. */

#ifndef VARIABLE_INTEGER_HEADER_FILE
#define VARIABLE_INTEGER_HEADER_FILE

#include "buffer.h"

// Convert a buffer to a big endian integer
unsigned int get_integer(BitBuffer* buffer);
unsigned long long get_long_integer(BitBuffer* buffer);

// Both functions decode an integer from the buffer. There
// must be enough data available.
unsigned int decode_integer(BitBuffer* buffer, int num_bits);
unsigned long long decode_long_integer(BitBuffer* buffer, int num_bits);
unsigned int decode_little_endian_integer(BitBuffer* buffer, int num_bits);

// Encode a big endian integer
void encode_big_endian_integer(unsigned int value, int num_bits, struct EncodedData* result);
void encode_little_endian_integer(unsigned int value, int num_bits, struct EncodedData* result);
void encode_long_big_endian_integer(unsigned long long value, int num_bits, struct EncodedData* result);
void encode_long_little_endian_integer(unsigned long long value, int num_bits, struct EncodedData* result);

// Helper function to print an xml escaped string
void print_escaped_string(Text* text);

#endif
