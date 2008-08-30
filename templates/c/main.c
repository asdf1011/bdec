
#include <stdio.h>
#include <stdlib.h>

#include "${protocol.name |filename}.h"

void usage(char* program)
{
    fprintf(stderr, "Usage:\n");
    fprintf(stderr, "\t%s <binary file>\n", program);
}

int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        /* Bad number of arguments */
        fprintf(stderr, "Bad number of arguments!\n");
        usage(argv[0]);
        return 1;
    }
    char* filename = argv[1];
    FILE* datafile = fopen(filename, "rb");
    if (datafile == 0)
    {
        /* Failed to open file */
        fprintf(stderr, "Failed to open file!\n");
        return 2;
    }
    fseek(datafile, 0, SEEK_END);
    long int length = ftell(datafile);
    fseek(datafile, 0, SEEK_SET);

    /* Load the data file into memory */
    unsigned char* data = malloc(length);
    fread(data, length, 1, datafile);
    fclose(datafile);

    /* Attempt to decode the file */
    BitBuffer buffer = {data, 0, length * 8};
    ${settings.ctype(protocol)} result;
    if (!${settings.decode_name(protocol)}(&buffer, &result))
    {
        /* Decode failed! */
        fprintf(stderr, "Decode failed!\n");
        free(data);
        return 3;
    }

    /* Print the decoded data */
    ${settings.print_name(protocol)}(&result, 0);
    ${settings.free_name(protocol)}(&result);
    free(data);
    return 0;
}

