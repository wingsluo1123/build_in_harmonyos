/*
 * HMBS fixture generator — builds a small xir graph with a DPU subgraph
 * carrying "device"/"runner" attributes, serializes it to an xmodel file
 * consumed by the upstream test/test_deserialize_model.cpp (which expects
 * an external xmodel input the upstream repo does not ship).
 *
 * This is adaptation-only test infrastructure; it is not part of the
 * packaged library.
 */
#include "xir/graph/graph.hpp"
#include "xir/op/op.hpp"

#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <vector>

int main(int argc, char* argv[]) {
  std::string out = argc > 1 ? argv[1] : "fixture.xmodel";

  std::shared_ptr<xir::Graph> graph = xir::Graph::create("hmbs_fixture");

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

  // conv2d bias 独立 const op：C_out=1（weights NCHW {1,1,8,8}），1 维 FLOAT32
  auto b_attrs = xir::Attrs::create();
  b_attrs->set_attr<std::vector<std::int32_t>>("shape", {1})
      ->set_attr<std::string>("data_type", "FLOAT32")
      ->set_attr<std::vector<char>>("data", std::vector<char>(1 * 4, 1));
  auto b = graph->add_op("conv_b", "const", std::move(b_attrs), {});

  auto conv_attrs = xir::Attrs::create();
  conv_attrs->set_attr<std::vector<std::int32_t>>("kernel", {1, 1})
      ->set_attr<std::vector<std::int32_t>>("stride", {1, 1})
      ->set_attr<std::string>("pad_mode", "SAME");
  graph->add_op("conv", "conv2d", std::move(conv_attrs),
                {{"weights", {w}}, {"bias", {b}}, {"input", {data}}});

  auto root = graph->get_root_subgraph();
  root->create_children();
  auto dpu = root->merge_children({root->find_op("data"), root->find_op("conv_w"),
                                   root->find_op("conv_b"),
                                   root->find_op("conv")});
  dpu->set_attr("device", std::string{"DPU"});
  dpu->set_attr("runner", std::map<std::string, std::string>{
                              {"run", "librunner.so"}});

  graph->serialize(out);
  std::cout << "fixture xmodel written to " << out << std::endl;
  return 0;
}
