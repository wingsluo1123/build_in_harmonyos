// test_package/test_ohos_e2e.cpp
//
// HarmonyOS-specific end-to-end consumer case for the vector-blf package.
//
// 构造输入 → 真实执行 → 产出结果 → 校验内容:
//
//   1. 构造输入: 6000 条确定性 CAN 报文（id/channel/flags/dlc/data/timestamp 全部由
//      固定公式生成，无随机数），经安装后的库写入 $TMPDIR 下的 BLF 文件。
//      * OHOS 平台特性: /tmp 只读（E002），因此必须用 $TMPDIR（HMDFS）；
//        报文总量 6000 x 48 B = 288000 B > 2 x 128 KiB 默认日志容器，落盘时会
//        触发多个 zlib 压缩 LOG_CONTAINER（compressionMethod=2）。
//   2. 真实执行: 把库当引擎跑完整流程 —— 写盘(压缩)/关闭/重开/全量流式读回，
//      并做第二遍读回（OHOS 上 /tmp 只读，故全部 I/O 落在 $TMPDIR/HMDFS）。
//      注: OHOS ELF 可加载性由独立探针 ohos_dlopen_probe 验证——它不链接本库，
//      因而加载器是在新进程里首次映射该产物（此处 in-process dlopen 会因
//      动态链接已在 main() 之前完成而失去意义）。
//   3. 产出结果: 写出确定性报告（key=value，字段与取值均可复现）。
//   4. 校验内容: 每条报文字段与构造公式逐项比对 + objectSize==calculateObjectSize()
//      + 文件头统计与库自身记账一致 + 第二遍读回摘要一致；
//      随后由 test_compare 与独立实现 ref_blf_parser 的报告逐行比对
//      （参考实现不链接 vector-blf，自行解析 BLF 容器/对象字节）。
//
// 用法: test_ohos_e2e <report-path> [blf-path]
//       blf-path 缺省为 $TMPDIR/vector_blf_ohos_e2e.blf（OHOS 上 /tmp 只读，见 E002）

#include <sys/stat.h>
#include <unistd.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include <Vector/BLF.h>

namespace {

const std::uint32_t kMessages = 6000;  // 6000 * 48 = 288000 B > 2 个 128 KiB 容器
const std::uint32_t kPayloadBytes = 8;

int g_failures = 0;
int g_checks = 0;

void check(bool ok, const char * what) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        std::cerr << "FAIL: " << what << std::endl;
    }
}

std::string scratchDir() {
    const char * tmp = std::getenv("TMPDIR");
    std::string dir = (tmp != nullptr && *tmp != '\0') ? std::string(tmp) : std::string(".");
    if (dir[dir.size() - 1] != '/')
        dir += '/';
    return dir;
}

// FNV-1a 64 over the on-disk field order of one CAN message.
std::uint64_t fnv1a(std::uint64_t h, const void * data, std::size_t len) {
    const unsigned char * p = static_cast<const unsigned char *>(data);
    for (std::size_t i = 0; i < len; ++i) {
        h ^= p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

std::uint16_t expChannel(std::uint32_t i) { return static_cast<std::uint16_t>(1 + (i % 4)); }
std::uint8_t expFlags(std::uint32_t i) { return static_cast<std::uint8_t>((i % 2) ? 1 : 0); }
std::uint8_t expByte(std::uint32_t i, std::uint32_t b) {
    return static_cast<std::uint8_t>((i * 7U + b) & 0xFFU);
}
std::uint64_t expTimestamp(std::uint32_t i) { return static_cast<std::uint64_t>(i) * 1000ULL; }

std::string hexBytes(const std::uint8_t * p, std::size_t n) {
    static const char * hex = "0123456789abcdef";
    std::string out;
    for (std::size_t i = 0; i < n; ++i) {
        out.push_back(hex[(p[i] >> 4) & 0xF]);
        out.push_back(hex[p[i] & 0xF]);
    }
    return out;
}

struct MsgView {
    std::uint16_t channel {};
    std::uint8_t flags {};
    std::uint8_t dlc {};
    std::uint32_t id {};
    std::uint8_t data[kPayloadBytes] {};
    std::uint32_t objFlags {};
    std::uint64_t timestamp {};
};

// Reads the whole object stream and folds every message into the digest.
// Returns false when an object is not a well-formed CAN message.
bool consume(Vector::BLF::File & file, std::uint64_t & digest, std::uint32_t & messages,
             std::uint32_t & objects, MsgView * first, MsgView * last) {
    while (file.good()) {
        Vector::BLF::ObjectHeaderBase * ohb = nullptr;
        try {
            ohb = file.read();
        } catch (const std::exception & e) {
            std::cerr << "read() threw: " << e.what() << std::endl;
            return false;
        }
        if (ohb == nullptr)
            break;
        ++objects;
        if (ohb->objectSize != ohb->calculateObjectSize())
            return false;
        if (ohb->objectType != Vector::BLF::ObjectType::CAN_MESSAGE)
            return false;
        auto * msg = dynamic_cast<Vector::BLF::CanMessage *>(ohb);
        if (msg == nullptr)
            return false;

        const std::uint32_t i = messages;
        MsgView v;
        v.channel = msg->channel;
        v.flags = msg->flags;
        v.dlc = msg->dlc;
        v.id = msg->id;
        std::memcpy(v.data, msg->data.data(), kPayloadBytes);
        v.objFlags = msg->objectFlags;
        v.timestamp = msg->objectTimeStamp;

        // field-by-field comparison against the construction formula
        if (v.channel != expChannel(i) || v.flags != expFlags(i) ||
            v.dlc != static_cast<std::uint8_t>(kPayloadBytes) || v.id != 0x100U + i ||
            v.timestamp != expTimestamp(i)) {
            delete ohb;
            return false;
        }
        for (std::uint32_t b = 0; b < kPayloadBytes; ++b) {
            if (v.data[b] != expByte(i, b)) {
                delete ohb;
                return false;
            }
        }

        digest = fnv1a(digest, &v.channel, sizeof(v.channel));
        digest = fnv1a(digest, &v.flags, sizeof(v.flags));
        digest = fnv1a(digest, &v.dlc, sizeof(v.dlc));
        digest = fnv1a(digest, &v.id, sizeof(v.id));
        digest = fnv1a(digest, v.data, kPayloadBytes);
        digest = fnv1a(digest, &v.objFlags, sizeof(v.objFlags));
        digest = fnv1a(digest, &v.timestamp, sizeof(v.timestamp));

        if (messages == 0 && first != nullptr)
            *first = v;
        if (last != nullptr)
            *last = v;
        ++messages;
        delete ohb;
    }
    return true;
}

}  // namespace

int main(int argc, char * argv[]) {
    const std::string report_path = (argc > 1) ? argv[1] : "vector_blf_ohos_e2e.report";
    const std::string dir = scratchDir();
    const std::string blf_path = (argc > 2) ? std::string(argv[2]) : (dir + "vector_blf_ohos_e2e.blf");
    std::remove(blf_path.c_str());

    /* ---------- 1. 构造输入 + 写盘（OHOS FS + zlib 压缩容器） ---------- */
    {
        Vector::BLF::File file;
        file.open(blf_path, std::ios_base::out);
        check(file.is_open(), "create OHOS blf file under $TMPDIR");
        if (!file.is_open())
            return 1;
        for (std::uint32_t i = 0; i < kMessages; ++i) {
            auto * msg = new Vector::BLF::CanMessage;
            msg->channel = expChannel(i);
            msg->flags = expFlags(i);
            msg->dlc = static_cast<std::uint8_t>(kPayloadBytes);
            msg->id = 0x100U + i;
            msg->objectTimeStamp = expTimestamp(i);
            for (std::uint32_t b = 0; b < kPayloadBytes; ++b)
                msg->data[b] = expByte(i, b);
            file.write(msg);
        }
        file.close();
        check(!file.is_open(), "close flushes and closes the file");
    }

    struct stat st {};
    check(::stat(blf_path.c_str(), &st) == 0, "written file is stat-able");
    const std::uint64_t file_size = static_cast<std::uint64_t>(st.st_size);
    check(file_size > 0, "written file is non-empty");

    /* ---------- 2. 真实执行: 全量读回 + 第二遍 + 头统计 ---------- */
    std::uint64_t digest = 1469598103934665603ULL;
    std::uint32_t messages = 0, objects = 0;
    MsgView first {}, last {};
    std::uint64_t header_object_count = 0, header_uncompressed_size = 0;
    {
        Vector::BLF::File file;
        file.open(blf_path);
        check(file.is_open(), "reopen written file for reading");
        if (!file.is_open())
            return 1;
        check(consume(file, digest, messages, objects, &first, &last),
              "every read object matches the constructed CAN message");
        header_object_count = file.fileStatistics.objectCount;
        header_uncompressed_size = file.fileStatistics.uncompressedFileSize;
        file.close();
    }
    check(messages == kMessages, "all messages were read back");
    check(objects == kMessages, "object stream holds exactly the written messages");
    check(header_object_count == kMessages, "file header objectCount matches");
    check(header_uncompressed_size > kMessages * 48ULL,
          "file header uncompressed size includes container headers");

    // second pass: same digest -> deterministic on the OHOS filesystem
    std::uint64_t digest2 = 1469598103934665603ULL;
    std::uint32_t messages2 = 0, objects2 = 0;
    {
        Vector::BLF::File file;
        file.open(blf_path);
        check(consume(file, digest2, messages2, objects2, nullptr, nullptr),
              "second pass verifies all messages again");
        file.close();
    }
    const bool second_pass_equal = (digest2 == digest && messages2 == messages);
    check(second_pass_equal, "second read pass yields the identical digest");

    /* ---------- 3. 缺失文件（平台 FS 行为） ---------- */
    {
        Vector::BLF::File file;
        file.open(dir + "vector_blf_ohos_e2e_absent.blf");
        check(!file.is_open(), "absent file is reported through is_open()");
    }

    /* ---------- 产出结果 ---------- */
    const std::uint64_t fnv_offset = 1469598103934665603ULL;
    char digest_hex[32];
    std::snprintf(digest_hex, sizeof(digest_hex), "%016llx",
                  static_cast<unsigned long long>(digest));

    std::vector<std::string> lines;
    auto kv = [&lines](const std::string & k, const std::string & v) {
        lines.push_back(k + "=" + v);
    };
    auto num = [](unsigned long long v) { return std::to_string(v); };

    kv("case", "ohos-e2e-consumer");
    kv("path", blf_path);
    kv("file_size", num(file_size));
    kv("objects_total", num(objects));
    kv("can_messages", num(messages));
    kv("expected_messages", num(kMessages));
    kv("header_object_count", num(header_object_count));
    kv("header_uncompressed_size", num(header_uncompressed_size));
    kv("fields_digest", digest_hex);
    kv("first_channel", num(first.channel));
    kv("first_flags", num(first.flags));
    kv("first_dlc", num(first.dlc));
    kv("first_id", num(first.id));
    kv("first_data", hexBytes(first.data, kPayloadBytes));
    kv("first_objflags", num(first.objFlags));
    kv("first_timestamp", num(first.timestamp));
    kv("last_channel", num(last.channel));
    kv("last_flags", num(last.flags));
    kv("last_dlc", num(last.dlc));
    kv("last_id", num(last.id));
    kv("last_data", hexBytes(last.data, kPayloadBytes));
    kv("last_objflags", num(last.objFlags));
    kv("last_timestamp", num(last.timestamp));
    kv("lib:second_pass_equal", second_pass_equal ? "1" : "0");
    kv("lib:tmpdir", dir);
    kv("lib:fnv_offset", num(fnv_offset));

    std::ofstream out(report_path.c_str());
    for (const std::string & l : lines)
        out << l << "\n";
    out.close();
    out.flush();
    check(out.good(), "report written");

    std::cout << "OHOS e2e consumer: " << messages << " messages, " << objects
              << " objects, file=" << file_size << " B, uncompressed="
              << header_uncompressed_size << " B, digest=" << digest_hex
              << ", checks=" << g_checks
              << ", failures=" << g_failures << std::endl;
    return g_failures == 0 ? 0 : 1;
}
