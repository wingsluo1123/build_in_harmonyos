/*
 * Consumer contract test for the kea 3.2.0 package.
 *
 * Compiles against the packaged public headers (include/kea/**) and links two
 * of the packaged libraries (libkea-exceptions.so, libkea-util.so), then
 * drives their public API the way Kea server, hook and utility code does.  A
 * package that shipped no libraries or no headers fails to link or fails
 * these checks.  Two of the headers pull boost in (util/str.h includes
 * boost/lexical_cast.hpp, dhcp/pkt.h includes boost/date_time and
 * boost/shared_ptr), so the compile also proves the transitive boost headers
 * reach the consumer (the recipe declares transitive_headers).
 *
 * Checks
 *   1. isc_throw(isc::InvalidParameter, ...) throws a catchable isc::Exception
 *   2. what() round-trips the message exactly
 *   3. the exception carries the throwing file/line context
 *   4. what(true) adds the file context to the message (verbose form)
 *   5. isc::Unexpected is catchable through the std::exception hierarchy
 *   6. its what() round-trips the message exactly (std::exception form)
 *   7. the stream form (isc_throw with <<) composes the message
 *   8. isc_throw(isc::OutOfRange, stream) throws
 *   9. isc::util::str::trim (a real symbol of libkea-util.so) executes
 *  10. isc::dhcp::PktPtr from the packaged dhcp/pkt.h is usable
 *
 * Exits non-zero on any failed check.
 */
#include <dhcp/pkt.h>
#include <exceptions/exceptions.h>
#include <util/str.h>

#include <cstring>
#include <iostream>
#include <string>

namespace {

int failures = 0;

void
check(bool cond, const char* what) {
    std::cout << (cond ? "ok   - " : "FAIL - ") << what << std::endl;
    if (!cond) {
        ++failures;
    }
}

std::string
basename_of(const char* path) {
    const char* slash = std::strrchr(path, '/');
    return (slash != nullptr ? std::string(slash + 1) : std::string(path));
}

} // namespace

int
main() {
    // 1-4: the exception model of libkea-exceptions.so.
    bool caught = false;
    try {
        isc_throw(isc::InvalidParameter, "kea-ohos-consumer-probe");
    } catch (const isc::Exception& ex) {
        caught = true;
        check(std::string(ex.what()) == "kea-ohos-consumer-probe",
              "isc::Exception::what() round-trips the message");
        check(basename_of(ex.getFile()) == "test_kea_api.cpp" && ex.getLine() > 0,
              "the exception carries the throwing file/line context");
        const std::string verbose(ex.what(true));
        check(verbose.find("test_kea_api.cpp") != std::string::npos &&
                  verbose.find("kea-ohos-consumer-probe") != std::string::npos,
              "what(true) adds the file context to the message");
    }
    check(caught, "isc_throw(isc::InvalidParameter, ...) throws isc::Exception");

    // 5: the hierarchy reaches std::exception.
    caught = false;
    try {
        isc_throw(isc::Unexpected, "kea-ohos-std-probe");
    } catch (const std::exception& ex) {
        caught = true;
        check(std::string(ex.what()) == "kea-ohos-std-probe",
              "isc exceptions flow through the std::exception hierarchy");
    }
    check(caught, "isc::Unexpected is catchable as std::exception");

    // 6: the stream form used across the Kea code base.
    caught = false;
    try {
        isc_throw(isc::OutOfRange, "value " << 42 << " out of range");
    } catch (const isc::Exception& ex) {
        caught = true;
        check(std::string(ex.what()) == "value 42 out of range",
              "isc_throw stream form composes the message");
    }
    check(caught, "isc_throw(isc::OutOfRange, stream) throws");

    // 7: a real symbol of libkea-util.so.
    check(isc::util::str::trim("  kea-3.2.0 \t") == "kea-3.2.0",
          "isc::util::str::trim executes from libkea-util.so");

    // 8: the packaged dhcp/pkt.h (boost::shared_ptr based) is usable.
    isc::dhcp::PktPtr pkt;
    check(!pkt, "isc::dhcp::PktPtr from dhcp/pkt.h is usable");

    if (failures == 0) {
        std::cout << "kea/3.2.0 consumer contract check OK" << std::endl;
        return 0;
    }
    std::cout << "kea/3.2.0 consumer contract check FAILED (" << failures
              << " check(s))" << std::endl;
    return 1;
}
