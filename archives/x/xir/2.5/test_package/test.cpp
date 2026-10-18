/*
 * xir 2.5 HarmonyOS 消费者用例（R34：实质调用被测包 API，非空壳）：
 * 建图（Graph/add_op）→ 序列化为 xmodel 文件 → 反序列化回读 →
 * 校验图内容往返一致。在 OHOS aarch64 真机执行。
 */
#include "xir/graph/graph.hpp"
#include "xir/op/op.hpp"

#include <iostream>
#include <memory>
#include <string>
#include <vector>

int main(int argc, char* argv[]) {
  std::string path = argc > 1 ? argv[1] : "hmbs_consumer.xmodel";

  // 1. 建图：data -> conv2d(weights)
  // 注意：xir 内置 op 表要求 conv2d weights 为 4 维 NCHW
  // （shape_inference.cpp:226 校验，2 维会 XIR_INVALID_ARG_OCCUR FATAL）
  auto graph = xir::Graph::create("hmbs_consumer");
  auto data_attrs = xir::Attrs::create();
  data_attrs->set_attr<std::vector<std::int32_t>>("shape", {1, 8, 8, 8})
      ->set_attr<std::string>("data_type", "FLOAT32");
  auto data = graph->add_op("data", "data", std::move(data_attrs), {});

  auto w_attrs = xir::Attrs::create();
  w_attrs->set_attr<std::vector<std::int32_t>>("shape", {1, 1, 8, 8})
      ->set_attr<std::string>("data_type", "FLOAT32")
      ->set_attr<std::vector<char>>("data",
                                    std::vector<char>(1 * 1 * 8 * 8 * 4, 1));
  auto w = graph->add_op("conv_w", "const", std::move(w_attrs), {});

  auto conv_attrs = xir::Attrs::create();
  conv_attrs->set_attr<std::vector<std::int32_t>>("kernel", {1, 1})
      ->set_attr<std::vector<std::int32_t>>("stride", {1, 1})
      ->set_attr<std::string>("pad_mode", "SAME");
  graph->add_op("conv", "conv2d", std::move(conv_attrs),
                {{"weights", {w}}, {"input", {data}}});

  // 2. 序列化到 xmodel 文件
  graph->serialize(path);

  // 3. 反序列化回读并校验
  auto back = xir::Graph::deserialize(path);
  auto root = back->get_root_subgraph();
  if (root->get_op_num() != 3) {
    std::cerr << "FAIL: op num " << root->get_op_num() << " != 3"
              << std::endl;
    return 1;
  }
  if (!root->has_op("data") || !root->has_op("conv_w") ||
      !root->has_op("conv")) {
    std::cerr << "FAIL: round-trip ops mismatch" << std::endl;
    return 1;
  }
  std::cout << "HMBS xir consumer test passed: serialize/deserialize "
               "round-trip OK (" << path << ")" << std::endl;
  return 0;
}
