// Smoke test for Wt 4.14.0 on OHOS: serve a plain-text WResource through
// the packaged wthttp connector on the loopback interface, fetch it at
// socket level and assert both the HTTP status line and the application
// marker. (A WApplication page delivers its body progressively via
// JavaScript; a plain WResource makes the served marker deterministic.)
#include <Wt/WResource.h>
#include <Wt/WServer.h>
#include <Wt/Http/Response.h>

#include <arpa/inet.h>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <unistd.h>

namespace {

class HelloResource : public Wt::WResource {
public:
    ~HelloResource() override = default;

protected:
    void handleRequest(const Wt::Http::Request& /*request*/,
                       Wt::Http::Response& response) override {
        response.setMimeType("text/plain");
        response.out() << "HELLO_WT_OK" << std::endl;
    }
};

bool fetch_path(const std::string& host, int port, const std::string& path,
                std::string& out) {
    int fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return false;
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(static_cast<uint16_t>(port));
    if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
        ::close(fd);
        return false;
    }
    if (::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        ::close(fd);
        return false;
    }
    std::string req =
        "GET " + path + " HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n";
    if (::send(fd, req.data(), req.size(), 0) < 0) {
        ::close(fd);
        return false;
    }
    char buf[8192];
    out.clear();
    for (;;) {
        ssize_t n = ::recv(fd, buf, sizeof(buf), 0);
        if (n <= 0) break;
        out.append(buf, static_cast<size_t>(n));
        if (out.size() > 1024 * 1024) break;  // 1 MiB safety cap
    }
    ::close(fd);
    return !out.empty();
}

}  // namespace

int main() {
    const int port = 18087;
    Wt::WServer server("wt_smoke");
    char arg0[] = "wt_smoke";
    char argDocroot[] = "--docroot";
    char argDot[] = ".";
    char argAddr[] = "--http-address";
    char argLoopback[] = "127.0.0.1";
    char argPort[] = "--http-port";
    char portBuf[8];
    std::snprintf(portBuf, sizeof(portBuf), "%d", port);
    char* argv[] = {arg0, argDocroot, argDot, argAddr, argLoopback,
                    argPort, portBuf, nullptr};
    int argc = 7;
    try {
        server.setServerConfiguration(argc, argv);
        auto resource = std::make_shared<HelloResource>();
        server.addResource(resource, "/hello");
        server.start();
    } catch (const std::exception& e) {
        std::cerr << "server setup failed: " << e.what() << std::endl;
        return 2;
    }

    std::string page;
    bool ok = false;
    for (int i = 0; i < 60 && !ok; ++i) {  // up to ~30 s for the accept loop
        if (fetch_path("127.0.0.1", port, "/hello", page)) {
            ok = true;
        } else {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
    }
    server.stop();

    if (!ok) {
        std::cerr << "no HTTP response from 127.0.0.1:" << port << std::endl;
        return 3;
    }
    if (page.find("HTTP/1.") == std::string::npos) {
        std::cerr << "not an HTTP response: " << page.substr(0, 64) << std::endl;
        return 4;
    }
    if (page.find("HELLO_WT_OK") == std::string::npos) {
        std::cerr << "application marker missing from served page"
                  << std::endl;
        return 5;
    }
    std::cout << "WT_SMOKE_OK: served " << page.size()
              << " bytes, status line + marker verified" << std::endl;
    return 0;
}
