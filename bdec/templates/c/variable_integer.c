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

#include <assert.h>
#include <stdio.h>
#include "variable_integer.h"

unsigned int get_integer(BitBuffer* buffer)
{
    // We'll just create a copy of the buffer, and decode it's value.
    BitBuffer temp = *buffer;
    return decode_integer(&temp, temp.num_bits);
}

unsigned long long get_long_integer(BitBuffer* buffer)
{
    // We'll just create a copy of the buffer, and decode it's value.
    BitBuffer temp = *buffer;
    return decode_long_integer(&temp, temp.num_bits);
}

unsigned int decode_integer(BitBuffer* buffer, int num_bits)
{
    unsigned int result = 0;
    while (num_bits > 0)
    {
        assert(buffer->num_bits > 0);

        // We need to mask the higher and lower bits we don't care about
        unsigned char mask = 0xFF >> buffer->start_bit;
        int bits_used;// = 8 - buffer->start_bit;
        if (buffer->start_bit + num_bits > 8)
        {
            bits_used = 8 - buffer->start_bit;
        }
        else
        {
            bits_used = num_bits;
        }
        unsigned int unused_trailing_bits = 8 - bits_used - buffer->start_bit;
        unsigned int data = (buffer->buffer[0] & mask) >> unused_trailing_bits;

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

unsigned long long decode_long_integer(BitBuffer* buffer, int num_bits)
{
    unsigned long long result = 0;
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
    // Little endian conversion only works for fields that are a multiple
    // of 8 bits.
    assert(num_bits % 8  == 0);

    int i;
    unsigned int result = 0;
    for (i = 0; i < num_bits / 8; ++i)
    {
        result |= decode_integer(buffer, 8) << (i * 8);
    }
    return result;
}

void print_escaped_string(Text* text)
{
    char c;
    unsigned int i;
    for (i = 0; i < text->length; ++i)
    {
        c = text->buffer[i];
        // The list of 'safe' xml characters is from
        // http://www.w3.org/TR/REC-xml/#NT-Char
        if (c == '<')
        {
            printf("&lt;");
        }
        else if (c == '>')
        {
            printf("&gt;");
        }
        else if (c >= 0x20 || c == 0x9 || c == 0xa || c == 0xd)
        {
            putc(c, stdout);
        }
        else
        {
            // This character cannot be safely represent in xml
            putc('?', stdout);
        }
    }
}

void encode_big_endian_integer(unsigned int value, int num_bits, struct EncodedData* result)
{
    ensureEncodeSpace(result, num_bits);
    char* buffer = &result->buffer[result->num_bits / 8];
    int shiftDistance = num_bits - (8 - result->num_bits % 8);
    int isFirstByteOverlapping = (result->num_bits % 8 != 0);
    if (shiftDistance >= 0)
    {
        if (isFirstByteOverlapping)
        {
            isFirstByteOverlapping = 0;
            // We need to OR the first byte (to fill the first byte)
            *(buffer++) |= (value >> shiftDistance) & 0xFF;
            shiftDistance -= 8;
        }
        // We can now proceed to write whole bytes to the output
        while (shiftDistance >= 0)
        {
            *(buffer++) = (value >> shiftDistance) & 0xFF;
            shiftDistance -= 8;
        }
    }
    // If we still have data left, it needs to be shifted to the left
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
}

void encode_little_endian_integer(unsigned int value, int num_bits, struct EncodedData* result)
{
    int i;
    for (i = 0; i < num_bits / 8; ++i)
    {
        encode_big_endian_integer(value & 0xFF, 8, result);
        value >>= 8;
    }
}

