/*  Copyright (C) 2010 Henry Ludemann
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
    SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    */

#include <assert.h>
#include <stdio.h>
#include "variable_integer.h"

unsigned int get_integer(const BitBuffer* buffer)
{
    /* We'll just create a copy of the buffer, and decode it's value. */
    BitBuffer temp = *buffer;
    return decode_integer(&temp, temp.num_bits);
}

uint64_t get_long_integer(const BitBuffer* buffer)
{
    /* We'll just create a copy of the buffer, and decode it's value. */
    BitBuffer temp = *buffer;
    return decode_long_integer(&temp, temp.num_bits);
}

unsigned int decode_integer(BitBuffer* buffer, int num_bits)
{
    unsigned int result = 0;
    unsigned char mask;
    int bits_used;
    unsigned int unused_trailing_bits;
    unsigned int data;
    while (num_bits > 0)
    {
        assert(buffer->num_bits > 0);

        /* We need to mask the higher and lower bits we don't care about */
        mask = 0xFF >> buffer->start_bit;
        if (buffer->start_bit + num_bits > 8)
        {
            bits_used = 8 - buffer->start_bit;
        }
        else
        {
            bits_used = num_bits;
        }
        unused_trailing_bits = 8 - bits_used - buffer->start_bit;
        data = (buffer->buffer[0] & mask) >> unused_trailing_bits;

        buffer->start_bit += bits_used;
        buffer->num_bits -= bits_used;
        assert(buffer->start_bit <= 8);
        if (buffer->start_bit == 8)
        {
            ++buffer->buffer;
            buffer->start_bit = 0;
        }
        num_bits -= bits_used;
        result |= data << num_bits;
    }
    return result;
}

uint64_t decode_long_integer(BitBuffer* buffer, int num_bits)
{
    uint64_t result = 0;
    while (num_bits > 0)
    {
        int size = num_bits > 32 ? 32 : num_bits;
        result <<= size;
        result |= decode_integer(buffer, size);
        num_bits -= size;
    }
    return result;
}

unsigned int decode_little_endian_integer(BitBuffer* buffer, int num_bits)
{
    int i;
    unsigned int result = 0;

    /* Little endian conversion only works for fields that are a multiple
       of 8 bits. */
    assert(num_bits % 8  == 0);
    for (i = 0; i < num_bits / 8; ++i)
    {
        result |= decode_integer(buffer, 8) << (i * 8);
    }
    return result;
}

uint64_t decode_long_little_endian_integer(BitBuffer* buffer, int num_bits)
{
    int i;
    uint64_t result = 0;
    uint64_t value;

    /* Little endian conversion only works for fields that are a multiple
       of 8 bits. */
    assert(num_bits % 8  == 0);
    for (i = 0; i < num_bits / 8; ++i)
    {
        value = decode_integer(buffer, 8);
        result |= value << (i * 8);
    }
    return result;
}

void print_escaped_string(const Text* text)
{
    char c;
    unsigned int i;
    for (i = 0; i < text->length; ++i)
    {
        c = text->buffer[i];
        /* The list of 'safe' xml characters is from
           http://www.w3.org/TR/REC-xml/#NT-Char */
        if (c == '<')
        {
            printf("&lt;");
        }
        else if (c == '>')
        {
            printf("&gt;");
        }
        else if (c == '&')
        {
            printf("&amp;");
        }
        else if (c >= 0x20 || c == 0x9 || c == 0xa || c == 0xd)
        {
            putc(c, stdout);
        }
        else
        {
            /* This character cannot be represented in xml */
            putc('?', stdout);
        }
    }
}

int encode_big_endian_integer(unsigned int value, unsigned int num_bits, struct EncodedData* result)
{
    char* buffer;
    int shiftDistance;
    int isFirstByteOverlapping;

    if (num_bits < sizeof(value) * 8 && (value >> num_bits) != 0)
    {
        /* This number is too big to store in num_bits. */
        return 0;
    }

    ensureEncodeSpace(result, num_bits);
    buffer = &result->buffer[result->num_bits / 8];
    shiftDistance = num_bits - (8 - result->num_bits % 8);
    isFirstByteOverlapping = (result->num_bits % 8 != 0);
    if (shiftDistance >= 0)
    {
        if (isFirstByteOverlapping)
        {
            isFirstByteOverlapping = 0;
            /* We need to OR the first byte (to fill the first byte) */
            *(buffer++) |= (value >> shiftDistance) & 0xFF;
            shiftDistance -= 8;
        }
        /* We can now proceed to write whole bytes to the output */
        while (shiftDistance >= 0)
        {
            *(buffer++) = (value >> shiftDistance) & 0xFF;
            shiftDistance -= 8;
        }
    }
    /* If we still have data left, it needs to be shifted to the left */
    if (shiftDistance > -8)
    {
        if (!isFirstByteOverlapping)
        {
            *(buffer++) = (value << (-shiftDistance)) & 0xFF;
        }
        else
        {
            *(buffer++) |= (value << (-shiftDistance)) & 0xFF;
        }
    }
    result->num_bits += num_bits;
    return 1;
}

int encode_little_endian_integer(unsigned int value, unsigned int num_bits, struct EncodedData* result)
{
    unsigned int i;
    for (i = 0; i < num_bits / 8; ++i)
    {
        encode_big_endian_integer(value & 0xFF, 8, result);
        value >>= 8;
    }
    return value == 0;
}

int encode_long_big_endian_integer(uint64_t value, unsigned int num_bits, struct EncodedData* result)
{
    unsigned int upper;

    if (num_bits < sizeof(value) * 8 && (value >> num_bits) != 0)
    {
        /* This number is too big to store in num_bits. */
        return 0;
    }

    if (num_bits > 32)
    {
        /* Encode the highest four bytes */
        num_bits -= 32;
        upper = value >> num_bits;
        encode_big_endian_integer(upper, 32, result);
        value -= ((uint64_t)upper) << num_bits;
    }
    return encode_big_endian_integer(value, num_bits, result);
}

int encode_long_little_endian_integer(uint64_t value, unsigned int num_bits, struct EncodedData* result)
{
    unsigned int i;
    for (i = 0; i < num_bits / 8; ++i)
    {
        encode_big_endian_integer(value & 0xFF, 8, result);
        value >>= 8;
    }
    return value == 0;
}

int64_t ${'divide with rounding' | function}(int64_t numerator, int64_t denominator, int should_round_up)
{
    int64_t result = numerator / denominator;
    int64_t remainder = numerator % denominator;
    if (remainder != 0)
    {
        if ((numerator < 0 && denominator > 0) || (numerator > 0 && denominator < 0))
        {
            /* C division is round towards zero, but this function implements round
               towards negative infinity... */
            --result;
        }
    }
    if (should_round_up && remainder != 0)
    {
        ++result;
    }
    return result;
}

