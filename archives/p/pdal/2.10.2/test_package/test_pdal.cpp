// test_package for PDAL — verifies the library can be linked and basic types work
#include <pdal/PointView.hpp>
#include <pdal/PointTable.hpp>
#include <pdal/Stage.hpp>
#include <pdal/StageFactory.hpp>
#include <pdal/PipelineManager.hpp>

#include <iostream>
#include <cstdlib>

int main() {
    pdal::PointTable table;
    pdal::PipelineManager manager;

    // Verify PDAL library is linked and basic types work
    std::cout << "PDAL test: PointTable created successfully" << std::endl;

    // Verify StageFactory can be instantiated
    pdal::StageFactory factory;
    std::cout << "PDAL test: StageFactory created successfully" << std::endl;

    std::cout << "PDAL test PASSED" << std::endl;
    return 0;
}
