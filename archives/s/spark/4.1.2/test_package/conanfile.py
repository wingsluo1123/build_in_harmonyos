#!/usr/bin/env python3
"""Conan test_package — Apache Spark 4.1.2.

Runs real Spark CLI checks through the packaged wrapper:
  1. spark-submit --version prints Spark 4.1.2.
  2. spark-submit runs the upstream SparkPi example on local[1].
"""
from __future__ import annotations

import os

from conan import ConanFile


class SparkTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        spark_home = self.dependencies["spark"].package_folder
        spark_submit = os.path.join(spark_home, "bin", "spark-submit")
        examples_jar = os.path.join(
            spark_home, "examples", "jars", "spark-examples_2.13-4.1.2.jar"
        )
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'sh "{test_script}" "{spark_submit}" "{examples_jar}"',
            env="conanrun",
        )
