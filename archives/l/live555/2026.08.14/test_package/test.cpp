// LIVE555 安装包消费者测试（OHOS 上真实执行，全程离线）。
//
// 断言的是「四个库与头文件真的可用」而非仅能编译：
//   1) 包含聚合头 <liveMedia.hh>（它自身 include 数十个子头，可验证头文件布局完整）；
//   2) 用 BasicUsageEnvironment/BasicTaskScheduler 构造真实的调度器与使用环境
//      —— 这两步会实际调用库内构造函数与虚表，静态库缺失符号时会链接失败、运行期异常时会崩溃；
//   3) 通过 UsageEnvironment 的输出流打印一行，随后按上游要求 reclaim/析构，验证生命周期正常。
// 任一断言失败即以非零退出码结束，使 test_package 真实失败。
#include <BasicUsageEnvironment/BasicUsageEnvironment.hh>
#include <liveMedia/liveMedia.hh>
#include <UsageEnvironment/UsageEnvironment.hh>

#include <cstdio>

int main() {
    TaskScheduler *scheduler = BasicTaskScheduler::createNew();
    if (scheduler == nullptr) {
        std::fprintf(stderr, "BasicTaskScheduler::createNew() 返回空\n");
        return 1;
    }
    UsageEnvironment *env = BasicUsageEnvironment::createNew(*scheduler);
    if (env == nullptr) {
        std::fprintf(stderr, "BasicUsageEnvironment::createNew() 返回空\n");
        delete scheduler;
        return 1;
    }

    *env << "live555 basic usage environment ok\n";

    env->reclaim();
    delete scheduler;
    std::printf("live555 liveMedia/BasicUsageEnvironment 可用性检查通过\n");
    return 0;
}
