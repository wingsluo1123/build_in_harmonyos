// Real meep consumer test (rule 12 / R34): compiles, links against
// libmeep.a + all transitive static deps, and CALLS the meep public API.
// Exercises: initialize -> structure -> fields -> one FDTD time step
// -> field query. A consumer that cannot link or run against the
// installed package fails here, even if package structure looks fine.

#include <cmath>
#include <complex>
#include <cstdio>

#include <meep.hpp>

using namespace meep;

// Uniform vacuum eps (material function signature: double f(const vec &)).
static double vacuum_eps(const vec & /*p*/) { return 1.0; }

int main() {
    // 1. Library global initialization (RAII MPI wrapper).
    int argc = 1;
    char program_name[] = "test_consumer";
    char *argv_array[1] = {program_name};
    char **argv = argv_array;
    initialize mpi(argc, argv);
    verbosity = 0;

    // 2. Build a small 1D FDTD problem: 2.0 a.u. cell at resolution 10.
    const double resolution = 10.0;
    grid_volume gv = vol1d(2.0, resolution);
    structure s(gv, vacuum_eps);

    // 3. Allocate fields and run one real FDTD time step (core engine).
    fields f(&s);
    f.step();

    // 4. Query the Ex field at cell center (public getter + complex math).
    const std::complex<double> ex = f.get_field(Ex, vec(1.0));

    master_printf("OHOS meep consumer OK: |Ex| after 1 step = %g\n",
                  std::abs(ex));

    // Sanity: the queried field must be a finite number.
    if (std::isnan(ex.real()) || std::isnan(ex.imag())) {
        fprintf(stderr, "FAIL: Ex is NaN\n");
        return 1;
    }
    return 0;
}
