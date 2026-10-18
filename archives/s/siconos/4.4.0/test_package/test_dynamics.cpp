#include <algorithm>
#include <cmath>
#include <cstdio>
#include <memory>
#include "SiconosKernel.hpp"
#include "LinearSensor.hpp"
#include "Contact2dR.hpp"
#include "MechanicsIO.hpp"
#include "LagrangianLinearDiagonalDS.hpp"
static int checks = 0, failures = 0;
static void check(bool ok, const char *name) {
  ++checks; if (!ok) ++failures;
  std::printf("[%s] %s\n", ok ? "PASS" : "FAIL", name);
}
static void vector_ownership() {
  auto x = std::make_shared<SiconosVector>(2);
  auto y = std::make_shared<SiconosVector>(1);
  (*x)(0) = 1; (*x)(1) = 2; (*y)(0) = 3;
  BlockVector blocks(x, y);
  auto z = std::make_shared<SiconosVector>(1);
  (*z)(0) = 4; blocks.insertPtr(z); (*z)(0) = 5;
  check(blocks.vector(2) == z && blocks(3) == 5,
        "insertPtr shares ownership and mutations");
  SiconosVector copy(blocks); copy(0) = 8;
  check(copy.num() == Siconos::DENSE && copy.size() == 4 &&
        (*x)(0) == 1 && copy(1) == 2 && copy(3) == 5,
        "dense block copy preserves values and owns independent storage");
}
static void affine_system() {
  auto x = std::make_shared<SiconosVector>(2);
  (*x)(0) = 5; (*x)(1) = 10;
  auto a = std::make_shared<SimpleMatrix>(2, 2); a->zero();
  auto b = std::make_shared<SiconosVector>(2);
  (*b)(0) = -1; (*b)(1) = 0;
  auto ds = std::make_shared<FirstOrderLinearTIDS>(x, a, b);
  auto model = std::make_shared<NonSmoothDynamicalSystem>(0, 1);
  model->insertDynamicalSystem(ds);
  auto td = std::make_shared<TimeDiscretisation>(0, .01);
  auto simulation = std::make_shared<TimeStepping>(model, td, 0);
  simulation->associate(std::make_shared<EulerMoreauOSI>(.5), ds);
  simulation->initialize();
  unsigned int steps = 0;
  while (simulation->hasNextEvent() && steps < 101) {
    simulation->computeOneStep(); simulation->nextStep(); ++steps;
  }
  check(steps == 100, "Euler-Moreau executes 100 steps");
  check(std::fabs((*ds->x())(0) - 4) < 1e-10 &&
        std::fabs((*ds->x())(1) - 10) < 1e-10,
        "affine dynamics matches analytical solution");
  auto c = std::make_shared<SimpleMatrix>(1, 2);
  (*c)(0, 0) = 2; (*c)(0, 1) = -1;
  LinearSensor sensor(ds, c);
  sensor.initialize(*model); sensor.capture();
  check(sensor.getYDim() == 1 && std::fabs(sensor.y()(0) + 2) < 1e-10,
        "control linear sensor computes Cx");
  (*ds->x())(0) = 7; sensor.capture();
  check(std::fabs(sensor.y()(0) - 4) < 1e-10, "sensor captures changed state");
}
static void bouncing_ball() {
  auto q = std::make_shared<SiconosVector>(1);
  auto v = std::make_shared<SiconosVector>(1);
  (*q)(0) = 1; (*v)(0) = 0;
  auto mass = std::make_shared<SimpleMatrix>(1, 1); (*mass)(0, 0) = 1;
  auto ball = std::make_shared<LagrangianLinearTIDS>(q, v, mass);
  auto force = std::make_shared<SiconosVector>(1); (*force)(0) = -9.81;
  ball->setFExtPtr(force);
  auto h = std::make_shared<SimpleMatrix>(1, 1); (*h)(0, 0) = 1;
  auto contact = std::make_shared<Interaction>(
      std::make_shared<NewtonImpactNSL>(.8), std::make_shared<LagrangianLinearTIR>(h));
  auto model = std::make_shared<NonSmoothDynamicalSystem>(0, 1);
  model->insertDynamicalSystem(ball); model->link(contact, ball);
  auto td = std::make_shared<TimeDiscretisation>(0, .0005);
  auto simulation = std::make_shared<TimeStepping>(
      model, td, std::make_shared<MoreauJeanOSI>(.5), std::make_shared<LCP>());
  simulation->initialize();
  unsigned int steps = 0, impacts = 0;
  double min_height = 1, restitution_error = 0; bool finite = true;
  while (simulation->hasNextEvent() && steps < 2001) {
    const double before = (*ball->velocity())(0);
    simulation->computeOneStep();
    const double height = (*ball->q())(0), speed = (*ball->velocity())(0);
    finite = finite && std::isfinite(height) && std::isfinite(speed);
    min_height = std::min(min_height, height);
    if (before < -1 && speed > 1) {
      ++impacts; restitution_error = std::fabs(speed + .8 * before);
    }
    simulation->nextStep(); ++steps;
  }
  check(steps == 2000 && finite, "Moreau-Jean completes 2000 finite steps");
  check(impacts == 1 && restitution_error < .03, "impact LCP enforces Newton restitution");
  check(min_height > -.003, "ground nonpenetration within step error");
  check((*ball->q())(0) > .2 && (*ball->q())(0) < .9,
        "post-impact ball remains above ground");
  MechanicsIO io;
  auto positions = io.positions(*model);
  auto velocities = io.velocities(*model);
  check(positions->size(0) == 1 && positions->size(1) == 2 &&
        std::fabs((*positions)(0, 1) - (*ball->q())(0)) < 1e-12,
        "I/O exports actual simulated position");
  check(velocities->size(0) == 1 && velocities->size(1) == 2 &&
        std::fabs((*velocities)(0, 1) - (*ball->velocity())(0)) < 1e-12,
        "I/O exports actual simulated velocity");
  Contact2dR planar_contact;
  SiconosVector local(2), floor(2), normal(2), gap(2);
  local.zero(); floor.zero(); normal.zero(); local(1) = -.5; normal(1) = 1;
  planar_contact.updateContactPoints(local, floor, normal);
  auto pose = std::make_shared<SiconosVector>(3); pose->zero(); (*pose)(1) = 1;
  BlockVector coordinates, parameters; coordinates.insertPtr(pose);
  planar_contact.computeh(coordinates, parameters, gap);
  const bool separated = std::fabs(gap(0) - .5) < 1e-12;
  (*pose)(1) = .25; planar_contact.computeh(coordinates, parameters, gap);
  check(separated && std::fabs(gap(0) + .25) < 1e-12,
        "mechanics computes positive gap and negative penetration");
}
static void diagonal_io() {
  auto q = std::make_shared<SiconosVector>(2);
  auto v = std::make_shared<SiconosVector>(2);
  auto stiffness = std::make_shared<SiconosVector>(2);
  (*q)(0) = 1; (*q)(1) = 2; (*v)(0) = 3; (*v)(1) = 4;
  stiffness->zero();
  auto ds = std::make_shared<LagrangianLinearDiagonalDS>(q, v, stiffness);
  NonSmoothDynamicalSystem model(0, 1); model.insertDynamicalSystem(ds);
  MechanicsIO io;
  auto positions = io.positions(model), velocities = io.velocities(model);
  check(positions->size(0) == 1 && positions->size(1) == 3 &&
        (*positions)(0, 1) == 1 && (*positions)(0, 2) == 2,
        "I/O dispatches diagonal-system positions");
  check(velocities->size(0) == 1 && velocities->size(1) == 3 &&
        (*velocities)(0, 1) == 3 && (*velocities)(0, 2) == 4,
        "I/O dispatches diagonal-system velocities");
}
int main() {
  try { vector_ownership(); affine_system(); bouncing_ball(); diagonal_io(); }
  catch (const std::exception& error) {
    std::fprintf(stderr, "consumer exception: %s\n", error.what());
    Siconos::exception::process();
    return 1;
  }
  std::printf("CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
  return failures ? 1 : 0;
}
