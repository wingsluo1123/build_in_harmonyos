/*
 * samarium 1.0.0 消费者用例（真实消费者：只 include 交付的头、只链接交付的 libsamarium.so）
 *
 * 判据全部来自**外部可核对真值**，不使用库自身作为 oracle：
 *   · 解析力学解：自由落体 y = y0 + v0·t − ½·g·t²、抛体射程 R = v²·sin2θ/g、
 *     最大高度 h = v0²·sin²θ/(2g)、弹性碰撞（等质量正碰交换速度）与胡克定律 F = k·x；
 *   · 显式欧拉積分的**离散闭式解**（代数恒等式，非库内实现）；
 *   · 平面几何恒等式（勾股、圆面积 πr²、矩形面积、线段交点）；
 *   · 均匀分布的性质（值域 [0,1]、期望 0.5）；
 *   · 滑动窗口不变量（Trail 容量上界 + 保留最近 N 点）。
 *
 * 每一步长/容差的来源都写在注释里；编译与链接真实依赖被测包（CI 的 L1e 会把
 * lib/、include/ 移走后重跑本用例，届时必须编译失败）。
 */
#include <cmath>
#include <cstdio>
#include <numbers>
#include <vector>

#include "samarium/samarium.hpp"

namespace
{
int g_checks   = 0;
int g_failures = 0;

void check(bool cond, const char* label)
{
    ++g_checks;
    if (cond) { std::printf("[ok]   %s\n", label); }
    else
    {
        ++g_failures;
        std::printf("[FAIL] %s\n", label);
    }
}

void check_close(double value, double expected, double tolerance, const char* label)
{
    ++g_checks;
    const auto diff = std::abs(value - expected);
    if (diff <= tolerance)
    {
        std::printf("[ok]   %s (实测 %.12g / 期望 %.12g / 容差 %.3g)\n", label, value, expected,
                    tolerance);
    }
    else
    {
        ++g_failures;
        std::printf("[FAIL] %s (实测 %.12g / 期望 %.12g / 差 %.3g > 容差 %.3g)\n", label, value,
                    expected, diff, tolerance);
    }
}

// 显式欧拉（Particle::update = {v += a·dt; x += v·dt}）在恒定加速度下的离散闭式解：
//   y_N = y0 + v0·t + ½·g·t·(t + dt)，其中 t = N·dt
auto euler_constant_accel(double y0, double v0, double g, double t, double dt) -> double
{
    return y0 + v0 * t + 0.5 * g * t * (t + dt);
}
} // namespace

int main()
{
    using namespace sm::literals;

    std::printf("== samarium 1.0.0 消费者用例 ==\n");

    // ── 1. 平面几何 / 向量（解析真值）──────────────────────────────────────
    check(sm::Vector2{3.0, 4.0}.length() == 5.0, "Vector2{3,4}.length() == 5（勾股）");
    check(sm::Vector2{3.0, 4.0}.length_sq() == 25.0, "Vector2{3,4}.length_sq() == 25");
    check_close(sm::Vector2{1.0, 1.0}.angle(), std::numbers::pi / 4.0, 1e-15,
                "Vector2{1,1}.angle() == π/4");
    check_close(sm::Vector2{3.0, 4.0}.angle(), std::atan2(4.0, 3.0), 1e-15,
                "Vector2{3,4}.angle() == libm atan2(4,3)");
    check(1.0_x == sm::Vector2{1.0, 0.0} && 1.0_y == sm::Vector2{0.0, 1.0},
          "字面量 1.0_x / 1.0_y 分别等于单位 x / y 向量");
    check(sm::Vector2::dot({1.0, 2.0}, {3.0, 4.0}) == 11.0,
          "Vector2::dot({1,2},{3,4}) == 11（点积定义）");
    check_close(sm::Vector2{3.0, 4.0}.normalized().length(), 1.0, 1e-15,
                "单位化后长度 == 1");

    check_close(sm::math::area(sm::Circle{.radius = 12.0}), std::numbers::pi * 144.0, 1e-9,
                "area(Circle{12}) == 144π = 452.3893421169302");
    check(sm::math::area(sm::BoundingBox<double>{{-10.0, -11.0}, {12.0, 13.0}}) == 528.0,
          "area(BoundingBox{(-10,-11),(12,13)}) == 22*24 = 528");
    const auto cross = sm::math::intersection({{-1.0, 0.0}, {1.0, 0.0}}, {{0.0, 1.0}, {0.0, -1.0}});
    check(cross.has_value() && *cross == sm::Vector2{} && cross->x == 0.0 && cross->y == 0.0,
          "两线段交点为 (0,0)（坐标轴交叉）");
    const auto miss = sm::math::clamped_intersection({{-1.0, -1.0}, {-0.5, -0.5}},
                                                     {{1.0, -1.0}, {0.5, -0.5}});
    check(!miss.has_value(), "首尾不相接的两线段无交点（clamped_intersection == nullopt）");
    check_close(sm::math::to_degrees(sm::math::pi), 180.0, 1e-12, "to_degrees(π) == 180");
    check(sm::math::almost_equal(1.0, 1.0 + 5e-5) && !sm::math::almost_equal(1.0, 1.1),
          "almost_equal 阈值语义（默认 ε=1e-4）");
    check(bool(sm::concepts::Integral<sm::u64>) && bool(sm::concepts::Number<sm::f64>),
          "core/concepts 约束成立（Integral<u64> / Number<f64>）");

    // ── 2. 自由落体：显式欧拉 vs 解析解与离散闭式解 ────────────────────────
    constexpr auto gravity = -9.81;       // m/s²（向下为正号的相反数）
    constexpr auto v0_y    = 100.0;       // m/s（竖直向上）
    constexpr auto dt_a    = 1.0 / 512.0; // 步长 1/512 s
    constexpr int steps_a  = 1536;        // 3.0 s
    constexpr auto t_a     = steps_a * dt_a;

    auto free_fall = sm::ParticleSystem{1UL, sm::Particle{{0.0, 0.0}, {0.0, v0_y}, {}, 1.0, 1.0}};
    for (auto i = 0; i < steps_a; ++i)
    {
        free_fall.apply_force({0.0, gravity});
        free_fall.update(dt_a);
    }
    const auto y_sim = free_fall.particles[0].pos.y;
    check_close(y_sim, euler_constant_accel(0.0, v0_y, gravity, t_a, dt_a), 1e-9,
                "自由落体 3 s（dt=1/512）：与显式欧拉离散闭式解一致（容差 1e-9，远大于 1536 步累积舍入 ~1e-12）");
    check_close(y_sim, v0_y * t_a + 0.5 * gravity * t_a * t_a,
                0.5 * std::abs(gravity) * t_a * dt_a + 1e-9,
                "自由落体 3 s：与解析解 y=y0+v0t−½gt² 之差 ≤ ½·|g|·t·dt = 0.02874 m（一阶离散化误差上界）");
    check_close(free_fall.particles[0].vel.y, v0_y + gravity * t_a, 1e-9,
                "自由落体末速度 = v0 + g·t = 70.57 m/s");
    check(free_fall.particles[0].pos.x == 0.0, "无水平力时 x 逐位保持 0（无伪侧向漂移）");

    // ── 3. 抛体运动：射程 / 最大高度 / 飞行时间 ────────────────────────────
    constexpr auto speed = 50.0;                     // m/s
    constexpr auto theta = std::numbers::pi / 4.0;   // 45°
    constexpr auto dt_b  = 1.0 / 1024.0;
    const auto vx        = speed * std::cos(theta);
    const auto vy        = speed * std::sin(theta);

    auto projectile = sm::ParticleSystem{1UL, sm::Particle{{0.0, 0.0}, {vx, vy}, {}, 1.0, 1.0}};
    auto peak_y     = 0.0;
    auto landing_x  = 0.0;
    auto landing_i  = 0;
    for (auto i = 0; i < 40000; ++i)
    {
        projectile.apply_force({0.0, gravity});
        projectile.update(dt_b);
        peak_y = std::max(peak_y, projectile.particles[0].pos.y);
        if (projectile.particles[0].pos.y <= 0.0)
        {
            landing_x = projectile.particles[0].pos.x;
            landing_i = i + 1;
            break;
        }
    }
    const auto t_flight      = 2.0 * vy / std::abs(gravity);                      // 解析飞行时间
    const auto range_analytic = speed * speed * std::sin(2.0 * theta) / std::abs(gravity);
    const auto peak_analytic  = vy * vy / (2.0 * std::abs(gravity));
    const auto step_x         = vx * dt_b;                                        // 一个积分步的水平位移

    check_close(landing_x, vx * (t_flight - dt_b), step_x + 1e-6,
                "抛体落点 == v·cosθ·(T−dt)（离散落点，整数步量化 ≤ 一个步长 0.0345 m）");
    check_close(landing_x, range_analytic, 2.0 * step_x + 1e-6,
                "抛体射程 == v²·sin2θ/g = 254.842 m（差 ≤ 两步水平位移，相对误差 < 0.03%）");
    // 显式欧拉的离散顶点：顶点被下移一阶离散化项 v·sinθ·dt/2，且顶点可能不落在整数步上
    // （再低最多 ½·|g|·(dt/2)² = 1.2e-6）——两处都写进容差，不做"解析解即离散解"的错假设
    const auto peak_euler =
        peak_analytic - vy * dt_b / 2.0 + std::abs(gravity) * dt_b * dt_b / 8.0;
    check_close(peak_y, peak_euler, 1e-5,
                "抛体最大高度 == 解析顶点 v²sin²θ/(2g) 减去一阶离散化项 v·sinθ·dt/2 = 0.01726 m");
    check_close(peak_y, peak_analytic, vy * dt_b / 2.0 + 1e-5,
                "抛体最大高度与解析式 63.7105 m 之差 ≤ 一阶离散化上界 v·sinθ·dt/2 = 0.0173 m");
    check_close(landing_i * dt_b, t_flight, 2.0 * dt_b,
                "飞行时间 == 2v·sinθ/g = 7.208 s（差 ≤ 两个步长）");

    // ── 4. 碰撞：非重叠不变量 / 等质量正碰交换速度（动量与动能守恒）────────
    sm::Particle pa{{-0.5, 0.0}, {1.0, 0.0}, {}, 1.0, 1.0};
    sm::Particle pb{{0.5, 0.0}, {-1.0, 0.0}, {}, 1.0, 1.0};
    const auto hit = sm::phys::did_collide(pa, pb);   // 圆心距 1.0 ≤ r1+r2 = 2.0
    check(hit.has_value() && hit->x == 0.0 && hit->y == 0.0,
          "did_collide：重叠圆的碰撞点 = 两圆心中点 (0,0)");
    sm::phys::collide(pa, pb, 1.0);
    check_close(sm::math::distance(pa.pos, pb.pos), pa.radius + pb.radius, 1e-12,
                "碰撞后圆心距 == r1+r2 == 2.0（非重叠不变量）");
    check(pa.vel == sm::Vector2{-1.0, 0.0} && pb.vel == sm::Vector2{1.0, 0.0},
          "等质量正碰交换速度（弹性碰撞 + 动量守恒的解析结论）");
    check(pa.vel.x * pa.mass + pb.vel.x * pb.mass == 0.0 && pa.vel.x * pa.vel.x == pb.vel.x * pb.vel.x,
          "碰撞后总动量 0、动能相等（一维弹性碰撞守恒律）");

    sm::Particle pc{{0.0, 0.0}, {2.0, 0.0}, {}, 1.0, 1.0};
    sm::Particle pd{{3.0, 0.0}, {-2.0, 0.0}, {}, 1.0, 1.0};   // 圆心距 3.0 > 2.0
    check(!sm::phys::did_collide(pc, pd).has_value(), "did_collide：圆心距 3.0 > r1+r2 = 2.0 判无碰撞");
    sm::phys::collide(pc, pd, 1.0);
    check(pc.pos == sm::Vector2{0.0, 0.0} && pc.vel == sm::Vector2{2.0, 0.0} &&
              pd.vel == sm::Vector2{-2.0, 0.0},
          "无碰撞时不产生伪冲量（位置与速度逐位不变）");

    // ── 5. 弹簧：胡克定律 F = k·x 与反作用力 ───────────────────────────────
    sm::Particle s1{{0.0, 0.0}, {}, {}, 1.0, 1.0};
    sm::Particle s2{{4.0, 0.0}, {}, {}, 1.0, 1.0};
    sm::Spring  spring{s1, s2, 50.0, 10.0};     // 自然长度取构造时圆心距 = 4，k = 50
    check(spring.rest_length == 4.0 && spring.length() == 4.0,
          "Spring 自然长度 == 构造时两质点距离 4.0");
    spring.update();
    check(s1.acc == sm::Vector2{0.0, 0.0} && s2.acc == sm::Vector2{0.0, 0.0},
          "处于自然长度时弹簧力为 0（F = k·x，x = 0）");
    s2.pos = {5.0, 0.0};                        // 拉伸 x = 1（速度均为 0 ⇒ 阻尼项为 0）
    spring.update();
    check(s1.acc == sm::Vector2{50.0, 0.0} && s2.acc == sm::Vector2{-50.0, 0.0},
          "拉伸 1 m 时 a = k·x/m = 50 m/s²，且两质点受力大小相等方向相反（牛顿第三定律）");
    s1.update(0.001);
    s1.acc = {};
    check_close(s1.vel.x, 50.0 * 0.001, 1e-12, "弹簧质点沿轴向加速（v = a·dt = 0.05 m/s）");

    // ── 6. Trail：滑动窗口不变量 ──────────────────────────────────────────
    sm::Trail trail{3UL};
    for (auto i = 0; i < 5; ++i) { trail.push_back({static_cast<double>(i), 0.0}); }
    check(trail.size() == 3UL, "Trail{3} 推入 5 个点后长度恒为 3（容量上界）");
    check(trail[0].x == 2.0 && trail[1].x == 3.0 && trail[2].x == 4.0,
          "Trail 保留最近 3 个点 [2,3,4]（滑动窗口语义）");
    check(trail.span().size() == 3UL, "Trail::span() 视图长度 == 轨迹长度");

    // ── 7. RandomGenerator：值域 / 均匀性 / 可复现 ────────────────────────
    sm::RandomGenerator rng{4096UL};            // Stable 模式，固定种子 69
    auto min_value = 1.0;
    auto max_value = 0.0;
    auto sum       = 0.0;
    constexpr int samples = 20000;
    for (auto i = 0; i < samples; ++i)
    {
        const auto value = rng.random();
        min_value = std::min(min_value, value);
        max_value = std::max(max_value, value);
        sum += value;
    }
    check(min_value >= 0.0 && max_value <= 1.0, "随机数落在 [0,1]（PCG 输出 / UINT32_MAX）");
    check_close(sum / samples, 0.5, 0.02, "20000 个样本的均值 ≈ 0.5（均匀分布期望，容差 0.02）");

    sm::RandomGenerator rng_a{64UL};
    sm::RandomGenerator rng_b{64UL};
    auto reproducible = true;
    for (auto i = 0; i < 64; ++i) { reproducible = reproducible && (rng_a.random() == rng_b.random()); }
    check(reproducible, "同种子（Stable 模式）产生逐位相同的序列");

    std::printf("消费者用例结果：%d 项检查，%d 项失败\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
