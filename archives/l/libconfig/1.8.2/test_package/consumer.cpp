#include <libconfig.h++>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <unistd.h>

#define CHECK(expr) do { if (!(expr)) { std::fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #expr); std::exit(1); } } while (0)

int main() {
    libconfig::Config cfg, restored;
    cfg.readString("answer=42; label=\"C++配置\"; big=4294967297L;");
    int answer = 0;
    std::string label;
    long long big = 0;
    CHECK(cfg.lookupValue("answer", answer) && answer == 42);
    CHECK(cfg.lookupValue("label", label) && label == "C++配置");
    CHECK(cfg.lookupValue("big", big) && big == 4294967297LL);
    bool missing = false;
    try { cfg.lookup("not_present"); } catch (const libconfig::SettingNotFoundException &) { missing = true; }
    CHECK(missing);
    bool wrong_type = false;
    try { const char *text = cfg.lookup("answer"); (void)text; } catch (const libconfig::SettingTypeException &) { wrong_type = true; }
    CHECK(wrong_type);
    const char *tmp = std::getenv("TMPDIR");
    CHECK(tmp != nullptr && tmp[0] == '/');
    std::string path = std::string(tmp) + "/cpp-" + std::to_string(getpid()) + ".cfg";
    cfg.writeFile(path.c_str());
    restored.readFile(path.c_str());
    CHECK(restored.lookupValue("answer", answer) && answer == 42);
    CHECK(unlink(path.c_str()) == 0);
    std::puts("CPP_API_EXCEPTIONS_ROUNDTRIP_PASS");
}
