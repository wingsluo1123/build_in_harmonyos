// Consumer test for mbtserver 0.17: verify the packaged library is usable.
//
// Includes the single public header <mbtserver/MbtServerBase.h> (which
// transitively requires the ticcutils/mbt dependency headers) and takes the
// addresses of MbtServer::StartServer and MbtServer::StartJSONServer, forcing
// the linker to resolve real symbols from libmbtserver.a. A broken package
// (missing library, missing headers, or missing symbols) fails this link.
//
// NOTE: MbtServerBase.h declares "static std::string VersionInfo(bool)" but
// upstream never defines it in any .cxx, so this test deliberately does not
// reference it (referencing it would be a link error caused by upstream,
// not by the packaging).
#include <iostream>

#include "mbtserver/MbtServerBase.h"

int main() {
    void (*start_server)(TiCC::CL_Options&) = &MbtServer::StartServer;
    void (*start_json_server)(TiCC::CL_Options&) = &MbtServer::StartJSONServer;
    if (start_server == 0 || start_json_server == 0) {
        std::cerr << "mbtserver 0.17: failed to resolve server entry points" << std::endl;
        return 1;
    }
    std::cout << "mbtserver 0.17: StartServer/StartJSONServer symbols resolved" << std::endl;
    return 0;
}
