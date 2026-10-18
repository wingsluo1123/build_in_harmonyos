// test_palabos.cpp - consumer test for palabos 2.3.01.
// Exercises the real 2D lattice Boltzmann API: D2Q9 descriptor, BGK
// dynamics, equilibrium initialization, collideAndStream loop, and
// macroscopic observables. 4 explicit checks.
#include "palabos2D.h"
#include "palabos2D.hh"

#include <cmath>
#include <iostream>

using namespace plb;
using namespace plb::descriptors;

typedef double T;
#define DESCRIPTOR D2Q9Descriptor

static int checkCount = 0;
static int passCount = 0;

static void check(bool cond, const char* name)
{
    ++checkCount;
    if (cond) {
        ++passCount;
        std::cout << "PASS: " << name << std::endl;
    } else {
        std::cout << "FAIL: " << name << std::endl;
    }
}

int main(int argc, char* argv[])
{
    plbInit(&argc, &argv);

    // Check 1: D2Q9 descriptor has 9 velocities.
    check(DESCRIPTOR<T>::q == 9, "D2Q9 q==9");

    const plint nx = 32;
    const plint ny = 32;
    const T omega = (T)1.0;

    MultiBlockLattice2D<T, DESCRIPTOR> lattice(
        nx, ny, new BGKdynamics<T, DESCRIPTOR>(omega));

    // Check 2: lattice dimensions match construction.
    check(lattice.getNx() == nx && lattice.getNy() == ny, "lattice 32x32 size");

    initializeAtEquilibrium(lattice, lattice.getBoundingBox(),
                            (T)1.0, Array<T, 2>((T)0.0, (T)0.0));
    lattice.initialize();

    for (int i = 0; i < 5; ++i) {
        lattice.collideAndStream();
    }

    // Check 3: average density stays finite and near 1.0.
    T rho = getStoredAverageDensity(lattice);
    check(std::isfinite(rho) && rho > (T)0.9 && rho < (T)1.1, "average density near 1.0");

    // Check 4: average energy is finite and non-negative.
    T energy = getStoredAverageEnergy(lattice);
    check(std::isfinite(energy) && energy >= (T)0.0, "average energy finite");

    std::cout << "checks=" << checkCount << " passed=" << passCount << std::endl;
    return (checkCount == 4 && passCount == 4) ? 0 : 1;
}
