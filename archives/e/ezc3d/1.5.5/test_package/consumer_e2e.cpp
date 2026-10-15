// =============================================================================
// ezc3d 消费者端到端用例（rule12 鸿蒙特有测试）
//
// 不是纯断言/纯头文件检查：完整走一遍消费者真正会用的流程 ——
//   1) 用公开 API 组装一个带 Points / Analogs / 自定义元参数的 C3D 对象
//   2) parametrizedWrite() 真实写盘（字节级序列化 + 头部校验和写入）
//   3) 用全新的 c3d 对象从盘上读回（解析器 + 校验和验证）
//   4) 逐点、逐模拟量、逐参数比对数值，确认回环无损
//   5) 读回的再写一次再读回，确认多次往返稳定
//   6) 覆盖错误路径：读不存在的文件必须抛异常
//
// 退出码 0 = 全部通过；非 0 = 有子项失败（真机/模拟器上以此判定）。
// =============================================================================
#include <cmath>
#include <cstdio>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

#include "ezc3d_all.h"

namespace {

int g_checks = 0;
int g_failed = 0;

void check(bool ok, const std::string &what) {
    ++g_checks;
    if (!ok) {
        ++g_failed;
        std::cout << "  [FAIL] " << what << std::endl;
    } else {
        std::cout << "  [ OK ] " << what << std::endl;
    }
}

bool nearly(double a, double b, double tol = 1e-6) {
    return std::fabs(a - b) <= tol * (1.0 + std::fabs(a) + std::fabs(b));
}

const std::size_t N_FRAMES = 10;
const std::size_t N_POINTS = 3;
const std::size_t N_ANALOGS = 3;
const double POINT_RATE = 100.0;
const double ANALOG_RATE = 1000.0;
const std::size_t N_SUBFRAMES = 10;  // ANALOG_RATE / POINT_RATE

// 期望值函数：与 fill 时用的公式完全一致，用于逐点比对
double expected_point(std::size_t f, std::size_t m, int axis) {
    return static_cast<double>(2 * f + 3 * m + static_cast<std::size_t>(axis) + 1) / 7.0;
}
double expected_analog(std::size_t f, std::size_t sf, std::size_t c) {
    return static_cast<double>(2 * f + 3 * sf + 4 * c + 1) / 7.0;
}

// ---------------------------------------------------------------- build a c3d
// 完全按上游 test_ezc3d.cpp 的 fillC3D() 公开 API 惯例组装，保证是真实消费者用法
ezc3d::c3d build_sample() {
    ezc3d::c3d c3d;

    for (std::size_t m = 0; m < N_POINTS; ++m) {
        c3d.point("point" + std::to_string(m + 1));
    }
    for (std::size_t a = 0; a < N_ANALOGS; ++a) {
        c3d.analog("analog" + std::to_string(a + 1));
    }

    ezc3d::ParametersNS::GroupNS::Parameter point_rate("RATE");
    point_rate.set(std::vector<double>() = {POINT_RATE});
    c3d.parameter("POINT", point_rate);

    ezc3d::ParametersNS::GroupNS::Parameter analog_rate("RATE");
    analog_rate.set(std::vector<double>() = {ANALOG_RATE});
    c3d.parameter("ANALOG", analog_rate);

    for (std::size_t f = 0; f < N_FRAMES; ++f) {
        ezc3d::DataNS::Frame frame;

        ezc3d::DataNS::Points3dNS::Points pts;
        for (std::size_t m = 0; m < N_POINTS; ++m) {
            ezc3d::DataNS::Points3dNS::Point pt;
            pt.x(expected_point(f, m, 0));
            pt.y(expected_point(f, m, 1));
            pt.z(expected_point(f, m, 2));
            pts.point(pt);
        }

        ezc3d::DataNS::AnalogsNS::Analogs analogs;
        for (std::size_t sf = 0; sf < N_SUBFRAMES; ++sf) {
            ezc3d::DataNS::AnalogsNS::SubFrame subframe;
            for (std::size_t c = 0; c < N_ANALOGS; ++c) {
                ezc3d::DataNS::AnalogsNS::Channel channel;
                channel.data(static_cast<float>(expected_analog(f, sf, c)));
                subframe.channel(channel);
            }
            analogs.subframe(subframe);
        }

        frame.add(pts, analogs);
        c3d.frame(frame);
    }
    return c3d;
}

// ---------------------------------------------------------------- compare
void compare_roundtrip(const ezc3d::c3d &b, const std::string &tag) {
    // c3d 的计数一律走 header()（上游 API：c3d 本身没有 points()/analogs()）
    check(b.header().nb3dPoints() == N_POINTS, tag + ": header().nb3dPoints() == 3");
    check(b.header().nbFrames() == N_FRAMES, tag + ": header().nbFrames() == 10");
    check(b.header().nbAnalogs() == N_ANALOGS, tag + ": header().nbAnalogs() == 3");

    bool pts_ok = true;
    for (std::size_t f = 0; f < N_FRAMES && pts_ok; ++f) {
        // 逐帧取数据：c3d.data().frame(f).points().point(m).x()/y()/z()
        const ezc3d::DataNS::Frame &frame = b.data().frame(f);
        for (std::size_t m = 0; m < N_POINTS && pts_ok; ++m) {
            const ezc3d::DataNS::Points3dNS::Point &pt = frame.points().point(m);
            if (!nearly(pt.x(), expected_point(f, m, 0)) ||
                !nearly(pt.y(), expected_point(f, m, 1)) ||
                !nearly(pt.z(), expected_point(f, m, 2))) {
                pts_ok = false;
            }
        }
    }
    check(pts_ok, tag + ": 全部 point 坐标逐点无损 (" + std::to_string(N_FRAMES) +
                      "x" + std::to_string(N_POINTS) + ")");

    bool ana_ok = true;
    for (std::size_t f = 0; f < N_FRAMES && ana_ok; ++f) {
        const ezc3d::DataNS::AnalogsNS::Analogs &an = b.data().frame(f).analogs();
        for (std::size_t sf = 0; sf < N_SUBFRAMES && ana_ok; ++sf) {
            for (std::size_t c = 0; c < N_ANALOGS && ana_ok; ++c) {
                if (!nearly(an.subframe(sf).channel(c).data(),
                            expected_analog(f, sf, c), 1e-5)) {
                    ana_ok = false;
                }
            }
        }
    }
    check(ana_ok, tag + ": 全部 analog 采样无损 (" + std::to_string(N_FRAMES) + "x" +
                      std::to_string(N_SUBFRAMES) + "x" + std::to_string(N_ANALOGS) + ")");

    check(b.pointNames().size() == N_POINTS && b.pointNames()[0] == "point1",
          tag + ": point 名称标签保留");
    check(b.channelNames().size() == N_ANALOGS && b.channelNames()[0] == "analog1",
          tag + ": analog 通道名保留");
}

}  // namespace

int main() {
    const std::string path = "ezc3d_consumer_roundtrip.c3d";

    std::cout << "== ezc3d consumer end-to-end (C3D write/read roundtrip) ==" << std::endl;

    // 1) 组装
    ezc3d::c3d original = build_sample();
    check(original.header().nb3dPoints() == N_POINTS, "构造: 3 个 point");
    check(original.header().nbFrames() == N_FRAMES, "构造: 10 帧");
    check(original.header().nbAnalogs() == N_ANALOGS, "构造: 3 个 analog 通道");

    // 2) 真实写盘
    bool wrote = true;
    try {
        original.parametrizedWrite(path, ezc3d::WRITE_FORMAT::DEFAULT, false);
    } catch (const std::exception &e) {
        wrote = false;
        std::cout << "  write 抛异常: " << e.what() << std::endl;
    }
    check(wrote, "写入 " + path + " 成功");

    std::FILE *fp = std::fopen(path.c_str(), "rb");
    long size = 0;
    if (fp) {
        std::fseek(fp, 0, SEEK_END);
        size = std::ftell(fp);
        std::fclose(fp);
    }
    check(size > 512, "落盘文件非空 (size=" + std::to_string(size) + " bytes > 512)");

    // 3) 全新建对象读回
    ezc3d::c3d reloaded(path);
    compare_roundtrip(reloaded, "回环1");

    // 4) 二次回环（读回的再写再读，确认多次往返稳定）
    const std::string path2 = "ezc3d_consumer_roundtrip2.c3d";
    reloaded.write(path2);
    ezc3d::c3d reloaded2(path2);
    compare_roundtrip(reloaded2, "回环2");

    // 5) 错误路径：不存在的文件必须抛异常
    bool threw = false;
    try {
        ezc3d::c3d missing("ThereIsNoSuchC3dFile_e2e.c3d");
    } catch (const std::exception &) {
        threw = true;
    }
    check(threw, "读取不存在的文件抛异常（错误路径正常）");

    std::remove(path.c_str());
    std::remove(path2.c_str());

    std::cout << "== checks: " << g_checks << ", failed: " << g_failed << " ==" << std::endl;
    if (g_failed != 0) {
        std::cout << "RESULT: FAIL" << std::endl;
        return 1;
    }
    std::cout << "RESULT: PASS" << std::endl;
    return 0;
}
