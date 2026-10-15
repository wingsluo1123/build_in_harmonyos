/* Consumer test for the packaged kmer toolkit.
 *
 * It plays the role of an application that links the installed static
 * libraries (libbio, libutil, ...) through the exported CMake target and drives
 * the public C API declared in the installed headers: the MD5 helpers from
 * libutil and the sequence helpers from libbio.
 */
#include <stdio.h>
#include <string.h>

#include <util.h>
#include <bio.h>

static int checks;
static int failures;

static void check(int condition, const char *name)
{
    checks++;
    if (condition) {
        printf("CHECK-OK: %s\n", name);
    } else {
        failures++;
        printf("CHECK-FAIL: %s\n", name);
    }
}

int main(void)
{
    md5_s   digest;
    char    ascii[33];
    char    seq[16];

    md5_string(&digest, (char *)"abc", 3);
    md5_toascii(&digest, ascii);
    check(strcmp(ascii, "900150983cd24fb0d6963f7d28e17f72") == 0,
          "md5_string(\"abc\") matches the RFC 1321 test vector");

    md5_string(&digest, (char *)"", 0);
    md5_toascii(&digest, ascii);
    check(strcmp(ascii, "d41d8cd98f00b204e9800998ecf8427e") == 0,
          "md5_string(\"\") matches the RFC 1321 empty-string vector");

    strcpy(seq, "abcde");
    reverseString(seq, 5);
    check(strcmp(seq, "edcba") == 0, "reverseString() reverses a sequence in place");

    initCompressionTablesForACGTSpace();
    strcpy(seq, "ACGTT");
    reverseComplementSequence(seq, 5);
    check(strcmp(seq, "AACGT") == 0,
          "reverseComplementSequence() complements and reverses a DNA sequence");

    strcpy(seq, "ACGT");
    reverseComplementSequence(seq, 4);
    check(strcmp(seq, "ACGT") == 0,
          "reverseComplementSequence() leaves a palindromic k-mer unchanged");

    check(uint64MAX == 0xffffffffffffffffULL && uint32MAX == 0xffffffffU,
          "uint64MAX/uint32MAX cover the full width of their types");

    printf("KMER_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    if (failures == 0) {
        printf("KMER_CONSUMER_OK\n");
    }
    return failures == 0 ? 0 : 1;
}
