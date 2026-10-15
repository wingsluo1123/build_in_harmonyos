// Consumer smoke test for libkysdk-vector-engine-client on HarmonyOS PC.
//
// Asserts, without any server running:
//   1. VectorDB::Database::Create() returns a usable instance
//      (shared-library load + runtime symbol resolution of the whole
//      grpc/protobuf closure absorbed into the DSO);
//   2. Connect() to a dead endpoint (127.0.0.1:1) performs a real gRPC
//      channel attempt (InsecureChannelCredentials + CreateCustomChannel +
//      WaitForConnected) and returns a non-OK Status with a non-empty
//      message — the graceful error path, not a crash and not a hang;
//   3. Disconnect() recovers cleanly (no crash on teardown).
#include <cstdint>
#include <cstdio>
#include <memory>
#include <string>

#include "kysdk-vector-engine-client/Database.h"
#include "kysdk-vector-engine-client/types/ConnectParam.h"

using namespace VectorDB;

namespace {

int g_failures = 0;

void check(bool cond, const char* label) {
    std::printf("%s %s\n", cond ? "[ok]" : "[fail]", label);
    if (!cond) {
        ++g_failures;
    }
}

}  // namespace

int main() {
    std::shared_ptr<Database> db = Database::Create();
    check(db != nullptr, "Database::Create() returns an instance");

    ConnectParam param(std::string("127.0.0.1"), static_cast<uint16_t>(1));
    param.SetConnectTimeout(500);  // ms; retry loop keeps total below ~8 s
    Status s = db->Connect(param);
    check(!s.IsOk(),
          "Connect() to a dead endpoint returns a non-OK Status (real channel attempt)");
    // The sw_64 stub branch answers NOT_SUPPORTED for everything; a NOT_
    // SUPPORTED code here means the real aarch64 client was not compiled in.
    check(s.Code() != StatusCode::NOT_SUPPORTED,
          "Connect() result is a real gRPC outcome, not the sw_64 stub reply");
    check(!s.Message().empty(), "error Status carries a non-empty message");
    std::printf("     connect status code: %d, message: %s\n",
                static_cast<int>(s.Code()), s.Message().c_str());

    Status d = db->Disconnect();
    check(d.IsOk(), "Disconnect() after a failed connect returns an OK Status");
    std::printf("     disconnect status code: %d\n", static_cast<int>(d.Code()));

    if (g_failures == 0) {
        std::printf("test_vector_client: all checks passed\n");
        return 0;
    }
    std::printf("test_vector_client: %d check(s) failed\n", g_failures);
    return 1;
}
