#include <cmath>
#include <cstdio>

#include <coin/CoinPackedVector.hpp>
#include <coin/OsiRowCut.hpp>

int main() {
    OsiRowCut cut;
    CoinPackedVector row;
    int indices[] = {1, 3};
    double values[] = {2.0, -1.0};

    row.setVector(2, indices, values);
    cut.setRow(row);
    cut.setLb(-1.0);
    cut.setUb(4.0);

    if (cut.row().getNumElements() != 2) return 1;
    if (cut.row().getIndices()[0] != 1) return 1;
    if (cut.row().getIndices()[1] != 3) return 1;
    if (std::fabs(cut.row().getElements()[0] - 2.0) >= 1e-12) return 1;
    if (std::fabs(cut.row().getElements()[1] + 1.0) >= 1e-12) return 1;
    if (std::fabs(cut.lb() + 1.0) >= 1e-12) return 1;
    if (std::fabs(cut.ub() - 4.0) >= 1e-12) return 1;

    std::puts("OsiRowCut smoke test passed");
    return 0;
}
