
#include <assert.h>
#include "variable_integer.h"

int get_integer(BitBuffer* buffer)
{
    // We'll just create a copy of the buffer, and decode it's value.
    BitBuffer temp = *buffer;
    return decode_integer(&temp, temp.num_bits);
}

int decode_integer(BitBuffer* buffer, int num_bits)
{
    int result = 0;
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

int decode_little_endian_integer(BitBuffer* buffer, int num_bits)
{
    // Little endian conversion only works for fields that are a multiple
    // of 8 bits.
    assert(num_bits % 8  == 0);

    int i;
    int result = 0;
    for (i = 0; i < num_bits / 8; ++i)
    {
        result |= decode_integer(buffer, 8) << (i * 8);
    }
    return result;
}
