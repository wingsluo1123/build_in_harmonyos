// test_package/test.cpp — real or-tools 9.15 API smoke test.
//
//  1. LP  : MPSolver("CLP", MPSolver::CLP_LINEAR_PROGRAMMING) — build a small
//           linear program, solve, assert status == OPTIMAL and objective 42.
//  2. CP  : CpModelBuilder + Solve() (cp_model_solver) — assert OPTIMAL with
//           the expected integer solution.
//  3. OHOS: #ifdef __OHOS__ platform-feature detection + static-link assertion
//           (no libortools.so mapped — the package is built with
//           BUILD_SHARED_LIBS=OFF, so ortools code must be statically linked).
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/utsname.h>

#include "ortools/linear_solver/linear_solver.h"
#include "ortools/sat/cp_model.h"

namespace {

int fail(const std::string& msg) {
  std::cerr << "FAIL: " << msg << "\n";
  return 1;
}

// LP: max 3*x + 4*y s.t. x + 2*y <= 14, 3*x - y >= 0, -x + y <= 0, x,y >= 0.
// Optimal solution: x = 14, y = 0, objective = 42.
int test_lp() {
  using namespace operations_research;
  MPSolver solver("CLP", MPSolver::CLP_LINEAR_PROGRAMMING);
  const double infinity = solver.infinity();
  MPVariable* const x = solver.MakeNumVar(0.0, infinity, "x");
  MPVariable* const y = solver.MakeNumVar(0.0, infinity, "y");

  MPConstraint* const c0 = solver.MakeRowConstraint(-infinity, 14.0, "c0");
  c0->SetCoefficient(x, 1.0);
  c0->SetCoefficient(y, 2.0);
  MPConstraint* const c1 = solver.MakeRowConstraint(0.0, infinity, "c1");
  c1->SetCoefficient(x, 3.0);
  c1->SetCoefficient(y, -1.0);
  MPConstraint* const c2 = solver.MakeRowConstraint(-infinity, 0.0, "c2");
  c2->SetCoefficient(x, -1.0);
  c2->SetCoefficient(y, 1.0);

  MPObjective* const objective = solver.MutableObjective();
  objective->SetCoefficient(x, 3.0);
  objective->SetCoefficient(y, 4.0);
  objective->SetMaximization();

  const MPSolver::ResultStatus status = solver.Solve();
  if (status != MPSolver::OPTIMAL) {
    return fail("MPSolver(CLP) status != OPTIMAL (status=" +
                std::to_string(static_cast<int>(status)) + ")");
  }
  const double obj = objective->Value();
  if (std::abs(obj - 42.0) > 1e-6) {
    return fail("MPSolver(CLP) objective mismatch: " + std::to_string(obj) +
                " vs expected 42.0");
  }
  std::cout << "LP OK: status=OPTIMAL objective=" << obj << "\n";
  return 0;
}

// CP: x,y in [0,10], x + y == 10, x >= 3, maximize x -> x=10, y=0.
int test_cp() {
  using namespace operations_research::sat;
  CpModelBuilder cp_model;
  const IntVar x = cp_model.NewIntVar({0, 10}).WithName("x");
  const IntVar y = cp_model.NewIntVar({0, 10}).WithName("y");
  cp_model.AddEquality(x + y, 10);
  cp_model.AddGreaterOrEqual(x, 3);
  cp_model.Maximize(x);

  const CpSolverResponse response = Solve(cp_model.Build());
  if (response.status() != CpSolverStatus::OPTIMAL) {
    return fail("CpSolver status != OPTIMAL (status=" +
                std::to_string(static_cast<int>(response.status())) + ")");
  }
  const int64_t x_val = SolutionIntegerValue(response, x);
  const int64_t y_val = SolutionIntegerValue(response, y);
  if (x_val != 10 || y_val != 0) {
    return fail("CpSolver unexpected solution: x=" + std::to_string(x_val) +
                " y=" + std::to_string(y_val) + " (expected x=10 y=0)");
  }
  std::cout << "CP OK: status=OPTIMAL x=" << x_val << " y=" << y_val << "\n";
  return 0;
}

int test_ohos() {
#ifdef __OHOS__
  // Platform feature detection: HarmonyOS exposes procfs and uname.
  std::ifstream maps("/proc/self/maps");
  if (!maps.good()) {
    return fail("OHOS: /proc/self/maps unreadable");
  }
  struct utsname un {};
  if (uname(&un) != 0) {
    return fail("OHOS: uname() failed");
  }
  const std::string machine(un.machine);
  if (machine.find("aarch64") == std::string::npos &&
      machine.find("arm64") == std::string::npos) {
    return fail("OHOS: unexpected machine: " + machine);
  }
  // Static-link assertion: the package ships static libs only
  // (BUILD_SHARED_LIBS=OFF), so no libortools.so may be loaded at runtime.
  std::string line;
  while (std::getline(maps, line)) {
    if (line.find("libortools") != std::string::npos) {
      return fail("OHOS: libortools.so mapped (expected static link): " + line);
    }
  }
  std::cout << "OHOS OK: __OHOS__ aarch64=" << machine
            << " /proc/self/maps readable, no libortools.so loaded\n";
#else
  std::cout << "OHOS tests skipped (built without __OHOS__)\n";
#endif
  return 0;
}

}  // namespace

int main() {
  int rc = 0;
  rc |= test_lp();
  rc |= test_cp();
  rc |= test_ohos();
  if (rc == 0) {
    std::cout << "or-tools 9.15 test_package: ALL PASS\n";
  }
  return rc;
}
