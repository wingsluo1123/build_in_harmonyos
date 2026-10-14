//
// HarmonyOS 专项测试 — pytorch 2.13.0 (libtorch C++ API)
//
// R8: 不使用任何 `#if defined(<平台宏>)` 平台条件编译。宿主平台改为**运行时**
// 判定（uname(2) 的 sysname）；只有在 HarmonyOS 上才执行鸿蒙适配点校验，其它
// 平台打印 SKIP 并以 0 退出，因此同一测试目标在任何平台构建/运行都成立。
//
// 覆盖的 OHOS / musl aarch64 适配点：
//   1) 平台身份：宿主为 HarmonyOS 且机器为 aarch64，libtorch 的 CPU 后端可用；
//   2) 补丁 0004 语义：c10/util/Enumerate.h 在 musl 下显式引入 sys/types.h，
//      使 ssize_t 可见（上游非 Windows 分支原本不引入，musl 不传递提供）；
//   3) 补丁 0001 领域：std::ranges::any_of 降级为 <algorithm> 迭代器版本，
//      覆盖 group_norm 的空张量判定与形状保持；
//   4) musl/OHOS 运行时：复数标量（complex64）与 CPU 张量算术、int64 归约、
//      STL 容器互操作；
//   5) 分布式 c10d：gloo 后端 / TCPStore / libuv / TensorPipe 的关键符号在
//      产物内可运行时解析（补丁 0008-0011 的直接回归判据），并用 c10d 的
//      FileStore 做一次真实的 set/get/add/deleteKey 往返；
//   6) BLAS/LAPACK：linalg_solve 与 linalg_svd 的数值正确性（Eigen 回退无论
//      如何也提供不了 LAPACK），以及走 CBLAS 的复数 dot；
//   7) ATen 线程池：线程数可设置、parallel_for 覆盖每个下标恰好一次（并行能力
//      未退化）；2.13.0.1 起 USE_OPENMP=ON，同时校验 OpenMP 运行时确实可用。
//   8) 后端启用（2.13.0.1）：FBGEMM / QNNPACK / XNNPACK / NNPACK / Kineto 的
//      可用性查询与数值正确性；oneDNN 与 ITT 均已编译进来，其中 oneDNN 的
//      aarch64 内核是运行时 JIT，故用「进程能否获得可执行内存」的运行时门控
//      （补丁 0017）决定是否派发，这里断言该门控的恒等式与一致性。
//
// 诊断：可选 argv[1] 覆盖检测到的 sysname（例如 `./test_pytorch_ohos Linux`），
// 用于在 OHOS 上验证非 OHOS 平台的跳过路径。
//
#include <torch/torch.h>
#include <torch/csrc/distributed/c10d/FileStore.hpp>

#include <ATen/Context.h>
#include <ATen/ops/_nnpack_available.h>
#include <c10/core/QEngine.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <mutex>
#include <set>
#include <string>
#include <sys/utsname.h>
#include <thread>
#include <tuple>
#include <unistd.h>
#include <utility>
#include <vector>

namespace {

struct Platform {
    std::string sysname;
    std::string machine;
};

Platform detect_platform() {
    Platform p{"unknown", "unknown"};
    struct utsname u;
    if (::uname(&u) == 0) {
        p.sysname = u.sysname;
        p.machine = u.machine;
    }
    return p;
}

std::string to_lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });
    return s;
}

// 运行时判据：OHOS 的 uname(2) 报 "HarmonyOS" / "OpenHarmony" / "OHOS"。
bool is_harmonyos(const std::string& sysname) {
    const std::string s = to_lower(sysname);
    return s.find("harmonyos") != std::string::npos ||
           s.find("openharmony") != std::string::npos ||
           s.find("ohos") != std::string::npos;
}

int g_failures = 0;

void check(bool ok, const char* what) {
    std::printf("  [%s] %s\n", ok ? "PASS" : "FAIL", what);
    if (!ok) {
        ++g_failures;
    }
}

// 1) 平台身份（运行时判定，无平台宏） --------------------------------------
void test_platform_identity(const Platform& plat) {
    std::printf("[1] 平台身份\n");
    check(is_harmonyos(plat.sysname), "host reports HarmonyOS/OHOS via uname(2)");
    check(plat.machine == "aarch64" || plat.machine == "arm64",
          "host machine is aarch64/arm64");
    check(sizeof(void*) == 8, "target is 64-bit");
    check(at::Device(at::kCPU).is_cpu(), "at::Device(kCPU) resolves to the CPU backend");
    check(at::get_default_dtype() == at::kFloat, "default dtype is float32");
    check(at::get_num_threads() > 0, "torch thread pool is initialised");
}

// 2) 补丁 0004 语义：musl 下 ssize_t 可见 ----------------------------------
void test_musl_ssize_t() {
    std::printf("[2] musl ssize_t 可见性（补丁 0004）\n");
    // ssize_t 由 <sys/types.h> 显式提供（补丁内容）；若头文件未引入则本 TU
    // 无法编译，构成实质性校验。
    ssize_t s = -1;
    unsigned long long max = static_cast<unsigned long long>(s);
    check(s == -1, "ssize_t is signed and usable under OHOS/musl");
    check(max > 0, "ssize_t round-trips through unsigned conversion");
    check(sizeof(ssize_t) == sizeof(void*), "ssize_t width matches pointer width");
    check(sizeof(std::int64_t) == 8, "int64_t is 8 bytes on OHOS aarch64");
}

// 3) 补丁 0001 领域：group_norm 的迭代器化实现 -----------------------------
void test_group_norm_algorithm_path() {
    std::printf("[3] group_norm 路径（补丁 0001，ranges→iterator）\n");
    const int64_t N = 2, C = 4, H = 3, W = 3;
    auto x = torch::arange(static_cast<float>(N * C * H * W)).reshape({N, C, H, W});
    // 上游 group_norm 的空张量判定在 OHOS 上走迭代器版本；这里用同一谓词
    // 校验维度扫描逻辑（std::any_of 迭代器版）在 OHOS 工具链下行为正确。
    auto sizes = x.sizes();
    const bool has_zero = std::any_of(sizes.begin(), sizes.end(),
                                      [](int64_t s) { return s == 0; });
    check(!has_zero, "std::any_of over sizes() detects no empty dims");

    auto y = torch::group_norm(x, /*num_groups=*/2);
    check(y.sizes() == x.sizes(), "group_norm preserves shape");
    check(y.defined() && y.numel() == x.numel(), "group_norm produced full output");
    check(torch::isfinite(y).all().item<bool>(), "group_norm output is finite");

    auto empty = torch::empty({0, C, H, W});
    auto empty_sizes = empty.sizes();
    const bool empty_has_zero = std::any_of(empty_sizes.begin(), empty_sizes.end(),
                                            [](int64_t s) { return s == 0; });
    check(empty_has_zero, "empty input detected by the same predicate");
}

// 4) OHOS aarch64 上的 musl/libc++ 算术与复数 -------------------------------
void test_ohos_numeric_paths() {
    std::printf("[4] OHOS aarch64 算术与复数\n");
    auto a = torch::tensor({1.0f, 2.0f, 3.0f, 4.0f});
    auto b = torch::tensor({4.0f, 3.0f, 2.0f, 1.0f});
    auto c = a * b + a;  // 5, 8, 9, 8 -> 30
    check(std::abs(c.sum().item<double>() - 30.0) < 1e-6,
          "arithmetic on aarch64 CPU tensors");

    // 复数标量路径（musl libc++ 下的 complex 运算）
    auto z = at::tensor({c10::complex<float>(1.0f, 2.0f), c10::complex<float>(3.0f, -1.0f)},
                        at::dtype(at::kComplexFloat));
    check(z.scalar_type() == at::kComplexFloat, "complex64 tensor constructed");
    auto z0 = (z[0] * z[0]).item<c10::complex<float>>();
    check(std::abs(z0.real() - (-3.0f)) < 1e-5 && std::abs(z0.imag() - 4.0f) < 1e-5,
          "complex64 multiply matches (1+2i)^2 = -3+4i");

    // 整数归约（sizes/索引路径在 musl 下使用 ssize_t）
    auto iv = torch::arange(0, 100, torch::kInt64);
    check(iv.sum().item<int64_t>() == 4950, "int64 arange+sum uses ssize_t-safe indexing");

    // STL 容器与 torch 交互（libc++ ABI 组合）
    std::vector<float> host{1.0f, 2.0f, 3.0f};
    auto t = torch::from_blob(host.data(), {3}, torch::kFloat).clone();
    check(t.sum().item<float>() == 6.0f, "std::vector -> tensor interop");
}

// 5) 分布式 c10d（补丁 0008-0011 的回归判据） ------------------------------
// 生产代码是否把 gloo/TCPStore/libuv/TensorPipe 真正编入并导出：
// gloo 的 CMakeLists 用 `STREQUAL "Linux"` 门控 TCP transport 与源码，libuv 同样
// 按 Linux 门控，命中时这些对象被静默排除，产物即带未解析的 uv__*（加载期
// Error relocating）或缺少 gloo 设备工厂符号。这里用 dlsym 在**运行时**核对
// 关键符号存在，并用 FileStore 跑一次真实的键值往返（FileStore 是 c10d 唯一
// 不依赖 gloo 头的公共 Store 实现）。
void test_distributed_c10d() {
    std::printf("[5] 分布式 c10d / gloo / libuv / TensorPipe\n");

    // libuv：补丁 0009 放行的 linux.c/proctitle.c 提供，若被门控排除则
    // libtorch_cpu.so 会带未解析的 uv__* 而无法加载。
    const char* uv_syms[] = {
        "uv_default_loop", "uv_run", "uv_loop_init", "uv_loop_close",
        "uv_loop_alive", "uv_tcp_init", "uv_handle_size",
    };
    int uv_ok = 0;
    for (const char* s : uv_syms) {
        if (::dlsym(RTLD_DEFAULT, s) != nullptr) {
            ++uv_ok;
        } else {
            std::printf("      missing libuv symbol: %s\n", s);
        }
    }
    check(uv_ok == 7, "all 7 libuv symbols resolve from the loaded libtorch (patch 0009)");

    // gloo：vtable/typeinfo 为数据符号，名字不受 libc++ 内联命名空间影响。
    check(::dlsym(RTLD_DEFAULT, "_ZTVN4c10d16ProcessGroupGlooE") != nullptr,
          "c10d::ProcessGroupGloo vtable is present (patch 0008/0011)");
    check(::dlsym(RTLD_DEFAULT, "_ZTVN4gloo10rendezvous11PrefixStoreE") != nullptr,
          "gloo rendezvous (PrefixStore) is linked in");
    check(::dlsym(RTLD_DEFAULT, "_ZTVN4gloo10rendezvous7ContextE") != nullptr,
          "gloo rendezvous Context is linked in");
    check(::dlsym(RTLD_DEFAULT, "_ZTVN4gloo9transport3tcp11DeferrablesE") != nullptr,
          "gloo TCP transport is linked in (the transport the Linux gating dropped)");
    check(::dlsym(RTLD_DEFAULT, "_ZTVN4c10d8TCPStoreE") != nullptr,
          "c10d::TCPStore was compiled in");

    // TensorPipe：USE_TENSORPIPE=ON 时的进程间后端。
    check(::dlsym(RTLD_DEFAULT, "_ZTVN10tensorpipe11ContextImplE") != nullptr,
          "tensorpipe::ContextImpl vtable is present (USE_TENSORPIPE)");

    // 真实的 c10d Store 往返：FileStore 是公共头（不依赖未安装的 gloo 头）。
    // 路径必须落在可写目录：HarmonyOS 的 /tmp 只读，故优先 TEST_TMPDIR/TMPDIR。
    const char* tmp = std::getenv("TEST_TMPDIR");
    if (tmp == nullptr) {
        tmp = std::getenv("TMPDIR");
    }
    if (tmp == nullptr) {
        tmp = ".";
    }
    const std::string path = std::string(tmp) + "/pytorch_ohos_c10d_store_"
                             + std::to_string(static_cast<long long>(::getpid()));
    bool roundtrip = false;
    std::string note = "ok";
    try {
        c10d::FileStore store(path, /*numWorkers=*/1);
        // 用 vector<uint8_t> 形式：FileStore 的 override 会隐藏基类的
        // set(string, string) 便捷重载（C++ 名字隐藏），此处直接走虚接口。
        const std::vector<uint8_t> value{'v'};
        store.set("k", value);
        const bool got_ok = (store.get_to_str("k") == "v");
        const int64_t after_add = store.add("counter", 41);
        store.add("counter", 1);
        const int64_t final_value = store.add("counter", 0);  // read back
        const bool deleted = store.deleteKey("k");
        const bool gone = !store.check({"k"});
        roundtrip = got_ok && after_add == 41 && final_value == 42 && deleted && gone;
        if (!roundtrip) {
            note = "set/get/add/deleteKey mismatch";
        }
    } catch (const std::exception& e) {
        note = std::string("exception: ") + e.what();
    }
    if (!roundtrip) {
        std::printf("      FileStore roundtrip: %s\n", note.c_str());
    }
    check(roundtrip, "c10d::FileStore set/get/add/deleteKey roundtrip");
    ::unlink(path.c_str());
}

// 6) BLAS/LAPACK：只有外部 LAPACK 才提供这些路径 ---------------------------
// 本包用 openblas/0.3.34（requires + -DBLAS=OpenBLAS）。没有 LAPACK 时
// linalg_solve 不可用，linalg_svd 只能走上游的慢速回退——数值正确性与
// 使用 CBLAS 的复数 dot 一起构成 BLAS 接线的功能判据。
void test_blas_lapack_paths() {
    std::printf("[6] BLAS/LAPACK 路径\n");

    // 与 Python 侧同一用例：(3x+1y=9, 1x+2y=8) 的解。
    auto A = torch::tensor({{3.0, 1.0}, {1.0, 2.0}});
    auto b = torch::tensor({9.0, 8.0});
    auto x = torch::linalg_solve(A, b);
    auto residual = torch::matmul(A, x) - b;
    check(residual.abs().max().item<double>() < 1e-6,
          "linalg_solve residual is zero (LAPACK linked)");
    check(std::abs(x[0].item<double>() - 2.0) < 1e-6 &&
              std::abs(x[1].item<double>() - 3.0) < 1e-6,
          "linalg_solve solution is (2, 3)");

    // SVD：A^T A 的奇异值 = 特征值平方根，可独立复算（不信任同一代码路径）。
    // both 走 float32（默认 dtype），LAPACK 的数值精度在 1e-5 量级；实测
    // 最大差 1.9e-6，故容差取 1e-5 而非 1e-6。
    auto M = torch::tensor({{1.0, 2.0}, {3.0, 4.0}, {5.0, 6.0}});
    auto svd = torch::linalg_svd(M, /*full_matrices=*/false);
    auto S = std::get<1>(svd);
    auto gram = torch::matmul(M.t(), M);
    auto eig = torch::linalg_eigvalsh(gram);
    auto expect = eig.clamp_min(0).sqrt();
    auto got = S.to(torch::kDouble);
    const bool svals_ok = std::abs(got[0].item<double>() - expect[1].item<double>()) < 1e-5 &&
                          std::abs(got[1].item<double>() - expect[0].item<double>()) < 1e-5;
    check(svals_ok, "linalg_svd singular values match sqrt(eigvals(A^T A))");

    // 复数 dot（AT_BLAS_USE_CBLAS_DOT）：与标量乘积独立复算。用本文件前面
    // 已验证过的 at::tensor + c10::complex 写法构造 complex64。
    auto z = at::tensor({c10::complex<float>(1.0f, 2.0f), c10::complex<float>(3.0f, 4.0f)},
                        at::dtype(at::kComplexFloat));
    auto w = at::tensor({c10::complex<float>(5.0f, -1.0f), c10::complex<float>(2.0f, 3.0f)},
                        at::dtype(at::kComplexFloat));
    const c10::complex<float> product =
        c10::complex<float>(1.0f, 2.0f) * c10::complex<float>(5.0f, -1.0f) +
        c10::complex<float>(3.0f, 4.0f) * c10::complex<float>(2.0f, 3.0f);
    const c10::complex<float> got_dot = torch::dot(z, w).item<c10::complex<float>>();
    check(std::abs(got_dot.real() - product.real()) < 1e-5f &&
              std::abs(got_dot.imag() - product.imag()) < 1e-5f,
          "complex64 dot matches the scalar product (CBLAS path)");
}

// 7) ATen 线程池（USE_OPENMP=OFF → ATEN_THREADING=NATIVE） ------------------
// OpenMP 在本工具链上不可用是有记录的设计取舍；这一组确认取舍没有拿掉并行
// 能力本身：parallel_for 覆盖每个下标恰好一次，且真正跨多个线程执行。
//
// 注意：NATIVE 后端**不允许在并行工作开始后再改** intra-op 线程数
// （ParallelNative.cpp 会告警并忽略），故这里不调用 set_num_threads()，
// 改为直接观测“多个线程各自拿到互不重叠的下标区间”这一实质并行证据。
void test_thread_pool() {
    std::printf("[7] ATen 线程池（NATIVE 后端）\n");

    const int workers = at::get_num_threads();
    check(workers >= 1, "at::get_num_threads() reports a positive worker count");

    constexpr int64_t kN = 10000;
    std::vector<std::atomic<int>> hits(kN);
    for (auto& h : hits) {
        h.store(0, std::memory_order_relaxed);
    }
    std::mutex id_mutex;
    std::set<std::thread::id> thread_ids;
    std::vector<std::pair<int64_t, int64_t>> ranges;
    at::parallel_for(0, kN, /*grain_size=*/1, [&](int64_t begin, int64_t end) {
        {
            std::lock_guard<std::mutex> guard(id_mutex);
            thread_ids.insert(std::this_thread::get_id());
            ranges.emplace_back(begin, end);
        }
        for (int64_t i = begin; i < end; ++i) {
            hits[static_cast<size_t>(i)].fetch_add(1, std::memory_order_relaxed);
        }
    });

    int32_t covered = 0, duplicated = 0;
    for (const auto& h : hits) {
        const int v = h.load(std::memory_order_relaxed);
        if (v == 1) {
            ++covered;
        } else if (v != 0) {
            ++duplicated;
        }
    }
    check(covered == kN, "parallel_for visited every index exactly once");
    check(duplicated == 0, "parallel_for did not duplicate any index");

    // 区间互不重叠：并行调度的正确性（与是否真并行无关）。
    std::sort(ranges.begin(), ranges.end());
    bool disjoint = true;
    for (size_t i = 1; i < ranges.size(); ++i) {
        if (ranges[i].first < ranges[i - 1].second) {
            disjoint = false;
            break;
        }
    }
    check(!ranges.empty() && disjoint, "the dispatched index ranges are disjoint");

    // 真并行：NATIVE 后端的线程池应让多个工作线程各自领到任务；单核机器上
    // 只可能观察到 1 个线程，故用 workers>1 作为前置条件，避免误判。
    if (workers > 1) {
        check(thread_ids.size() > 1,
              "parallel_for really ran on more than one worker thread");
    } else {
        std::printf("  [SKIP] single-worker pool: multi-thread evidence not applicable\n");
    }
}

// 8) 后端启用（2.13.0.1）---------------------------------------------------
// 2.13.0 把 FBGEMM/QNNPACK/XNNPACK/NNPACK/Kineto/oneDNN/ITT 全部关掉；本修订
// 逐个打开。这里的判据是**运行时可查询且数值正确**，不是 configure 的输出：
//   * at::hasMKLDNN()          -> AT_MKLDNN_ENABLED()，本修订为**真**（编进来了）
//   * at::isMKLDNNJitUsable()  -> 本进程能否拿到可执行内存（补丁 0017 的运行时
//                                 探测；解释器域全封，原生域可用）
//   * userEnabledMkldnn()      -> enabled_mkldnn && isMKLDNNJitUsable()，
//                                 即"请求开启 且 在本进程能跑"
//   * isXNNPACKAvailable()     -> #ifdef USE_XNNPACK
//   * at::_nnpack_available()  -> NNPACK 可执行路径
//   * supportedQEngines()      -> FBGEMM/QNNPACK（ONEDNN 仅在门控放行时）
//   * ITT（补丁 0018）-> 由 Python 侧断言 torch.profiler.itt.is_available()
//                        并真的走一次 range_push/pop/mark：itt.cpp 编入
//                        torch_python（torch/CMakeLists.txt:134-138），
//                        C++ 消费者链接不到那个库。
// 数值部分用手算可验的卷积/线性，避免“只是链接上了”这种弱证据。
void test_backend_enablement() {
    std::printf("[8] 后端启用：oneDNN(运行时门控) / ITT / FBGEMM / QNNPACK / "
                "XNNPACK / NNPACK / Kineto\n");

    // --- oneDNN：编译进来 + 运行时门控恒等式 -------------------------------
    // 补丁 0017 把 oneDNN 编进来（hasMKLDNN() 为真），但只在**本进程确实能获得
    // 可执行内存**时才派发：其 aarch64 内核由 xbyak_aarch64 在运行时生成，需要
    // mmap(RW)+mprotect(RX)。HarmonyOS PC 的解释器域把这条路全封死（实测
    // mmap(RWX)/mmap(RX)/memfd/实文件/已签名 .so 双映射与 RW->RX 的 mprotect
    // 全部 EINVAL/EACCES），而同一设备的原生进程不受限。
    // 所以这里断言三件事：编译期为真、门控恒等式成立、以及无论走哪条路数值都对。
    check(at::hasMKLDNN(),
          "at::hasMKLDNN() is true: oneDNN is compiled in (USE_MKLDNN=ON)");
    const bool jit_ok = at::isMKLDNNJitUsable();
    std::printf("      isMKLDNNJitUsable()=%d (this process %s obtain executable "
                "memory)\n", static_cast<int>(jit_ok),
                jit_ok ? "can" : "cannot");
    {
        // userEnabledMkldnn() 必须严格等于 enabled_mkldnn && jit_ok：
        // 这正是补丁 0017 的语义，也是所有 mkldnn 派发点的总开关。
        at::globalContext().setUserEnabledMkldnn(true);
        const bool requested = at::globalContext().userEnabledMkldnn();
        at::globalContext().setUserEnabledMkldnn(false);
        const bool not_requested = at::globalContext().userEnabledMkldnn();
        at::globalContext().setUserEnabledMkldnn(true);
        check(requested == jit_ok,
              "userEnabledMkldnn(true) == isMKLDNNJitUsable() (gate identity)");
        check(!not_requested,
              "userEnabledMkldnn() is false when the user turned it off");
    }

    check(at::globalContext().isXNNPACKAvailable(),
          "Context::isXNNPACKAvailable(): USE_XNNPACK compiled in");
    check(at::_nnpack_available(), "at::_nnpack_available(): NNPACK is available");
    check(at::hasOpenMP(), "at::hasOpenMP(): OpenMP runtime is active (_OPENMP)");
    // ITT 与 Kineto 的可用性判据都放在 Python 侧：ITT 的 itt.cpp 编入
    // torch_python（torch/CMakeLists.txt:134-138），C++ 消费者链接不到；Kineto 的
    // torch/csrc/profiler/kineto_shim.h 会无守卫地 #include <ActivityType.h>，
    // 而 libkineto 的头安装到 <prefix>/include/kineto，不在本目标的包含路径上，
    // 直接 include 会让消费方编译失败。

    // --- 量化引擎 ---------------------------------------------------------
    // supportedQEngines() 由 USE_FBGEMM / USE_PYTORCH_QNNPACK / (oneDNN+门控)
    // 决定，是量化算子真正可选的引擎集合。
    bool has_fbgemm = false, has_qnnpack = false, has_onednn = false;
    for (const auto& e : at::globalContext().supportedQEngines()) {
        if (e == at::kFBGEMM) {
            has_fbgemm = true;
        }
        if (e == at::kQNNPACK) {
            has_qnnpack = true;
        }
        if (e == at::kONEDNN) {
            has_onednn = true;
        }
    }
    check(has_fbgemm, "supportedQEngines() contains kFBGEMM (USE_FBGEMM=ON)");
    check(has_qnnpack, "supportedQEngines() contains kQNNPACK (USE_PYTORCH_QNNPACK=ON)");
    // 补丁 0017：只有门控放行时才把 kONEDNN 报成可选，否则 setQEngine(kONEDNN)
    // 会把量化算子路由到一用就 abort 的内核。
    check(has_onednn == jit_ok,
          "supportedQEngines() advertises kONEDNN exactly when JIT is usable");
    // 默认引擎：门控放行时是 oneDNN，否则回落到 QNNPACK（补丁 0016/0017）。
    check(at::globalContext().qEngine() == (jit_ok ? at::kONEDNN : at::kQNNPACK),
          "default quantized engine matches the oneDNN gate");

    // 切换到每个引擎再读回：只有该引擎真的被编译进来才设置成功。
    // 注意必须恢复**原引擎**：上游 Context::setQEngine 会把 kNoQEngine 判为
    // "not supported" 并抛异常（Context.cpp:772），不能拿它当"复位"值。
    auto engine_roundtrip = [](at::QEngine want, const char* name) -> bool {
        try {
            const at::QEngine previous = at::globalContext().qEngine();
            at::globalContext().setQEngine(want);
            const bool ok = (at::globalContext().qEngine() == want);
            at::globalContext().setQEngine(previous);
            return ok;
        } catch (const std::exception& e) {
            std::printf("      setQEngine(%s) raised: %s\n", name, e.what());
            return false;
        }
    };
    check(engine_roundtrip(at::kFBGEMM, "fbgemm"),
          "quantized engine can be set to FBGEMM and read back");
    check(engine_roundtrip(at::kQNNPACK, "qnnpack"),
          "quantized engine can be set to QNNPACK and read back");

    // --- 数值：卷积与线性（ATen 原生路径；oneDNN 已按平台限制关闭）---------
    // 用手算可验的小例子：3x3 输入 + 2x2 全 1 卷积核，sum 应为 12/16/24/28。
    {
        auto x = at::arange(1, 10, at::kFloat).reshape({1, 1, 3, 3});
        auto w = at::ones({1, 1, 2, 2}, at::kFloat);
        auto y = at::conv2d(x, w).contiguous();
        const float expect[4] = {12.f, 16.f, 24.f, 28.f};
        bool ok = (y.numel() == 4);
        if (ok) {
            const float* p = y.data_ptr<float>();
            for (int i = 0; i < 4; ++i) {
                if (std::fabs(p[i] - expect[i]) > 1e-4f) {
                    ok = false;
                    break;
                }
            }
        }
        check(ok, "conv2d numerics match the hand-computed sum-of-2x2");
    }
    {
        // 线性：weight [[3,4]]，bias [5]，输入 [1,2] -> 3+8+5 = 16
        auto in = at::tensor({1.f, 2.f}, at::kFloat).reshape({1, 2});
        auto w = at::tensor({3.f, 4.f}, at::kFloat).reshape({1, 2});
        auto b = at::tensor({5.f}, at::kFloat);
        auto out = at::linear(in, w, b);
        check(out.numel() == 1 &&
                  std::fabs(out.item<float>() - 16.f) < 1e-4f,
              "linear numerics: 3*1 + 4*2 + 5 = 16");
    }
    {
        // 更大规模的卷积 + 池化：确认多通道路径可用且输出有限。
        auto big = at::randn({2, 3, 16, 16});
        auto w2 = at::randn({8, 3, 3, 3});
        auto y2 = at::conv2d(big, w2, {}, /*stride=*/1, /*padding=*/1);
        auto pooled = at::max_pool2d(y2, {2, 2});
        check(y2.sizes() == at::IntArrayRef({2, 8, 16, 16}) &&
                  pooled.sizes() == at::IntArrayRef({2, 8, 8, 8}),
              "3->8 channel conv + max_pool produce the expected shapes");
        check(at::isfinite(y2).all().item<bool>() &&
                  at::isfinite(pooled).all().item<bool>(),
              "conv/pool outputs are finite (kernel dispatch is sane)");
    }

    // --- XNNPACK 可用时的推理路径 -----------------------------------------
    // Context 只暴露 isXNNPACKAvailable()（没有运行时开关的公共 API），所以
    // 这里断言可用性并走一次会经过 XNNPACK 派发的线性层。
    if (at::globalContext().isXNNPACKAvailable()) {
        auto lin = at::linear(at::randn({3, 16}), at::randn({8, 16}));
        check(lin.sizes() == at::IntArrayRef({3, 8}),
              "linear runs while XNNPACK is available");
        auto conv_x = at::randn({1, 3, 16, 16});
        auto conv_w = at::randn({4, 3, 3, 3});
        auto conv_y = at::conv2d(conv_x, conv_w, {}, 1, 1);
        check(conv_y.sizes() == at::IntArrayRef({1, 4, 16, 16}),
              "conv2d runs while XNNPACK is available");
    } else {
        std::printf("  [SKIP] XNNPACK unavailable at run time\n");
    }

    // --- Kineto ------------------------------------------------------------
    // 这里只验证「profiler 构建下的常规算子仍可用」；Kineto 是否真的接进来由
    // Python 侧断言（torch.autograd.profiler.kineto_available() 为真，且
    // torch.profiler 能采到事件），因为 C++ 的 kineto_shim.h 需要 libkineto
    // 私有头 <ActivityType.h>，不在本目标的包含路径上。
    {
        auto a = at::randn({64, 64});
        auto mm = at::matmul(a, a);
        check(mm.sizes() == at::IntArrayRef({64, 64}),
              "matmul works in the profiler-enabled build");
    }
}

}  // namespace

int main(int argc, char** argv) {
    Platform plat = detect_platform();
    if (argc > 1) {  // diagnostic override, see file header
        plat.sysname = argv[1];
    }

    std::printf("== HarmonyOS 专项测试: pytorch 2.13.0 ==\n");
    std::printf("   platform: sysname=%s machine=%s\n", plat.sysname.c_str(),
                plat.machine.c_str());
    std::printf("   torch version: %s\n", TORCH_VERSION);

    if (!is_harmonyos(plat.sysname)) {
        std::printf("SKIP: HarmonyOS-specific checks need a HarmonyOS host "
                    "(detected sysname=%s); exiting 0.\n", plat.sysname.c_str());
        return 0;
    }

    test_platform_identity(plat);
    test_musl_ssize_t();
    test_group_norm_algorithm_path();
    test_ohos_numeric_paths();
    test_distributed_c10d();
    test_blas_lapack_paths();
    test_thread_pool();
    test_backend_enablement();

    if (g_failures != 0) {
        std::fprintf(stderr, "ohos special test FAILED: %d check(s) failed\n", g_failures);
        return 1;
    }
    std::printf("ohos special test OK (all checks passed)\n");
    return 0;
}
