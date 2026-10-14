// R34 反空壳消费者测试：用被测包（AdaptiveCpp）的 acpp 驱动
// 真实编译并运行一个 SYCL 内核，验证异构编译链路可用。
//
// 校验点：
//   1. SYCL 头文件与运行时可用（包含与链接）；
//   2. 内核在 CPU（OpenMP）后端上真实执行；
//   3. 计算结果正确（不是只打印字符串）。
#include <sycl/sycl.hpp>

#include <cstdio>
#include <vector>

int main() {
  constexpr std::size_t n = 256;
  std::vector<int> host(n, 0);

  {
    sycl::queue q{sycl::default_selector_v};
    std::printf("device: %s\n",
                q.get_device().get_info<sycl::info::device::name>().c_str());

    int* dev = sycl::malloc_device<int>(n, q);
    q.submit([&](sycl::handler& h) {
      h.parallel_for(sycl::range<1>{n}, [=](sycl::id<1> i) {
        dev[i] = static_cast<int>(i.get(0)) * 2;
      });
    }).wait();
    // 显式等待内核完成后再拷回：omp 后端对内核与 memcpy 使用不同的提交
    // 队列且 flush 是异步的，在 OHOS 上实测 memcpy 可能早于内核执行，
    // 因此这里不依赖 inorder 语义，显式同步。
    q.memcpy(host.data(), dev, n * sizeof(int)).wait();
    sycl::free(dev, q);
  }

  // 真实断言：逐元素校验内核结果
  for (std::size_t i = 0; i < n; ++i) {
    if (host[i] != static_cast<int>(i) * 2) {
      std::printf("FAIL at %zu: got %d, expect %d\n", i, host[i],
                  static_cast<int>(i) * 2);
      return 1;
    }
  }
  std::printf("OK: %zu elements verified\n", n);
  return 0;
}
