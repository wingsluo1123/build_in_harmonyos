#include <kdl/frames.hpp>
#include <kdl/chain.hpp>
#include <kdl/chainfksolverpos_recursive.hpp>
#include <kdl/chainjnttojacsolver.hpp>
#include <kdl/frames_io.hpp>
#include <iostream>
#include <cassert>

int main() {
    // Test 1: Basic frame arithmetic
    KDL::Frame frame1 = KDL::Frame::Identity();
    KDL::Frame frame2(KDL::Rotation::RPY(0.5, 0.2, 0.1),
                      KDL::Vector(1.0, 2.0, 3.0));
    KDL::Frame result = frame1 * frame2;
    assert(result.p.x() == 1.0);
    assert(result.p.y() == 2.0);
    assert(result.p.z() == 3.0);
    std::cout << "Frame arithmetic: PASS" << std::endl;

    // Test 2: Chain creation and forward kinematics
    KDL::Chain chain;
    chain.addSegment(KDL::Segment(KDL::Joint(KDL::Joint::RotZ),
                                  KDL::Frame(KDL::Rotation::Identity(),
                                             KDL::Vector(0.0, 0.0, 1.0))));
    chain.addSegment(KDL::Segment(KDL::Joint(KDL::Joint::RotZ),
                                  KDL::Frame(KDL::Rotation::Identity(),
                                             KDL::Vector(0.0, 0.0, 1.0))));

    KDL::ChainFkSolverPos_recursive fksolver(chain);
    KDL::JntArray q(chain.getNrOfJoints());
    q(0) = 0.5;
    q(1) = 0.3;
    KDL::Frame cartpos;
    int ret = fksolver.JntToCart(q, cartpos);
    assert(ret == 0);
    std::cout << "Forward kinematics: PASS (ret=" << ret << ")" << std::endl;

    // Test 3: Jacobian
    KDL::ChainJntToJacSolver jacsolver(chain);
    KDL::Jacobian jac(chain.getNrOfJoints());
    ret = jacsolver.JntToJac(q, jac);
    assert(ret == 0);
    std::cout << "Jacobian: PASS (ret=" << ret << ", cols=" << jac.columns() << ")" << std::endl;

    std::cout << "orocos-kdl 1.5.3: ALL TESTS PASSED" << std::endl;
    return 0;
}