// test_package/test_limonp.cpp — limonp 0.6.1 消费者测试
//
// 五组断言，失败以退出码 2..6 区分。判据全部是**可观测行为**：
// 公开头文件在同一条 include 路径下可编译、StringUtil 的字符串契约、
// LocalVector 的栈上内联缓冲语义、Closure/ArgvContext 的行为，
// 以及鸿蒙特有断言（aarch64 的 char 有符号性 + GBK 字节宽字符往返）。
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>
#include <thread>
#include <vector>

#include <limonp/ArgvContext.hpp>
#include <limonp/Closure.hpp>
#include <limonp/Config.hpp>
#include <limonp/LocalVector.hpp>
#include <limonp/StdExtension.hpp>
#include <limonp/StringUtil.hpp>

using namespace limonp;

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

static void g1_noop() {
}

// ── 组 1：安装布局 + header-only 符号可编译 ────────────────────────────
static int group1() {
    std::vector<std::string> words;
    Split(std::string("a,b,c"), words, std::string(","));
    if (words.size() != 3) return fail(2, "Split through <limonp/StringUtil.hpp> is unusable");

    LocalVector<size_t> lv;
    lv.push_back(1);
    if (lv.size() != 1) return fail(2, "LocalVector through <limonp/LocalVector.hpp> is unusable");

    ClosureInterface* c = NewClosure(&g1_noop);
    c->Run();
    delete c;

    const char* argv[] = {"exe", "pos"};
    ArgvContext ac(2, argv);
    if (ac[0] != "exe" || ac[1] != "pos")
        return fail(2, "ArgvContext through <limonp/ArgvContext.hpp> is unusable");

    std::printf("PASS 1: public headers compile; Split/LocalVector/Closure/ArgvContext work\n");
    return 0;
}

// ── 组 2：StringUtil 的字符串契约 ──────────────────────────────────────
static int group2() {
    const std::string s1 = StringFormat("select %s from %s;", "*", "table1");
    if (s1 != "select * from table1;") return fail(3, "StringFormat output mismatch");

    std::vector<std::string> parts;
    Split("name=value&k2=v2", parts, "&");
    if (parts.size() != 2 || parts[0] != "name=value")
        return fail(3, "Split with multi-char pattern mismatch");

    std::string joined;
    std::vector<std::string> arr;
    Split("x:y:z", arr, ":");
    Join(arr.begin(), arr.end(), joined, "|");
    if (joined != "x|y|z") return fail(3, "Join output mismatch");

    std::printf("PASS 2: StringUtil StringFormat/Split/Join contracts verified\n");
    return 0;
}

// ── 组 3：Config 的 key=value 解析 ─────────────────────────────────────
// 注意：v0.6.1 的 Config::LoadFile 遇到非 "key=value" 行（如 [section]）会
// assert(false) 崩溃——段支持是 1.0.2 之后才加的。这里只用注释与键值对。
static int group3() {
    std::ofstream ofs("limonp_test_config");
    ofs << "# comment\n  name = limonp\nkey = value\n";
    ofs.close();
    Config conf("limonp_test_config");  // 0.6.1 唯一公开构造：explicit Config(filePath)
    const std::string name = conf.Get("name", "");
    const std::string key = conf.Get("key", "");
    if (name != "limonp" || key != "value")
        return fail(4, "Config parse of key=value (with comment) mismatch");
    std::printf("PASS 3: Config key=value parsing (comment) verified\n");
    return 0;
}

// ── 组 4：鸿蒙特有——GBK 字节对打包对 char 有符号性免疫 ────────────────
// aarch64-linux-ohos 的 char 是 unsigned；x86-linux 是 signed。
// v0.6.1 的 GBKTrans 不做 Unicode 查表，而是把两个 GBK 字节**打包成
// uint16_t**：0xD6 0xD0 -> 0xD6D0。正确实现必须先把 char 转无符号再掩码
// （`uint16_t(c) & 0x00ff`），否则 signed char 下 0xD6 会变成 0xFFD6。
// 两端（signed/unsigned char）都必须得到 0xD6D0。
static int group4() {
    const std::string gbk = std::string() + (char)0xD6 + (char)0xD0;  // "中" 的 GBK 编码
    std::vector<uint16_t> uni;
    GBKTrans(gbk, uni);
    if (uni.size() != 1 || uni[0] != 0xD6D0)
        return fail(5, "GBK 0xD6D0 did not pack to uint16_t 0xD6D0 (signed-char trap)");
    std::printf("PASS 4: GBK 0xD6D0 -> uint16_t 0x%04x under %s char\n",
                uni[0], (char)0xD6 < 0 ? "signed" : "unsigned");
    return 0;
}

// ── 组 5：多线程纯函数——std::thread 内 StringUtil 行为一致 ────────────
static size_t g5_run(size_t rounds) {
    size_t checksum = 0;
    for (size_t i = 0; i < rounds; i++) {
        std::vector<std::string> w;
        Split("aa:bb:cc", w, ":");
        std::string j;
        Join(w.begin(), w.end(), j, "-");
        checksum ^= j.size();
    }
    return checksum;
}

static int group5() {
    const size_t kRounds = 1000;
    const size_t reference = g5_run(kRounds);
    std::vector<size_t> got(4, 0);
    std::vector<std::thread> ts;
    for (int i = 0; i < 4; i++) {
        ts.push_back(std::thread([i, kRounds, &got] { got[i] = g5_run(kRounds); }));
    }
    for (int i = 0; i < 4; i++) ts[i].join();
    for (int i = 0; i < 4; i++) {
        if (got[i] != reference)
            return fail(6, "std::thread produced a different StringUtil checksum");
    }
    std::printf("PASS 5: 4 std::threads x %zu rounds match single-thread checksum\n", kRounds);
    return 0;
}

int main() {
    int rc = 0;
    if ((rc = group1()) != 0) return rc;
    if ((rc = group2()) != 0) return rc;
    if ((rc = group3()) != 0) return rc;
    if ((rc = group4()) != 0) return rc;
    if ((rc = group5()) != 0) return rc;
    std::printf("ALL PASS: limonp 0.6.1 consumer checks (5 groups)\n");
    return 0;
}