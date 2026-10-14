#ifndef LIBUPNPP_TEST_READFILE_H
#define LIBUPNPP_TEST_READFILE_H

#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <unistd.h>

// The release's TEST_BASE64 main refers to this missing helper. Provide real
// binary file/stdin I/O; do not replace the upstream test or its assertions.
inline bool file_to_string(const std::string& filename, std::string& output,
                           std::string* reason)
{
    std::ifstream file;
    std::istream* input = &std::cin;
    if (!filename.empty()) {
        file.open(filename, std::ios::in | std::ios::binary);
        if (!file) {
            if (reason) *reason = "cannot open input file";
            return false;
        }
        input = &file;
    }
    output.assign(std::istreambuf_iterator<char>(*input),
                  std::istreambuf_iterator<char>());
    if (input->bad()) {
        if (reason) *reason = "input read failed";
        return false;
    }
    return true;
}

#endif
