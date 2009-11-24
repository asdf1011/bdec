
#include <assert.h>

#include "buffer.h"
#include "variable_integer.h"

union FloatConversion
{
    unsigned char buffer[8];
    float floatValue;
    double doubleValue;
};

Encoding getMachineEncoding()
{
    union {
        long int l;
        unsigned char c[sizeof (long int)];
    } u;
    u.l = 1;

    // Derived from http://stackoverflow.com/questions/280162/is-there-a-way-to-do-a-c-style-compile-time-assertion-to-determine-machines-en
    return u.c[0] == 1 ? BDEC_LITTLE_ENDIAN : BDEC_BIG_ENDIAN;
}

static void convertEndian(Encoding encoding, unsigned char output[], BitBuffer* data)
{
    int numBytes = data->num_bits / 8;
    if (encoding == getMachineEncoding())
    {
        for (int i = 0; i < numBytes; ++i)
        {
            output[i] = decode_integer(data, 8);
        }
    }
    else
    {
        for (int i = 0; i < numBytes; ++i)
        {
            output[numBytes - 1 - i] = decode_integer(data, 8);
        }
    }
}

double decodeFloat(BitBuffer* data, Encoding encoding)
{
    assert(data->num_bits == 32);
    union FloatConversion conv;
    convertEndian(encoding, conv.buffer, data);
    return conv.floatValue;
}

double decodeDouble(BitBuffer* data, Encoding encoding)
{
    assert(data->num_bits == 64);
    union FloatConversion conv;
    convertEndian(encoding, conv.buffer, data);
    return conv.doubleValue;
}

