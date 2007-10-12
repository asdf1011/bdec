#ifndef BIT_BUFFER_HEADER_FILE
#define BIT_BUFFER_HEADER_FILE

// Structure to hold data to be decoded
typedef struct 
{
    unsigned char* buffer;
    // The start bit is the offset in buffer to start decoding at. It should
    // be in the range [0,8).
    unsigned int start_bit;
    unsigned char* end;
}BitBuffer;

// Structure to hold bit aligned data to be decoded.
typedef struct
{
    unsigned char* buffer;
    int length;
}Buffer;

#endif
