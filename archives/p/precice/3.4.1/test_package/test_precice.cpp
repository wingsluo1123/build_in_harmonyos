// Consumer test for precice 3.4.1 — exercises the real public API.
//
// 4 explicit checks (no MPI, no config file needed):
//   1. precice::getVersionInformation() contains "3.4.1".
//   2. Version info reports PRECICE_FEATURE_MPI_COMMUNICATION=N (recipe MPI OFF).
//      upstream versions.cpp.in emits PRECICE_FEATURE_*=@*_VAL@ and
//      GenerateVersionInformation.cmake maps OFF->N / ON->Y.
//   3. Version info reports PRECICE_FEATURE_PETSC_MAPPING=N (recipe PETSc OFF, same mapping).
//   4. precice::tooling::printConfigReference(MD) yields non-empty output
//      starting with the preCICE markdown marker.
// Prints CHECKS_PASSED=x/4 for the conanfile marker parsing.
#include <iostream>
#include <sstream>
#include <string>

#include <precice/Tooling.hpp>
#include <precice/precice.hpp>

int main()
{
  int passed = 0;
  const int total = 4;

  std::string info = precice::getVersionInformation();
  std::cout << "version info: " << info << std::endl;

  if (info.find("3.4.1") != std::string::npos) {
    std::cout << "CHECK 1 ok: version contains 3.4.1" << std::endl;
    ++passed;
  } else {
    std::cout << "CHECK 1 FAIL: version missing 3.4.1" << std::endl;
  }

  if (info.find("PRECICE_FEATURE_MPI_COMMUNICATION=N") != std::string::npos) {
    std::cout << "CHECK 2 ok: MPI off as configured (PRECICE_FEATURE_MPI_COMMUNICATION=N)" << std::endl;
    ++passed;
  } else {
    std::cout << "CHECK 2 FAIL: MPI flag mismatch" << std::endl;
  }

  if (info.find("PRECICE_FEATURE_PETSC_MAPPING=N") != std::string::npos) {
    std::cout << "CHECK 3 ok: PETSc off as configured (PRECICE_FEATURE_PETSC_MAPPING=N)" << std::endl;
    ++passed;
  } else {
    std::cout << "CHECK 3 FAIL: PETSc flag mismatch" << std::endl;
  }

  std::ostringstream ref;
  precice::tooling::printConfigReference(ref, precice::tooling::ConfigReferenceType::MD);
  std::string md = ref.str();
  if (!md.empty() && md.find("precice-configuration") != std::string::npos) {
    std::cout << "CHECK 4 ok: config reference MD non-empty (" << md.size() << " bytes)" << std::endl;
    ++passed;
  } else {
    std::cout << "CHECK 4 FAIL: config reference MD empty" << std::endl;
  }

  std::cout << "CHECKS_PASSED=" << passed << "/" << total << std::endl;
  return passed == total ? 0 : 1;
}
