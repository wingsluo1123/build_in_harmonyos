/* Installed-package consumer test for XNNPACK.
 *
 * 以"库的使用者"身份，只经公开头文件 <xnnpack.h> 构造 subgraph / runtime，
 * 真跑 aarch64 上的 f32 微内核，并逐元素与 CPU 参考实现对拍。
 *
 * 不使用 assert()：CMake 的 Release 配置会定义 NDEBUG，把 assert 预处理成
 * 空语句，测试会退化成"必然通过"的假测试（CI 的 L1e 破坏性反向验证正是
 * 针对这种情形）。这里用自研 CHECK 宏累计失败数，最后以非零退出码上报，
 * 并打印 checks=/failures= 供外部复算。
 *
 * 覆盖点：
 *   T1  xnn_initialize / xnn_deinitialize 正常；
 *   T2  Fully Connected（batch=5, in=48, out=17）端到端数值对拍；
 *   T3  Fully Connected 大 K（batch=16, in=256, out=33）—— 走 GEMM 路径；
 *   T4  Fully Connected 退化形状（batch=1, in=1, out=1）—— 走 GEMV 路径；
 *   T5  2D Convolution（[1,9,9,3] × 3x3 × 8 输出通道）端到端数值对拍 ——
 *       XNNPACK 在 aarch64 上最主要的 NEON 卷积微内核路径；
 *   T6  同一 runtime 重复 invoke 结果稳定（权重打包缓存复用路径）。
 */
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include <xnnpack.h>

namespace {

int g_checks = 0;
int g_failures = 0;

#define CHECK_TRUE(expr)                                                       \
  do {                                                                         \
    ++g_checks;                                                                \
    if (!(expr)) {                                                             \
      std::fprintf(stderr, "  [FAIL] %s (line %d)\n", #expr, __LINE__);        \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

#define CHECK_STATUS(expr)                                                     \
  do {                                                                         \
    ++g_checks;                                                                \
    const enum xnn_status status_ = (expr);                                    \
    if (status_ != xnn_status_success) {                                       \
      std::fprintf(stderr, "  [FAIL] %s -> xnn_status %d (line %d)\n", #expr,  \
                   static_cast<int>(status_), __LINE__);                       \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

#define CHECK_NEAR(actual, expected)                                           \
  do {                                                                         \
    ++g_checks;                                                                \
    const double a_ = static_cast<double>(actual);                             \
    const double e_ = static_cast<double>(expected);                           \
    const double tol_ = 1e-3 * (std::fabs(e_) > 1.0 ? std::fabs(e_) : 1.0);    \
    if (!(std::fabs(a_ - e_) <= tol_)) {                                       \
      std::fprintf(stderr,                                                     \
                   "  [FAIL] %s line %d: got %.7g, want %.7g (tol %.7g)\n",    \
                   #actual, __LINE__, a_, e_, tol_);                           \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

// 确定性伪随机权重（避免依赖 <random> 的实现差异）
float W(size_t i) { return std::sin(0.37f * static_cast<float>(i) + 0.11f) * 0.5f; }

// ── T2/T3/T4: Fully Connected ───────────────────────────────────────────────
void TestFullyConnected(size_t batch, size_t in_channels, size_t out_channels,
                        const char* label) {
  std::printf("[RUN ] fully_connected %s (batch=%zu in=%zu out=%zu)\n", label,
              batch, in_channels, out_channels);
  const float output_min = -1.0e30f;
  const float output_max = 1.0e30f;

  std::vector<float> filter(out_channels * in_channels);
  for (size_t i = 0; i < filter.size(); ++i) {
    filter[i] = W(i);
  }
  std::vector<float> bias(out_channels);
  for (size_t i = 0; i < out_channels; ++i) {
    bias[i] = 0.05f * static_cast<float>(i) - 0.25f;
  }
  std::vector<float> input(batch * in_channels);
  for (size_t i = 0; i < input.size(); ++i) {
    input[i] = W(i + 7);
  }
  std::vector<float> output(batch * out_channels, 0.0f);

  xnn_subgraph_t subgraph = nullptr;
  CHECK_STATUS(xnn_create_subgraph(/*external_value_ids=*/4, /*flags=*/0, &subgraph));

  const size_t input_dims[2] = {batch, in_channels};
  const size_t filter_dims[2] = {out_channels, in_channels};
  const size_t bias_dims[1] = {out_channels};
  const size_t output_dims[2] = {batch, out_channels};

  uint32_t input_id = XNN_INVALID_VALUE_ID;
  uint32_t filter_id = XNN_INVALID_VALUE_ID;
  uint32_t bias_id = XNN_INVALID_VALUE_ID;
  uint32_t output_id = XNN_INVALID_VALUE_ID;
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 2, input_dims,
                                       nullptr, /*external_id=*/0,
                                       XNN_VALUE_FLAG_EXTERNAL_INPUT, &input_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 2, filter_dims,
                                       filter.data(), XNN_INVALID_VALUE_ID, 0,
                                       &filter_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 1, bias_dims,
                                       bias.data(), XNN_INVALID_VALUE_ID, 0,
                                       &bias_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 2, output_dims,
                                       nullptr, /*external_id=*/1,
                                       XNN_VALUE_FLAG_EXTERNAL_OUTPUT, &output_id));
  CHECK_STATUS(xnn_define_fully_connected(subgraph, output_min, output_max, input_id,
                                          filter_id, bias_id, output_id,
                                          /*flags=*/0));

  xnn_runtime_t runtime = nullptr;
  CHECK_STATUS(xnn_create_runtime_v2(subgraph, /*threadpool=*/nullptr, /*flags=*/0,
                                     &runtime));
  CHECK_STATUS(xnn_reshape_runtime(runtime));

  const struct xnn_external_value external[] = {
      {input_id, input.data()},
      {output_id, output.data()},
  };
  CHECK_STATUS(xnn_setup_runtime_v2(runtime, 2, external));
  CHECK_STATUS(xnn_invoke_runtime(runtime));

  // 与 CPU 三重循环参考实现对拍（double 累加）
  for (size_t n = 0; n < batch; ++n) {
    for (size_t o = 0; o < out_channels; ++o) {
      double expected = static_cast<double>(bias[o]);
      for (size_t k = 0; k < in_channels; ++k) {
        expected += static_cast<double>(input[n * in_channels + k]) *
                    static_cast<double>(filter[o * in_channels + k]);
      }
      CHECK_NEAR(output[n * out_channels + o], expected);
    }
  }

  // T6: 重复 invoke 结果稳定
  std::vector<float> second(output.size(), 0.0f);
  const struct xnn_external_value external2[] = {
      {input_id, input.data()},
      {output_id, second.data()},
  };
  CHECK_STATUS(xnn_setup_runtime_v2(runtime, 2, external2));
  CHECK_STATUS(xnn_invoke_runtime(runtime));
  for (size_t i = 0; i < output.size(); ++i) {
    CHECK_TRUE(output[i] == second[i]);
  }

  CHECK_STATUS(xnn_delete_runtime(runtime));
  CHECK_STATUS(xnn_delete_subgraph(subgraph));
}

// ── T5: 2D Convolution ──────────────────────────────────────────────────────
void TestConvolution2D() {
  const size_t batches = 1;
  const size_t input_height = 9;
  const size_t input_width = 9;
  const size_t input_channels = 3;
  const size_t kernel_height = 3;
  const size_t kernel_width = 3;
  const size_t output_channels = 8;
  const size_t output_height = input_height - kernel_height + 1;
  const size_t output_width = input_width - kernel_width + 1;

  std::printf("[RUN ] convolution_2d ([%zu,%zu,%zu,%zu] x %zux%zu -> %zu ch)\n",
              batches, input_height, input_width, input_channels, kernel_height,
              kernel_width, output_channels);

  std::vector<float> filter(output_channels * kernel_height * kernel_width *
                            input_channels);
  for (size_t i = 0; i < filter.size(); ++i) {
    filter[i] = W(i + 3);
  }
  std::vector<float> bias(output_channels);
  for (size_t i = 0; i < output_channels; ++i) {
    bias[i] = 0.02f * static_cast<float>(i);
  }
  std::vector<float> input(batches * input_height * input_width * input_channels);
  for (size_t i = 0; i < input.size(); ++i) {
    input[i] = W(i + 101);
  }
  std::vector<float> output(
      batches * output_height * output_width * output_channels, 0.0f);

  xnn_subgraph_t subgraph = nullptr;
  CHECK_STATUS(xnn_create_subgraph(4, 0, &subgraph));

  const size_t input_dims[4] = {batches, input_height, input_width, input_channels};
  const size_t filter_dims[4] = {output_channels, kernel_height, kernel_width,
                                 input_channels};
  const size_t bias_dims[1] = {output_channels};
  const size_t output_dims[4] = {batches, output_height, output_width,
                                 output_channels};

  uint32_t input_id = XNN_INVALID_VALUE_ID;
  uint32_t filter_id = XNN_INVALID_VALUE_ID;
  uint32_t bias_id = XNN_INVALID_VALUE_ID;
  uint32_t output_id = XNN_INVALID_VALUE_ID;
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 4, input_dims,
                                       nullptr, 0, XNN_VALUE_FLAG_EXTERNAL_INPUT,
                                       &input_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 4, filter_dims,
                                       filter.data(), XNN_INVALID_VALUE_ID, 0,
                                       &filter_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 1, bias_dims,
                                       bias.data(), XNN_INVALID_VALUE_ID, 0,
                                       &bias_id));
  CHECK_STATUS(xnn_define_tensor_value(subgraph, xnn_datatype_fp32, 4, output_dims,
                                       nullptr, 1, XNN_VALUE_FLAG_EXTERNAL_OUTPUT,
                                       &output_id));
  CHECK_STATUS(xnn_define_convolution_2d(
      subgraph,
      /*input_padding_top=*/0, /*input_padding_right=*/0,
      /*input_padding_bottom=*/0, /*input_padding_left=*/0,
      /*kernel_height=*/static_cast<uint32_t>(kernel_height),
      /*kernel_width=*/static_cast<uint32_t>(kernel_width),
      /*subsampling_height=*/1, /*subsampling_width=*/1,
      /*dilation_height=*/1, /*dilation_width=*/1,
      /*groups=*/1,
      /*group_input_channels=*/input_channels,
      /*group_output_channels=*/output_channels,
      /*output_min=*/-1.0e30f, /*output_max=*/1.0e30f, input_id, filter_id, bias_id,
      output_id, /*flags=*/0));

  xnn_runtime_t runtime = nullptr;
  CHECK_STATUS(xnn_create_runtime_v2(subgraph, nullptr, 0, &runtime));
  CHECK_STATUS(xnn_reshape_runtime(runtime));
  const struct xnn_external_value external[] = {
      {input_id, input.data()},
      {output_id, output.data()},
  };
  CHECK_STATUS(xnn_setup_runtime_v2(runtime, 2, external));
  CHECK_STATUS(xnn_invoke_runtime(runtime));

  // 参考实现：NHWC 直接卷积（double 累加）
  for (size_t oh = 0; oh < output_height; ++oh) {
    for (size_t ow = 0; ow < output_width; ++ow) {
      for (size_t oc = 0; oc < output_channels; ++oc) {
        double expected = static_cast<double>(bias[oc]);
        for (size_t kh = 0; kh < kernel_height; ++kh) {
          for (size_t kw = 0; kw < kernel_width; ++kw) {
            for (size_t ic = 0; ic < input_channels; ++ic) {
              const double x = static_cast<double>(
                  input[((oh + kh) * input_width + (ow + kw)) * input_channels + ic]);
              const double w = static_cast<double>(
                  filter[((oc * kernel_height + kh) * kernel_width + kw) *
                             input_channels +
                         ic]);
              expected += x * w;
            }
          }
        }
        CHECK_NEAR(output[(oh * output_width + ow) * output_channels + oc], expected);
      }
    }
  }

  CHECK_STATUS(xnn_delete_runtime(runtime));
  CHECK_STATUS(xnn_delete_subgraph(subgraph));
}

}  // namespace

int main() {
  CHECK_STATUS(xnn_initialize(/*allocator=*/nullptr));

  TestFullyConnected(5, 48, 17, "small");
  TestFullyConnected(16, 256, 33, "gemm");
  TestFullyConnected(1, 1, 1, "degenerate");
  TestConvolution2D();

  CHECK_STATUS(xnn_deinitialize());

  std::printf("HMBS_TEST_PACKAGE_RESULT={\"name\":\"test_xnnpack\",\"checks\":%d,"
              "\"failures\":%d}\n",
              g_checks, g_failures);
  std::printf("checks=%d failures=%d\n", g_checks, g_failures);
  if (g_failures != 0) {
    std::fprintf(stderr, "test_xnnpack FAILED: %d of %d checks failed\n", g_failures,
                 g_checks);
    return EXIT_FAILURE;
  }
  std::printf("test_xnnpack PASSED: %d checks\n", g_checks);
  return EXIT_SUCCESS;
}
