// indi-starbook-ten consumer test (R34: exercises the real public C++ API).
// The package vendors the StarBook protocol client (starbook_ten.cpp/.h +
// bundled httplib.h). We stand up an httplib::Server on localhost answering
// canned StarBook mount responses, then call the real StarbookTen public
// API and assert request handling + response parsing end to end — no
// telescope hardware required.
#include <cstdio>
#include <exception>
#include <thread>
#include <chrono>
#include "starbook_ten.h"

static int failures = 0;

#define CHECK(cond)                                              \
    do {                                                         \
        if (!(cond)) {                                           \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);     \
            ++failures;                                          \
        }                                                        \
    } while (0)

int main(void)
{
    httplib::Server svr;

    svr.Get("/version", [](const httplib::Request &, httplib::Response &res) {
        res.set_content("<!--VERSION=5.10-->", "text/plain");
    });
    svr.Get("/getstatus2", [](const httplib::Request &, httplib::Response &res) {
        res.set_content("<!--RA=5.5000&DEC=-20.2500&GOTO=0&STATE=SCOPE-->",
                        "text/html");
    });
    svr.Get("/get_pierside", [](const httplib::Request &, httplib::Response &res) {
        res.set_content("<html>PIERSIDE=1</html>", "text/html");
    });
    svr.Get("/stop", [](const httplib::Request &, httplib::Response &res) {
        res.set_content("<!--OK-->", "text/html");
    });

    int port = svr.bind_to_any_port("127.0.0.1");
    if (port <= 0) {
        printf("FAIL: cannot bind mock server\n");
        return 1;
    }
    std::thread serverThread([&svr]() { svr.listen_after_bind(); });
    for (int i = 0; i < 100 && !svr.is_running(); ++i)
        std::this_thread::sleep_for(std::chrono::milliseconds(10));

    try {
        httplib::Client client("127.0.0.1", port);
        StarbookTen mount(&client);

        // Real API 1: getFirmwareVersion() — GET /version + regex parse.
        auto fw = mount.getFirmwareVersion();
        printf("firmware: %d.%d (expect 5.10)\n",
               std::get<0>(fw), std::get<1>(fw));
        CHECK(std::get<0>(fw) == 5 && std::get<1>(fw) == 10);

        // Real API 2: getStatus() — GET /getstatus2 + structured parse.
        StarbookTen::MountStatus st = mount.getStatus();
        printf("status: ra=%.4f dec=%.4f goto=%d state=%d\n",
               st.ra, st.dec, (int)st.goto_busy, (int)st.state);
        CHECK(st.ra == 5.5 && st.dec == -20.25);
        CHECK(st.goto_busy == false);
        CHECK(st.state == StarbookTen::STATE_SCOPE);

        // Real API 3: getPierSide() — enum mapping (1 -> PIERSIDE_EAST).
        CHECK(mount.getPierSide() == StarbookTen::PIERSIDE_EAST);

        // Real API 4: stop() — command endpoint validated by <!--OK-->.
        CHECK(mount.stop() == true);
    } catch (const std::exception &e) {
        printf("FAIL: unexpected exception: %s\n", e.what());
        ++failures;
    }

    svr.stop();
    serverThread.join();

    if (failures == 0) {
        printf("PASS: StarbookTen public API exercised against mock mount\n");
        return 0;
    }
    printf("FAILED: %d checks\n", failures);
    return 1;
}
