/*  Copyright (C) 2010-2011 Henry Ludemann
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
    <http://www.gnu.org/licenses/>.
 
 This file incorporates work covered by the following copyright and  
 permission notice:  
  
    Copyright (c) 2010, PRESENSE Technologies GmbH
    All rights reserved.
    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the PRESENSE Technologies GmbH nor the
          names of its contributors may be used to endorse or promote products
          derived from this software without specific prior written permission.
    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
    ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL PRESENSE Technologies GmbH BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
    LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
    ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. */

#ifndef VARIABLE_INTEGER_HEADER_FILE
#define VARIABLE_INTEGER_HEADER_FILE

#include "buffer.h"

#ifdef __cplusplus
extern "C" {
#endif

/* Convert a buffer to a big endian integer */
unsigned int get_integer(const BitBuffer* buffer);
uint64_t get_long_integer(const BitBuffer* buffer);

/* Both functions decode an integer from the buffer. There
   must be enough data available. */
unsigned int decode_integer(BitBuffer* buffer, int num_bits);
uint64_t decode_long_integer(BitBuffer* buffer, int num_bits);
unsigned int decode_little_endian_integer(BitBuffer* buffer, int num_bits);
uint64_t decode_long_little_endian_integer(BitBuffer* buffer, int num_bits);

/* Encode a big endian integer */
void encode_big_endian_integer(unsigned int value, int num_bits, struct EncodedData* result);
void encode_little_endian_integer(unsigned int value, int num_bits, struct EncodedData* result);
void encode_long_big_endian_integer(uint64_t value, int num_bits, struct EncodedData* result);
void encode_long_little_endian_integer(uint64_t value, int num_bits, struct EncodedData* result);

/* Helper function to print an xml escaped string */
void print_escaped_string(const Text* text);

/* Divide with round towards either negative infinity or postive infinity. */
int64_t ${'divide with rounding' | function}(int64_t numerator, int64_t denominator, int should_round_up);
/* TODO: Add a normal width integer version of this function... */

#ifdef __cplusplus
}
#endif

#endif
