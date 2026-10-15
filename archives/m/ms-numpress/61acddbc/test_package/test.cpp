// test_package 消费者测试：真实调用 ms-numpress 的编码/解码 API 并验证往返一致
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include <msnumpress/MSNumpress.hpp>

namespace msn = ms::numpress::MSNumpress;

static int fails = 0;

static void check(bool ok, const char *name) {
    std::printf("%s %s\n", ok ? "+ pass" : "- FAIL", name);
    if (!ok) fails++;
}

int main(void) {
    // 与上游 MSNumpressTest.cpp 相同的用例形态：浮点 m/z 数组 linear 编码往返
    std::vector<double> mzs = {
        100.0, 200.0, 300.00005, 400.00010, 450.0, 500.5, 600.25
    };
    const size_t nMzs = mzs.size();

    std::vector<unsigned char> encoded(2 * nMzs * 4 + 16, 0);

    double fixedPoint = msn::optimalLinearFixedPoint(&mzs[0], nMzs);
    check(fixedPoint > 0.0, "optimalLinearFixedPoint returns scaling factor");

    size_t encodedBytes = msn::encodeLinear(&mzs[0], nMzs, &encoded[0], fixedPoint);
    check(encodedBytes > 0, "encodeLinear returns encoded size");

    std::vector<double> decoded(nMzs, 0.0);
    size_t decodedCount = msn::decodeLinear(&encoded[0], encodedBytes, &decoded[0]);
    check(decodedCount == nMzs, "decodeLinear restores element count");

    double maxErr = 0.0;
    for (size_t i = 0; i < nMzs; i++) {
        double e = std::fabs(decoded[i] - mzs[i]);
        if (e > maxErr) maxErr = e;
    }
    check(maxErr < 5e-6, "linear round-trip max error below 5e-6");

    // PIC 编码往返（与上游 MSNumpressTest.cpp encodeDecodePic 同口径：
    // 0..999999 随机整数，解码误差必须 < 0.5）
    std::srand(123459);
    const size_t nPic = 1000;
    std::vector<double> ics(nPic);
    for (size_t i = 0; i < nPic; i++) ics[i] = std::rand() % 1000000;

    std::vector<unsigned char> picEnc(5000, 0);
    size_t picBytes = msn::encodePic(&ics[0], nPic, &picEnc[0]);
    check(picBytes > 0, "encodePic returns encoded size");

    std::vector<double> decodedPic(nPic, 0.0);
    size_t picCount = msn::decodePic(&picEnc[0], picBytes, &decodedPic[0]);
    check(picCount == nPic, "decodePic restores element count");

    double maxPicErr = 0.0;
    for (size_t i = 0; i < nPic; i++) {
        double e = std::fabs(decodedPic[i] - ics[i]);
        if (e > maxPicErr) maxPicErr = e;
    }
    check(maxPicErr < 0.5, "pic round-trip max error below 0.5");

    if (fails > 0) {
        std::printf("FAILED: %d checks failed\n", fails);
        return EXIT_FAILURE;
    }
    std::printf("all tests succeeded! (%zu checks)\n", nMzs);
    return EXIT_SUCCESS;
}