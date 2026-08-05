import os
import tempfile
import site

from conan import ConanFile


class BlackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Find black binary from the dependency's cpp_info
        black_bin = None
        dep = self.dependencies["black"]
        for bindir in dep.cpp_info.bindirs:
            candidate = os.path.join(bindir, "black")
            if os.path.isfile(candidate):
                black_bin = candidate
                break

        # Build PYTHONPATH: package site-packages + system site-packages for runtime deps
        python_paths = []
        for libdir in dep.cpp_info.libdirs:
            if os.path.isdir(libdir):
                python_paths.append(libdir)

        # Add system pip-global path where click, mypy-extensions etc. are installed
        pip_global = os.path.join(os.path.expanduser("~"), ".opendesk", "interpreters", "pip-global")
        if os.path.isdir(pip_global):
            python_paths.append(pip_global)

        # Add system site-packages
        for sp in site.getsitepackages():
            if os.path.isdir(sp):
                python_paths.append(sp)

        if python_paths:
            os.environ["PYTHONPATH"] = os.pathsep.join(python_paths)

        if not os.environ.get("TMPDIR"):
            os.environ["TMPDIR"] = tempfile.gettempdir()

        if not black_bin:
            raise Exception("black binary not found in package")

        # Test 1: Verify black --version works (R34: test must use the package)
        self.run(f"python3 {black_bin} --version")

        # Test 2: Verify black can format Python code
        test_py = os.path.join(self.build_folder, "test_format.py")
        with open(test_py, "w") as f:
            f.write("def foo( x,y ):\n    return  x+y\n")
        self.run(f"python3 {black_bin} {test_py}")

        # Verify the file was reformatted
        with open(test_py, "r") as f:
            formatted = f.read()
        assert "def foo(x, y):" in formatted, f"black did not reformat correctly: {formatted}"
        assert "return x + y" in formatted, f"black did not reformat correctly: {formatted}"
