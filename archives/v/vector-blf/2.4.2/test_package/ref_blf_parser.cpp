// test_package/ref_blf_parser.cpp
//
// INDEPENDENT reference implementation used by the OHOS end-to-end consumer case.
//
// It deliberately does NOT link vector-blf: it parses the BLF byte stream itself
// (file statistics header, LOG_CONTAINER framing, zlib payload, object stream,
// CAN_MESSAGE fields) and emits the same key=value report as test_ohos_e2e.cpp.
// test_compare then diffs the two reports, so a library that silently changed the
// on-disk format, mis-encoded a field or mis-counted its statistics is caught.
//
// Layout implemented (per upstream Vector/BLF headers):
//   FileStatistics  144 B: signature(LOGG,u32) statisticsSize(u32) apiNumber(u32)
//                          applicationId/comprLevel/appMajor/appMinor(u8 x4)
//                          fileSize(u64) uncompressedFileSize(u64)
//                          objectCount(u32) applicationBuild(u32)
//                          measurementStartTime(16) lastObjectTime(16)
//                          restorePointsOffset(u64) reserved(u32 x16)
//   LogContainer     32 B header + compressed payload, padded by objectSize % 4:
//                          ObjectHeaderBase(signature LOBJ, headerSize, headerVersion,
//                          objectSize, objectType=10) method(u16) r1(u16) r2(u32)
//                          uncompressedFileSize(u32) r3(u32) payload
//   Object stream    concatenation of all containers' payloads, then objects:
//                          ObjectHeaderBase(16) [+16 ObjectHeader] + fields
//   CAN_MESSAGE (1)  ObjectHeader: objectFlags(u32) clientIndex(u16) objectVersion(u16)
//                          objectTimeStamp(u64); then channel(u16) flags(u8) dlc(u8)
//                          id(u32) data[8]
//
// 用法: ref_blf_parser <blf-file> <report-path>

#include <zlib.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

namespace {

const std::uint32_t kObjectSignature = 0x4A424F4C;  // "LOBJ"
const std::uint32_t kFileSignature = 0x47474F4C;    // "LOGG"
const std::size_t kStatisticsSize = 144;
const std::uint32_t kLogContainer = 10;
const std::uint32_t kCanMessage = 1;

std::uint64_t fnv1a(std::uint64_t h, const void * data, std::size_t len) {
    const unsigned char * p = static_cast<const unsigned char *>(data);
    for (std::size_t i = 0; i < len; ++i) {
        h ^= p[i];
        h *= 1099511628211ULL;
    }
    return h;
}

std::uint16_t rd16(const std::vector<unsigned char> & b, std::size_t o) {
    std::uint16_t v; std::memcpy(&v, &b[o], sizeof(v)); return v;
}
std::uint32_t rd32(const std::vector<unsigned char> & b, std::size_t o) {
    std::uint32_t v; std::memcpy(&v, &b[o], sizeof(v)); return v;
}
std::uint64_t rd64(const std::vector<unsigned char> & b, std::size_t o) {
    std::uint64_t v; std::memcpy(&v, &b[o], sizeof(v)); return v;
}

struct Msg {
    std::uint16_t channel {};
    std::uint8_t flags {};
    std::uint8_t dlc {};
    std::uint32_t id {};
    unsigned char data[8] {};
    std::uint32_t objFlags {};
    std::uint64_t timestamp {};
};

std::string hexBytes(const unsigned char * p, std::size_t n) {
    static const char * hex = "0123456789abcdef";
    std::string out;
    for (std::size_t i = 0; i < n; ++i) {
        out.push_back(hex[(p[i] >> 4) & 0xF]);
        out.push_back(hex[p[i] & 0xF]);
    }
    return out;
}

// zlib inflate of one container payload
bool inflatePayload(const unsigned char * src, std::size_t src_len,
                    std::size_t expected, std::vector<unsigned char> & out) {
    out.assign(expected, 0);
    if (expected == 0)
        return true;
    uLongf dst_len = static_cast<uLongf>(expected);
    const int rc = ::uncompress(out.data(), &dst_len,
                                reinterpret_cast<const Bytef *>(src),
                                static_cast<uLong>(src_len));
    if (rc != Z_OK) {
        std::cerr << "independent parser: inflate failed rc=" << rc << std::endl;
        return false;
    }
    out.resize(dst_len);
    return dst_len == expected;
}

}  // namespace

int main(int argc, char * argv[]) {
    if (argc < 3) {
        std::cerr << "usage: ref_blf_parser <blf-file> <report-path>" << std::endl;
        return 2;
    }
    const std::string blf_path = argv[1];
    const std::string report_path = argv[2];

    std::ifstream in(blf_path.c_str(), std::ios::binary);
    if (!in) {
        std::cerr << "independent parser: cannot open " << blf_path << std::endl;
        return 1;
    }
    std::vector<unsigned char> buf((std::istreambuf_iterator<char>(in)),
                                   std::istreambuf_iterator<char>());
    if (buf.size() < kStatisticsSize) {
        std::cerr << "independent parser: file too small" << std::endl;
        return 1;
    }

    // ---- file statistics header ----
    if (rd32(buf, 0) != kFileSignature) {
        std::cerr << "independent parser: bad LOGG signature" << std::endl;
        return 1;
    }
    if (rd32(buf, 4) != kStatisticsSize) {
        std::cerr << "independent parser: unexpected statisticsSize" << std::endl;
        return 1;
    }
    // signature(0) statisticsSize(4) apiNumber(8) applicationId/compressionLevel/
    // applicationMajor/applicationMinor(12..15) fileSize(16) uncompressedFileSize(24)
    // objectCount(32) applicationBuild(36) measurementStartTime(40) lastObjectTime(56)
    // restorePointsOffset(72) reserved(80..143)
    const std::uint64_t header_file_size = rd64(buf, 16);
    const std::uint64_t header_uncompressed = rd64(buf, 24);
    const std::uint64_t header_object_count = rd32(buf, 32);

    // ---- containers ----
    std::vector<std::uint32_t> container_sizes;
    std::vector<std::uint16_t> container_methods;
    std::vector<std::uint32_t> container_uncompressed;
    std::vector<unsigned char> stream;
    std::size_t pos = kStatisticsSize;
    while (pos + 16 <= buf.size()) {
        if (rd32(buf, pos) != kObjectSignature)
            break;
        const std::uint32_t object_size = rd32(buf, pos + 8);
        const std::uint32_t object_type = rd32(buf, pos + 12);
        if (object_type != kLogContainer || pos + 32 > buf.size())
            break;
        const std::uint16_t method = rd16(buf, pos + 16);
        const std::uint32_t uncompressed = rd32(buf, pos + 24);
        const std::size_t payload_len = object_size - 32;
        if (pos + object_size > buf.size()) {
            std::cerr << "independent parser: truncated container" << std::endl;
            return 1;
        }
        if (method == 0) {
            stream.insert(stream.end(), buf.begin() + pos + 32,
                          buf.begin() + pos + 32 + payload_len);
        } else if (method == 2) {
            std::vector<unsigned char> inflated;
            if (!inflatePayload(&buf[pos + 32], payload_len, uncompressed, inflated))
                return 1;
            stream.insert(stream.end(), inflated.begin(), inflated.end());
        } else {
            std::cerr << "independent parser: unknown compressionMethod " << method << std::endl;
            return 1;
        }
        container_sizes.push_back(object_size);
        container_methods.push_back(method);
        container_uncompressed.push_back(uncompressed);
        pos += object_size + (object_size % 4);  // LogContainer::read() padding rule
    }

    // ---- object stream ----
    // The library's own bookkeeping: 144 + sum(internalHeaderSize(32) + uncompressed)
    std::uint64_t computed_uncompressed = kStatisticsSize;
    for (std::uint32_t u : container_uncompressed)
        computed_uncompressed += 32ULL + u;

    std::uint64_t digest = 1469598103934665603ULL;
    std::uint32_t objects = 0;
    Msg first {}, last {};
    std::size_t i = 0;
    while (i + 16 <= stream.size()) {
        if (rd32(stream, i) != kObjectSignature) {
            std::cerr << "independent parser: bad object signature at " << i << std::endl;
            return 1;
        }
        const std::uint32_t object_size = rd32(stream, i + 8);
        const std::uint32_t object_type = rd32(stream, i + 12);
        if (object_size < 16 || i + object_size > stream.size()) {
            std::cerr << "independent parser: invalid object size" << std::endl;
            return 1;
        }
        if (object_type == kCanMessage) {
            const std::size_t p = i;
            Msg m;
            m.objFlags = rd32(stream, p + 16);
            m.timestamp = rd64(stream, p + 24);
            m.channel = rd16(stream, p + 32);
            m.flags = stream[p + 34];
            m.dlc = stream[p + 35];
            m.id = rd32(stream, p + 36);
            std::memcpy(m.data, &stream[p + 40], 8);

            digest = fnv1a(digest, &m.channel, sizeof(m.channel));
            digest = fnv1a(digest, &m.flags, sizeof(m.flags));
            digest = fnv1a(digest, &m.dlc, sizeof(m.dlc));
            digest = fnv1a(digest, &m.id, sizeof(m.id));
            digest = fnv1a(digest, m.data, 8);
            digest = fnv1a(digest, &m.objFlags, sizeof(m.objFlags));
            digest = fnv1a(digest, &m.timestamp, sizeof(m.timestamp));

            if (objects == 0)
                first = m;
            last = m;
        }
        ++objects;
        i += object_size;
    }
    const std::size_t trailing = stream.size() - i;

    // ---- report (同一 key 口径，前缀 ref: 的为独立实现额外信息) ----
    char digest_hex[32];
    std::snprintf(digest_hex, sizeof(digest_hex), "%016llx",
                  static_cast<unsigned long long>(digest));
    std::vector<std::string> lines;
    auto kv = [&lines](const std::string & k, const std::string & v) { lines.push_back(k + "=" + v); };
    auto num = [](unsigned long long v) { return std::to_string(v); };

    kv("case", "ohos-e2e-consumer");
    kv("path", blf_path);
    kv("file_size", num(buf.size()));
    kv("objects_total", num(objects));
    kv("can_messages", num(objects));
    kv("expected_messages", "6000");
    kv("header_object_count", num(header_object_count));
    kv("header_uncompressed_size", num(header_uncompressed));
    kv("fields_digest", digest_hex);
    kv("first_channel", num(first.channel));
    kv("first_flags", num(first.flags));
    kv("first_dlc", num(first.dlc));
    kv("first_id", num(first.id));
    kv("first_data", hexBytes(first.data, 8));
    kv("first_objflags", num(first.objFlags));
    kv("first_timestamp", num(first.timestamp));
    kv("last_channel", num(last.channel));
    kv("last_flags", num(last.flags));
    kv("last_dlc", num(last.dlc));
    kv("last_id", num(last.id));
    kv("last_data", hexBytes(last.data, 8));
    kv("last_objflags", num(last.objFlags));
    kv("last_timestamp", num(last.timestamp));

    kv("ref:containers", num(container_sizes.size()));
    {
        std::string methods, sizes, uncomps;
        for (std::size_t k = 0; k < container_methods.size(); ++k) {
            if (k) { methods += ","; sizes += ","; uncomps += ","; }
            methods += std::to_string(container_methods[k]);
            sizes += std::to_string(container_sizes[k]);
            uncomps += std::to_string(container_uncompressed[k]);
        }
        kv("ref:compression_methods", methods);
        kv("ref:container_bytes", sizes);
        kv("ref:container_uncompressed_sizes", uncomps);
    }
    kv("ref:computed_header_uncompressed_size", num(computed_uncompressed));
    kv("ref:header_file_size", num(header_file_size));
    kv("ref:stream_bytes", num(stream.size()));
    kv("ref:trailing_bytes", num(trailing));

    std::ofstream out(report_path.c_str());
    for (const std::string & l : lines)
        out << l << "\n";
    out.close();

    std::cout << "independent reference parser: " << objects << " objects, "
              << container_sizes.size() << " containers, "
              << "stream=" << stream.size() << " B, trailing=" << trailing
              << " B, digest=" << digest_hex << std::endl;
    return 0;
}
