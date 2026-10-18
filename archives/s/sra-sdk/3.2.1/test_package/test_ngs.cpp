/* Consumer test: open a read collection through the NGS C++ API.
 * The path does not exist, so a well-formed ErrorMsg must be raised by the
 * SDK. This exercises the ngs-c++ wrapper plus the VDB reader backend. */

#include <ngs/ncbi/NGS.hpp>
#include <ngs/ErrorMsg.hpp>

#include <iostream>

int main()
{
    try
    {
        ncbi::NGS::openReadCollection("/nonexistent/ohos-sra-sdk-read-collection");
        std::cerr << "opening a missing collection unexpectedly succeeded\n";
        return 1;
    }
    catch (const ngs::ErrorMsg &e)
    {
        std::cout << "expected SDK error: " << e.what() << "\n";
    }

    return 0;
}
