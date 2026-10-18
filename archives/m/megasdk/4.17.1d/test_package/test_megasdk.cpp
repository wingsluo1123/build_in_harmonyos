// test_megasdk.cpp -- consumer test for megasdk/4.17.1d (R34: real API use).
//
// Six local-only checks (no network, no account): they link against the
// packaged libmega and exercise real SDK entry points.
// Each passing check prints "MEGASDK-CHECK <name> OK"; the final line
// "MEGASDK_CHECKS_PASSED=a/b" is the single deterministic counting source.
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>

#include <mega/base64.h>
#include <megaapi.h>

static int failures = 0;

#define CHECK(name, cond)                                              \
    do {                                                               \
        if (cond) {                                                    \
            std::cout << "MEGASDK-CHECK " << name << " OK" << std::endl; \
        } else {                                                       \
            std::cout << "MEGASDK-CHECK " << name << " FAIL" << std::endl; \
            ++failures;                                                \
        }                                                              \
    } while (0)

int main()
{
    // 1. Base64 roundtrip through the SDK codec (handle encoding path).
    std::string plain = "MEGA-SDK-OHOS-consumer-test";
    std::string encoded = mega::Base64::btoa(plain);
    std::string decoded = mega::Base64::atob(encoded);
    CHECK("base64-roundtrip", !encoded.empty() && decoded == plain);

    // 2. Empty input stays empty (no crash on zero length).
    std::string empty_enc = mega::Base64::btoa(std::string(""));
    std::string empty_dec = mega::Base64::atob(empty_enc);
    CHECK("base64-empty", empty_enc.empty() && empty_dec.empty());

    // 3. Integer codec roundtrip.
    std::string num;
    mega::Base64::itoa(123456789, &num);
    int64_t back = mega::Base64::atoi(&num);
    CHECK("base64-itoa", back == 123456789);

    // 4. URL escaping roundtrip (request signing path).
    std::string url = "hello world/test?x=1&y=2";
    std::string escaped, unescaped;
    mega::URLCodec::escape(&url, &escaped);
    mega::URLCodec::unescape(&escaped, &unescaped);
    CHECK("urlcodec-roundtrip", !escaped.empty() && unescaped == url);

    // 5. Proxy object roundtrip (pure local configuration object).
    mega::MegaProxy proxy;
    bool proxy_ok = (proxy.getProxyType() == mega::MegaProxy::PROXY_AUTO);
    proxy.setProxyType(mega::MegaProxy::PROXY_CUSTOM);
    proxy.setProxyURL("http://127.0.0.1:8080");
    proxy.setCredentials("user", "pass");
    proxy_ok = proxy_ok
        && proxy.getProxyType() == mega::MegaProxy::PROXY_CUSTOM
        && std::string(proxy.getProxyURL()) == "http://127.0.0.1:8080"
        && proxy.credentialsNeeded()
        && std::string(proxy.getUsername()) == "user";
    CHECK("proxy-roundtrip", proxy_ok);

    // 6. Full client object construction/destruction (links the whole
    // libmega, starts/stops worker threads, no login -> no network).
    // Uses a dedicated empty subdir under the writable TMPDIR (upstream
    // MegaApiTest defaults basePath to nullptr = no local cache; passing
    // the TMPDIR root itself shares the dir with other workers/files, so
    // a fresh subdir is the closest faithful local-cache exercise).
    // stderr progress markers stay in consumer_test.log even if the SDK
    // aborts, pinpointing construct vs destruct for the next preflight.
    const char* tmp = getenv("TMPDIR");
    if (!tmp) tmp = getenv("TMP");
    if (!tmp) tmp = getenv("TEMP");
    std::string base = (tmp && tmp[0]) ? tmp : ".";
    std::string cache = base + "/test_megaapi_cache";
    ::mkdir(cache.c_str(), 0700);
    std::fprintf(stderr, "MEGASDK-PROGRESS megaapi-construct begin base=%s\n",
                 cache.c_str());
    std::fflush(stderr);
    mega::MegaApi* api = new mega::MegaApi("megasdk-conan-test-key",
                                           cache.c_str(),
                                           "megasdk-conan-test/1.0");
    bool api_ok = (api != nullptr);
    std::fprintf(stderr, "MEGASDK-PROGRESS megaapi-construct end api=%p\n",
                 (void*)api);
    std::fflush(stderr);
    delete api;
    std::fprintf(stderr, "MEGASDK-PROGRESS megaapi-destroyed\n");
    std::fflush(stderr);
    CHECK("megaapi-lifecycle", api_ok);

    const int total = 6;
    const int passed = total - failures;
    std::cout << "MEGASDK_CHECKS_PASSED=" << passed << "/" << total << std::endl;
    return failures == 0 ? 0 : 1;
}
