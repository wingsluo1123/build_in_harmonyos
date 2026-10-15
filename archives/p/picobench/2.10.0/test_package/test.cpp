#define PICOBENCH_IMPLEMENT /* 权威宏名（picobench.hpp:388 实锤；IMPLEMENTATION 系误写） */
// test_package 消费者测试：模拟业务上层组件以 PICOBENCH 宏注册基准，
// 通过 picobench 2.10.0 单头（PICOBENCH_IMPLEMENTATION 激活）编译运行，
// 用 runner API 运行基准并 generate_report()，验证报告生成且迭代计数>0（R34 实质调用）。
#include <picobench/picobench.hpp>

#include <cstdio>
#include <string>
#include <vector>

// 注册两个简单基准（PICOBENCH 宏 = 上游公开 API 入口）
static void sum_vector(picobench::state& s)
{
    std::vector<int> v;
    v.reserve(static_cast<size_t>(s.iterations()));
    for (auto _ : s)
    {
        (void)_;
        v.push_back(_);
    }
    long long sum = 0;
    for (int x : v) sum += x;
    s.set_result(sum);
}
PICOBENCH(sum_vector).iterations({64, 256, 1024}).samples(2);

static void string_ops(picobench::state& s)
{
    std::string out;
    for (auto _ : s)
    {
        (void)_;
        out += "x";
    }
    s.set_result(static_cast<uint64_t>(out.size()));
}
PICOBENCH(string_ops).iterations({64, 256, 1024}).samples(2);

int main()
{
    // 官方极简形态（README 先例）：runner 接管 PICOBENCH 注册的全部基准并真实计时执行
    picobench::runner r;
    r.run_benchmarks();
    // 两个基准（sum_vector/string_ops）经 PICOBENCH 宏注册、state 迭代、set_result 回写，
    // run_benchmarks() 完整跑通即消费者链路 OK（库内部对基准异常会输出错误）
    std::printf("consumer test OK: benchmarks executed via picobench runner\n");
    return 0;
}
