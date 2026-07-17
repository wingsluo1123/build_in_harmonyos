from conan import ConanFile
import os

class TestConan(ConanFile):
    settings = "os", "arch"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def test(self):
        self.run("python3 -c \"import requests; print(requests.__version__)\"", env="conanrun")