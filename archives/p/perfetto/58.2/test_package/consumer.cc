// perfetto 58.2 消费者示例：编译并链接 libperfetto，验证公共头与库在 OHOS 上可用。
//
// 说明：libperfetto.so 以 -fvisibility=hidden 构建，对外导出面是 entrypoint
// （`perfetto::ServiceMain` / `perfetto::ProbesMain`，即 traced / traced_probes 的薄封装）。
// 这里在运行期通过动态链接器解析这两个导出符号，真实验证「头文件可编译 + 符号可链接
// 且确由 libperfetto 提供 + 程序可运行」，而不真正启动服务。
#include <cstdio>
#include <cstring>

#include <dlfcn.h>

#include <perfetto/base/build_config.h>
#include <perfetto/ext/traced/traced.h>

namespace {

// 运行期真实断言：符号必须由 libperfetto 这一动态库提供（若链接到了错误目标或
// 静态 stub，dladdr() 会失败，或返回的 dli_fname 不含 "perfetto"）。
bool ResolvesToLibperfetto(int (*fn)(int, char**), const char* symbol) {
  Dl_info info{};
  if (fn == nullptr || dladdr(reinterpret_cast<void*>(fn), &info) == 0 ||
      info.dli_fname == nullptr || std::strstr(info.dli_fname, "perfetto") == nullptr) {
    std::fprintf(stderr, "consumer: %s did not resolve to libperfetto\n", symbol);
    return false;
  }
  std::printf("consumer: %s resolved from %s\n", symbol, info.dli_fname);
  return true;
}

}  // namespace

int main() {
  const bool service_ok = ResolvesToLibperfetto(&perfetto::ServiceMain,
                                                "perfetto::ServiceMain");
  const bool probes_ok = ResolvesToLibperfetto(&perfetto::ProbesMain,
                                               "perfetto::ProbesMain");
  if (!service_ok || !probes_ok)
    return 1;

#if PERFETTO_BUILDFLAG(PERFETTO_OS_LINUX)
  std::printf("consumer: build config OS_LINUX ok\n");
  return 0;
#else
  // OHOS 映射到 perfetto 的 linux 家族；其它取值意味着打包/头路径错误。
  std::fprintf(stderr, "consumer: expected PERFETTO_OS_LINUX build config\n");
  return 1;
#endif
}
