#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <iostream>
#include <string>
#include <vector>

// HarmonyOS (OHOS aarch64) consumer feasibility test.
//
// Intentionally assertion-free: every check is performed via an explicit
// boolean comparison and a non-zero process exit code on failure, so the test
// outcome is observable without relying on assert()/abort(). It substantively
// exercises the cppzmq C++ wrapper AND the underlying libzmq (zeromq) runtime
// over a real inproc transport on OpenHarmony, proving the port actually works
// end-to-end on the target platform.

static int g_failures = 0;

static void check(bool cond, const char* what) {
    if (!cond) {
        std::cerr << "OHOS consumer test FAILED: " << what << std::endl;
        ++g_failures;
    } else {
        std::cout << "OK: " << what << std::endl;
    }
}

int main() {
    try {
        zmq::context_t ctx(1);
        check(ctx.handle() != nullptr, "zmq::context_t created on OHOS");

        zmq::socket_t rep(ctx, zmq::socket_type::rep);
        zmq::socket_t req(ctx, zmq::socket_type::req);
        rep.bind("inproc://ohos_consumer_test");
        req.connect("inproc://ohos_consumer_test");

        // Single-part round trip. REQ/REP is a strict state machine: a REQ may
        // not send again until it has received the reply, so we must drive a
        // full request->reply cycle (REQ send, REP recv, REP send, REQ recv)
        // before the sockets return to a neutral state.
        std::string payload = "HarmonyOS cppzmq consumer";
        zmq::message_t out(payload.begin(), payload.end());
        bool sent = req.send(out, zmq::send_flags::none).has_value();
        check(sent, "REQ socket send() succeeded");

        zmq::message_t in;
        bool received = rep.recv(in, zmq::recv_flags::none).has_value();
        check(received, "REP socket recv() succeeded");
        check(in.to_string() == payload, "round-trip payload matches");

        // Complete the cycle so REQ/REP return to a neutral state.
        zmq::message_t reply(payload.begin(), payload.end());
        bool reply_sent = rep.send(reply, zmq::send_flags::none).has_value();
        check(reply_sent, "REP socket send() reply succeeded");
        zmq::message_t reply_in;
        bool reply_recv = req.recv(reply_in, zmq::recv_flags::none).has_value();
        check(reply_recv, "REQ socket recv() reply succeeded");

        // Multipart round trip via zmq_addon. PAIR sockets have no state
        // machine, so they are safe for free-form send/recv of multipart
        // messages over a fresh inproc endpoint.
        zmq::socket_t pair_a(ctx, zmq::socket_type::pair);
        zmq::socket_t pair_b(ctx, zmq::socket_type::pair);
        pair_a.bind("inproc://ohos_consumer_multipart");
        pair_b.connect("inproc://ohos_consumer_multipart");

        std::vector<zmq::message_t> parts;
        // NB: construct from std::string, NOT a char literal. The
        // `message_t(const Char (&data)[N])` overload treats a string literal as
        // a char array and includes the trailing NUL terminator in the message
        // size; the std::string overload uses str.size() and avoids that.
        parts.emplace_back(zmq::message_t(std::string("part-a")));
        parts.emplace_back(zmq::message_t(std::string("part-b")));
        auto sres = zmq::send_multipart(pair_a, std::move(parts));
        check(sres.has_value(), "zmq::send_multipart() succeeded");

        std::vector<zmq::message_t> got;
        auto rres = zmq::recv_multipart(pair_b, std::back_inserter(got));
        check(rres.has_value(), "zmq::recv_multipart() succeeded");
        check(got.size() == 2, "multipart message has 2 frames");
        if (got.size() == 2) {
            check(got[0].to_string() == "part-a", "multipart frame[0] matches");
            check(got[1].to_string() == "part-b", "multipart frame[1] matches");
        }
    } catch (const zmq::error_t& e) {
        std::cerr << "OHOS consumer test exception: " << e.what() << std::endl;
        return 2;
    }

    if (g_failures == 0) {
        std::cout << "OHOS consumer test PASSED (cppzmq + zeromq on OpenHarmony aarch64)"
                  << std::endl;
        return 0;
    }
    std::cerr << g_failures << " check(s) failed" << std::endl;
    return 1;
}
