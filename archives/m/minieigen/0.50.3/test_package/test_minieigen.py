#!/usr/bin/env python3
"""Runtime assertions for the packaged minieigen extension."""

import math
import struct
import sysconfig

import minieigen


def check(condition, message):
    if not condition:
        raise AssertionError(message)


suffix = sysconfig.get_config_var("EXT_SUFFIX")
check(suffix == ".cpython-312-aarch64-linux-ohos.so", "target EXT_SUFFIX")
check(minieigen.__file__.endswith(suffix), "imported target ABI filename")

with open(minieigen.__file__, "rb") as stream:
    header = stream.read(20)
check(header[:4] == b"\x7fELF", "extension ELF magic")
check(struct.unpack("<H", header[18:20])[0] == 183, "AArch64 e_machine")

vector = minieigen.Vector3(1, 2, 3)
check(vector.sum() == 6.0, "Vector3 sum")
check(vector.dot(minieigen.Vector3(4, 5, 6)) == 32.0, "Vector3 dot")
check(
    vector.cross(minieigen.Vector3.UnitX) == minieigen.Vector3(0, 3, -2),
    "Vector3 cross",
)
check(minieigen.Vector3.Zero == minieigen.Vector3(0, 0, 0), "Vector3 equality")

matrix = minieigen.Matrix3(1, 2, 3, 0, 1, 4, 5, 6, 0)
check(
    matrix * minieigen.Vector3(1, 0, 0) == minieigen.Vector3(1, 0, 5),
    "matrix-vector product",
)
identity = matrix * matrix.inverse()
check(identity.isApprox(minieigen.Matrix3.Identity, 1e-10), "matrix inverse")

box = minieigen.AlignedBox3((1, 2, 3), (4, 6, 8))
check(box.volume() == 60.0 and box.contains((2, 3, 4)), "aligned box")
rotation = minieigen.Quaternion((0, 0, 1), math.pi / 2)
check(
    (rotation * minieigen.Vector3.UnitX).isApprox(minieigen.Vector3.UnitY, 1e-12),
    "quaternion rotation",
)

print("PASS: 12 minieigen consumer assertions")
