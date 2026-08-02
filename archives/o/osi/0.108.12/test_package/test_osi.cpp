#include <cmath>
#include <cstdio>

#include <coin/CoinPackedVector.hpp>
#include <coin/OsiRowCut.hpp>

namespace {
bool check(bool condition, const char* message) {
    if (!condition) {
        std::fprintf(stderr, "OsiRowCut smoke test failed: %s\n", message);
        return false;
    }
    return true;
}
} // namespace

int main() {
    OsiRowCut cut;
    CoinPackedVector row;
    int indices[] = {1, 3};
    double values[] = {2.0, -1.0};

    row.setVector(2, indices, values);
    cut.setRow(row);
    cut.setLb(-1.0);
    cut.setUb(4.0);

    if (!check(cut.row().getNumElements() == 2, "unexpected row element count") ||
        !check(cut.row().getIndices()[0] == 1, "unexpected first row index") ||
        !check(cut.row().getIndices()[1] == 3, "unexpected second row index") ||
        !check(std::fabs(cut.row().getElements()[0] - 2.0) < 1e-12, "unexpected first row value") ||
        !check(std::fabs(cut.row().getElements()[1] + 1.0) < 1e-12, "unexpected second row value") ||
        !check(std::fabs(cut.lb() + 1.0) < 1e-12, "unexpected lower bound") ||
        !check(std::fabs(cut.ub() - 4.0) < 1e-12, "unexpected upper bound")) {
        return 1;
    }

    std::puts("OsiRowCut smoke test passed");
    return 0;
}
