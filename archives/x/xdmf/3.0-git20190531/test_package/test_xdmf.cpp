#include "XdmfArray.hpp"
#include "XdmfArrayType.hpp"
#include "XdmfGeometryType.hpp"
#include "XdmfInformation.hpp"
#include "XdmfTopologyType.hpp"

#include <iostream>
#include <string>

static int g_run = 0;
static int g_failed = 0;

static void check(bool cond, const char *name) {
  ++g_run;
  if (cond) {
    std::cout << "[PASS] " << name << std::endl;
  } else {
    ++g_failed;
    std::cout << "[FAIL] " << name << std::endl;
  }
}

int main() {
  // 1: fresh array is empty (XdmfCore API).
  shared_ptr<XdmfArray> array = XdmfArray::New();
  check(array->getSize() == 0, "array_initial_size_zero");

  // 2-3: insert int32 values and read them back (XdmfCore API).
  int values[] = {1, 2, 3, 4};
  array->insert(0, &values[0], 4, 1, 1);
  check(array->getSize() == 4, "array_size_after_insert");
  check(array->getValuesString().compare("1 2 3 4") == 0, "array_values_string");

  // 4: key/value metadata round-trip (XdmfCore API).
  shared_ptr<XdmfInformation> info =
      XdmfInformation::New("hmbs_key", "hmbs_value");
  check(info->getKey() == "hmbs_key" && info->getValue() == "hmbs_value",
        "information_key_value");

  // 5: topology descriptor (Xdmf API, links the Xdmf library).
  shared_ptr<const XdmfTopologyType> hexa = XdmfTopologyType::Hexahedron();
  check(hexa->getNodesPerElement() == 8, "hexahedron_nodes_per_element");

  // 6: geometry descriptor (Xdmf API, links the Xdmf library).
  shared_ptr<const XdmfGeometryType> xyz = XdmfGeometryType::XYZ();
  check(xyz->getDimensions() == 3, "xyz_dimensions");

  std::cout << "Results: " << (g_run - g_failed) << "/" << g_run
            << " checks passed" << std::endl;
  std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":"
            << (g_failed == 0 ? "true" : "false")
            << ",\"command\":\"./test_xdmf\",\"discovered\":" << g_run
            << ",\"passedCount\":" << (g_run - g_failed) << "}" << std::endl;
  return g_failed == 0 ? 0 : 1;
}
