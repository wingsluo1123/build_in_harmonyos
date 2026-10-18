/*
    Unit tests for the Lunatico Armadillo / Platypus focuser driver
    (directory indi-armadillo-platypus/ of the upstream indi-3rdparty monorepo).

    They exercise the driver's own code with no hardware and no INDI server:
      * the device name and the focuser capability flags set by the constructor;
      * the INDI property vectors filled in by initProperties()
        (temperature readout, per-port switch, wiring and half-step options).

    Why the property vectors are inspected directly instead of through INDI's
    public getNumber()/getSwitch() accessors: INDI only inserts a driver's
    properties into the device container once it is CONNECTED -- and
    ArmPlat::updateProperties() guards every defineProperty() behind
    isConnected() (deleteProperty()ing them otherwise) -- so the accessors
    return nothing offline.  The INDI and standard headers are therefore
    included FIRST, so that their include guards make the redefinition below a
    no-op for them, and only this driver's own class declaration sees
    `private public`.
*/
#include <gtest/gtest.h>

#include "indifocuser.h"
#include "indicom.h"
#include "connectionplugins/connectionserial.h"
#include <cmath>
#include <cstring>
#include <memory>
#include <termios.h>
#include <unistd.h>

#define private public
#define ARMADILLO          // same translation-unit selection as indi_armadillo_focus
#include "arm_plat_focuser_common.cpp"
#undef private

TEST(ArmPlatFocuser, DeviceNameMatchesController)
{
    ArmPlat dev;
    EXPECT_STREQ(dev.getDefaultName(), "Armadillo focuser");
}

TEST(ArmPlatFocuser, ConstructorDeclaresFocuserCapabilities)
{
    ArmPlat dev;
    // set by ArmPlat::ArmPlat()
    EXPECT_TRUE(dev.CanAbsMove());
    EXPECT_TRUE(dev.CanRelMove());
    EXPECT_TRUE(dev.CanAbort());
    EXPECT_TRUE(dev.CanSync());
    EXPECT_TRUE(dev.HasBacklash());
    // this driver never sets these two
    EXPECT_FALSE(dev.CanReverse());
    EXPECT_FALSE(dev.HasVariableSpeed());
}

TEST(ArmPlatFocuser, InitPropertiesRegistersTemperatureReadout)
{
    ArmPlat dev;
    ASSERT_TRUE(dev.initProperties());
    EXPECT_EQ(dev.TemperatureNP.nnp, 1);
    EXPECT_STREQ(dev.TemperatureNP.name, "FOCUS_TEMPERATURE");
    EXPECT_DOUBLE_EQ(dev.TemperatureN[0].min, -50.0);
    EXPECT_DOUBLE_EQ(dev.TemperatureN[0].max, 70.0);
    EXPECT_EQ(dev.TemperatureNP.p, IP_RO);
}

TEST(ArmPlatFocuser, ArmadilloExposesTwoMotorPorts)
{
    ArmPlat dev;
    ASSERT_TRUE(dev.initProperties());
    // indi_armadillo_focus is built with ARMADILLO defined -> two ports only
    EXPECT_EQ(dev.PerPortSP.nsp, 2);
    EXPECT_STREQ(dev.PerPortS[0].name, "Main");
    EXPECT_STREQ(dev.PerPortS[1].name, "Exp");
    EXPECT_EQ(dev.PerPortS[0].s, ISS_ON);
    EXPECT_EQ(dev.PerPortS[1].s, ISS_OFF);
    EXPECT_EQ(dev.PerPortSP.r, ISR_1OFMANY);
}

TEST(ArmPlatFocuser, WiringAndHalfStepOptions)
{
    ArmPlat dev;
    ASSERT_TRUE(dev.initProperties());
    EXPECT_EQ(dev.WiringSP.nsp, 4);
    EXPECT_STREQ(dev.WiringS[0].name, "Lunatico Normal");
    EXPECT_STREQ(dev.WiringS[3].name, "RF/Moonlite Reverse");
    EXPECT_EQ(dev.WiringS[0].s, ISS_ON);
    EXPECT_EQ(dev.HalfStepSP.nsp, 2);
    EXPECT_STREQ(dev.HalfStepS[0].name, "Off");
    EXPECT_STREQ(dev.HalfStepS[1].name, "On");
}
