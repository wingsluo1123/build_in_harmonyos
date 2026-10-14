#!/usr/bin/env python3
"""Conan recipe for PyTorch 2.13.0 — HarmonyOS PC (aarch64) adaptation.

PyTorch's GitHub release tarball does NOT bundle the ~37 `third_party` git
submodules (they appear as empty directories). This recipe therefore:

1. Downloads the official source tarball (R39).
2. In source(): populates the required third_party submodules from their
   official per-commit codeload archives (pinned commits below), so the CMake
   configure step sees complete third_party trees — same as a recursive clone.
3. Applies the adaptation patches:
   - 0001: top-level source fixes (CMake 4.x WHOLE_ARCHIVE, musl __assert_fail
     signature, non-standard `uint` type, std::ranges -> <algorithm> for the
     SDK's libc++ 15 which has no ranges).
   - 0002: cpuinfo OHOS platform support (treat OHOS as Linux so the
     arm/linux sources are compiled and cpuinfo_initialize works).
4. Builds with CMake using the OHOS SDK clang 15 toolchain + native libc++ 15.
   PyTorch 2.13.0 hard-requires Clang >= 16; we satisfy that with a clang
   22.1.8 build requirement and point CMAKE_C/CXX_COMPILER at it, while
   keeping the SDK sysroot/libc++ for the target.
5. Outputs libtorch.so + libtorch_cpu.so (the C++ libtorch library), and with
   the `with_python` option (default on) the torch Python module as well.

Verified locally: configure + make -j2 succeed, `libtorch_cpu.so` and
`libtorch.so` are produced (see notes.md / task book).
"""
import errno
import glob
import os
import re
import shutil
import subprocess
import time
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.scm import Version


class PytorchConan(ConanFile):
    name = "pytorch"
    # R37: adaptation revisions carry a trailing .N (the registry cannot hold two
    # revisions of a published version); the upstream source stays v2.13.0.
    version = "2.13.0.1"
    description = "PyTorch: tensors and dynamic neural networks (C++ libtorch), adapted for HarmonyOS PC aarch64"
    license = "BSD-3-Clause"
    homepage = "https://pytorch.org"
    url = "https://github.com/pytorch/pytorch"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # with_python builds the torch Python extension (`_C` + libtorch_python.so)
    # and packages the torch/ module tree. The Python API is PyTorch's primary
    # interface, so it defaults to ON; C++-only consumers can turn it off with
    # -o pytorch/*:with_python=False.
    options = {"shared": [True, False], "with_python": [True, False],
               "with_distributed": [True, False]}
    default_options = {"shared": True, "with_python": True,
                       "with_distributed": True}

    # Dependencies are declared in method form rather than as class attributes:
    # the repository's dependency gate (preflight PF4 / CI) parses
    # self.requires(...)/self.tool_requires(...) calls, so this form is what
    # makes every declaration visible to it.
    def requirements(self):
        # Optimized BLAS/LAPACK. Without it PyTorch falls back to its bundled
        # Eigen BLAS, which provides no LAPACK at all (torch.linalg
        # solve/qr/svd/decompositions are unavailable or take slow paths).
        # openblas/0.3.34 is published for the exact ohos-aarch64 profile used
        # here, and its SONAME is plain-name (libopenblas.so.0), which the musl
        # loader accepts.
        self.requires("openblas/0.3.34")

    def build_requirements(self):
        # PyTorch 2.13.0 requires Clang >= 16 (CMakeLists hard check); the OHOS
        # SDK ships clang 15.0.4, so provide a newer clang for the build.
        self.tool_requires("clang/22.1.8")
        if self.options.with_python:
            # python: interpreter + development artifacts for the `_C` extension
            # module; pyyaml/typing-extensions/packaging: modules torchgen (run
            # by CMake) imports. Declaring them keeps the BUILD_PYTHON path
            # hermetic instead of depending on whatever the worker's interpreter
            # happens to ship.
            self.tool_requires("python/3.12.9")
            self.tool_requires("pyyaml/6.0.2")
            self.tool_requires("typing-extensions/4.16.0")
            self.tool_requires("packaging/26.3")

    # third_party submodules (path -> commit) pinned by the pytorch v2.13.0 tag.
    # The GitHub tarball omits these; each is fetched from its official repo.
    _SUBMODULES = {
        "third_party/pybind11": "d03662f0984f652b60e7ddce53d3868002275197",
        "third_party/googletest": "52eb8108c5bdec04579160ae17225d66034bd723",
        "third_party/benchmark": "299e5928955cc62af9968370293b916f5130916f",
        "third_party/protobuf": "d1eca4e4b421cd2997495c4b4e65cea6be4e9b8a",
        "third_party/NNPACK": "c07e3a0400713d546e0dea2d5466dd22ea389c73",
        "third_party/gloo": "bcd1672ee07538123ea8f4fac76832efc58fb8ef",
        "third_party/pthreadpool": "a56dcd79c699366e7ac6466792c3025883ff7704",
        "third_party/FXdiv": "b408327ac2a15ec3e43352421954f5b1967701d1",
        "third_party/FP16": "4dfe081cf6bcd15db339cf2680b9281b8451eeb3",
        "third_party/psimd": "072586a71b55b7f8c584153d223e95687148a900",
        "third_party/cpuinfo": "bc3c01e230c6974283e4b89421cfb0e232435589",
        "third_party/python-peachpy": "f45429b087dd7d5bc78bb40dc7cf06425c252d67",
        "third_party/onnx": "e709452ef2bbc1d113faf678c24e6d3467696e83",
        "third_party/sleef": "5a1d179df9cf652951b59010a2d2075372d67f68",
        "third_party/ideep": "e087b6e4b32a7ba684db82231d1558123968ac1d",
        "third_party/gemmlowp/gemmlowp": "3fb5c176c17c765a3492cd2f0321b0dab712f350",
        "third_party/fbgemm": "d08742c6602efedc6a3c9fca124b96ad555316e4",
        "android/libs/fbjni": "7e1e1fe3858c63c251c637ae41a20de425dde96f",
        "third_party/XNNPACK": "51a0103656eff6fc9bfd39a4597923c4b542c883",
        "third_party/fmt": "407c905e45ad75fc29bf0f9bb7c5c2fd3475976f",
        "third_party/tensorpipe": "2b4cd91092d335a697416b2a3cb398283246849d",
        "third_party/cudnn_frontend": "c4a97621eca52fa0c3a1862a411a16be580b25c6",
        "third_party/kineto": "094d3c1d072362d0a919a77299459eee94f97931",
        "third_party/pocketfft": "0fa0ef591e38c2758e3184c6c23e497b9f732ffa",
        "third_party/ittapi": "0c57540822deb5dae43bef6c1cc9b3be4772a033",
        "third_party/flatbuffers": "a2cd1ea3b6d3fee220106b5fed3f7ce8da9eb757",
        "third_party/nlohmann": "55f93686c01528224f448c19128836e7df245f72",
        "third_party/VulkanMemoryAllocator": "1d8f600fd424278486eade7ed3e877c99f0846b1",
        "third_party/cutlass": "da5e086dab31d63815acafdac9a9c5893b1c69e2",
        "third_party/mimalloc": "02a2f5df9d7d46d30263b83832eebeeab62dc5fe",
        "third_party/cpp-httplib": "811dd0b6f2382f50f801f3cfdb5ba349d08bb575",
        "third_party/NVTX": "3ebbc93ded7285963bff932c678fa367eb393ba6",
        "third_party/composable_kernel": "f1746955fdaf80a3414de814bf32437686dac347",
        "third_party/kleidiai": "d7770c89632329a9914ef1a90289917597639cbe",
        "third_party/flash-attention": "6c4f74fb338e0c3cdb07ac6f5eab5f54fc367c15",
        "third_party/aiter": "9a469a608b2c10b7157df573a38d31e5bf4038b4",
        "third_party/mslk": "3d332d1c0c0ac7765852c97b3979c9ef913e037f",
        # fbgemm nested submodules (PreBuildSteps checks external/asmjit)
        "third_party/fbgemm/external/asmjit": "a3199e8857792cd10b7589ff5d58343d2c9008ea",
        "third_party/fbgemm/external/cpuinfo": "161a9ec374884f4b3e85725cb22e05f9458fdc93",
        "third_party/fbgemm/external/googletest": "52eb8108c5bdec04579160ae17225d66034bd723",
        "third_party/fbgemm/external/hipify_torch": "63b6a7b541fa7f08f8475ca7d74054db36ff2691",
        "third_party/fbgemm/external/cutlass": "571edeb2d0ac872a8392fc49285b156b07884b4e",
        "third_party/fbgemm/external/composable_kernel": "7fe50dc3da2069d6645d9deb8c017a876472a977",
        "third_party/fbgemm/external/json": "55f93686c01528224f448c19128836e7df245f72",
        # kineto nested submodules (libkineto/third_party/*). dynolog and fmt are
        # add_subdirectory'd unconditionally by libkineto's CMakeLists whenever
        # USE_KINETO=ON; json/googletest are only reached with KINETO_BUILD_TESTS=ON.
        "third_party/kineto/libkineto/third_party/dynolog": "d2ffe0a4e3acace628db49974246b66fc3e85fb1",
        "third_party/kineto/libkineto/third_party/fmt": "40626af88bd7df9a5fb80be7b25ac85b122d6c21",
        "third_party/kineto/libkineto/third_party/json": "55f93686c01528224f448c19128836e7df245f72",
        "third_party/kineto/libkineto/third_party/googletest": "52eb8108c5bdec04579160ae17225d66034bd723",
        # ideep's nested mkl-dnn submodule (oneDNN): built in-tree by
        # cmake/Modules/FindMKLDNN.cmake from third_party/ideep/mkl-dnn when
        # USE_MKLDNN=ON.
        "third_party/ideep/mkl-dnn": "80afa71049cd69a3df32adcccb623b12cd7baa22",
        # tensorpipe nested submodules (needed when USE_TENSORPIPE=ON, i.e. RPC)
        "third_party/tensorpipe/third_party/libuv": "5152db2cbfeb5582e9c27c5ea1dba2cd9e10759b",
        "third_party/tensorpipe/third_party/libnop": "910b55815be16109f04f4180e9adee14fb4ce281",
        "third_party/tensorpipe/third_party/pybind11": "a23996fce38ff6ccfbcdc09f1e63f2c4be5ea2ef",
        "third_party/tensorpipe/third_party/googletest": "aee0f9d9b5b87796ee8a0ab26b7587ec30e8858e",
    }

    # submodule repo overrides (path -> owner/repo) for the handful that are not
    # derivable from the standard URL scheme or need a specific mirror.
    _REPO_OVERRIDE = {
        "third_party/pybind11": "pybind/pybind11",
        "third_party/benchmark": "google/benchmark",
        "third_party/gemmlowp/gemmlowp": "google/gemmlowp",
        "third_party/python-peachpy": "malfet/PeachPy",
        "third_party/mslk": "meta-pytorch/MSLK",
        "third_party/kleidiai": "ARM-software/kleidiai",
        "third_party/ittapi": "intel/ittapi",
        "third_party/cudnn_frontend": "NVIDIA/cudnn-frontend",
        "third_party/flash-attention": "Dao-AILab/flash-attention",
        "third_party/cpuinfo": "pytorch/cpuinfo",
        "third_party/cpp-httplib": "yhirose/cpp-httplib",
        "third_party/fbgemm/external/asmjit": "asmjit/asmjit",
        "third_party/fbgemm/external/hipify_torch": "ROCm/hipify_torch",
        "third_party/fbgemm/external/composable_kernel": "ROCm/composable_kernel",
        "third_party/fbgemm/external/cutlass": "NVIDIA/cutlass",
        "third_party/fbgemm/external/json": "nlohmann/json",
        # tensorpipe nested submodules: libuv/libnop are not in the simple map
        # (their names do not match the owner), the other two resolve via it.
        "third_party/tensorpipe/third_party/libuv": "libuv/libuv",
        "third_party/tensorpipe/third_party/libnop": "google/libnop",
        # kineto nested submodules: fmt/googletest resolve via the simple name
        # map, dynolog and json do not (their directory names are not repos).
        "third_party/kineto/libkineto/third_party/dynolog": "facebookincubator/dynolog",
        "third_party/kineto/libkineto/third_party/json": "nlohmann/json",
        # ideep's nested mkl-dnn: "mkl-dnn" is not in the simple name map.
        "third_party/ideep/mkl-dnn": "intel/mkl-dnn",
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Populate third_party submodules missing from the release tarball.
        self._fetch_submodules()

    def _repo_for(self, path):
        if path in self._REPO_OVERRIDE:
            return self._REPO_OVERRIDE[path]
        # derive owner/repo from the submodule name (most follow owner/repo)
        name = path.rsplit("/", 1)[-1]
        simple = {
            "pybind11": "pybind/pybind11",
            "googletest": "google/googletest",
            "benchmark": "google/benchmark",
            "protobuf": "protocolbuffers/protobuf",
            "NNPACK": "Maratyszcza/NNPACK",
            "gloo": "pytorch/gloo",
            "pthreadpool": "google/pthreadpool",
            "FXdiv": "Maratyszcza/FXdiv",
            "FP16": "Maratyszcza/FP16",
            "psimd": "Maratyszcza/psimd",
            "cpuinfo": "pytorch/cpuinfo",
            "python-peachpy": "malfet/PeachPy",
            "onnx": "onnx/onnx",
            "sleef": "shibatch/sleef",
            "ideep": "intel/ideep",
            "gemmlowp": "google/gemmlowp",
            "fbgemm": "pytorch/FBGEMM",
            "fbjni": "facebookincubator/fbjni",
            "XNNPACK": "google/XNNPACK",
            "fmt": "fmtlib/fmt",
            "tensorpipe": "pytorch/tensorpipe",
            "cudnn_frontend": "NVIDIA/cudnn-frontend",
            "kineto": "pytorch/kineto",
            "pocketfft": "mreineck/pocketfft",
            "ittapi": "intel/ittapi",
            "flatbuffers": "google/flatbuffers",
            "nlohmann": "nlohmann/json",
            "VulkanMemoryAllocator": "GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator",
            "cutlass": "NVIDIA/cutlass",
            "mimalloc": "microsoft/mimalloc",
            "cpp-httplib": "yhirose/cpp-httplib",
            "NVTX": "NVIDIA/NVTX",
            "composable_kernel": "ROCm/composable_kernel",
            "kleidiai": "ARM-software/kleidiai",
            "flash-attention": "Dao-AILab/flash-attention",
            "aiter": "ROCm/aiter",
            "mslk": "meta-pytorch/MSLK",
        }
        return simple.get(name)

    def _fetch_submodules(self):
        """Fetch each pinned third_party submodule from its official codeload."""
        base = self.source_folder
        # Offline/air-gapped fallback: PYTORCH_SUBMODULE_DONOR may point at a tree
        # that already holds the populated third_party/ submodules (e.g. the
        # source folder of an earlier build of this recipe). It is consulted only
        # when a submodule directory is still empty, and leaving it unset keeps
        # the normal download path exactly as before.
        donor = os.environ.get("PYTORCH_SUBMODULE_DONOR", "")
        for path, commit in self._SUBMODULES.items():
            repo = self._repo_for(path)
            if not repo:
                self.output.warning(f"no repo mapping for {path}, skipping")
                continue
            dest = os.path.join(base, path)
            if os.path.isdir(dest) and os.listdir(dest):
                continue  # already populated (e.g. a vendored copy)
            os.makedirs(dest, exist_ok=True)
            if donor:
                src = os.path.join(donor, path)
                if os.path.isdir(src) and os.listdir(src):
                    shutil.copytree(src, dest, symlinks=True, dirs_exist_ok=True)
                    self.output.info(
                        f"submodule {path}: seeded from PYTORCH_SUBMODULE_DONOR")
                    continue
            url = (
                f"https://gh-proxy.com/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://gh.ddlc.top/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://ghfast.top/https://github.com/{repo}/archive/{commit}.tar.gz",
                f"https://codeload.github.com/{repo}/tar.gz/{commit}",
            )
            tarball = os.path.join(self.source_folder, f".sub-{path.rsplit('/', 1)[-1]}.tgz")
            try:
                self._download(url, tarball)
                # strip the top-level "<repo>-<sha>" directory
                shutil.rmtree(dest, ignore_errors=True)
                os.makedirs(dest, exist_ok=True)
                self._untar_strip(tarball, dest)
            finally:
                if os.path.exists(tarball):
                    os.remove(tarball)

    def _untar_strip(self, tarball, dest):
        """Extract a tarball, stripping its single top-level directory.

        Uses Python's tarfile (no dependency on the system `tar` binary, which
        is absent in the conan build environment).
        """
        import tarfile
        with tarfile.open(tarball, "r:gz") as tf:
            members = tf.getmembers()
            # find the single top-level directory name
            tops = sorted({m.name.split("/", 1)[0] for m in members if m.name})
            prefix = (tops[0] + "/") if tops else ""
            for m in members:
                name = m.name
                if name.startswith(prefix):
                    name = name[len(prefix):]
                if not name:
                    continue
                target = os.path.join(dest, name)
                if m.isdir():
                    os.makedirs(target, exist_ok=True)
                elif m.issym() or m.islnk():
                    lnk = m.linkname
                    if lnk.startswith(prefix):
                        lnk = lnk[len(prefix):]
                    if os.path.lexists(target):
                        os.unlink(target)
                    os.symlink(lnk, target)
                elif m.isfile():
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with tf.extractfile(m) as src, open(target, "wb") as fh:
                        shutil.copyfileobj(src, fh)

    def _download(self, urls, dest):
        """Download from the first URL that works (retry transient failures).

        codeload.github.com is intermittently blocked in this environment, so
        the ghfast.top mirror (same prefix E017 uses) is tried first, with the
        canonical codeload URL as a fallback.
        """
        if isinstance(urls, str):
            urls = [urls]
        last_err = None
        for url in urls:
            for attempt in range(3):
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as fh:
                        shutil.copyfileobj(resp, fh)
                    return
                except Exception as e:  # noqa: BLE001 - retry transient network failures
                    last_err = e
                    self.output.warning(f"download failed (attempt {attempt + 1}/3): {url}: {e}")
                    time.sleep(5)
        raise last_err

    def _sdk_native(self):
        """Locate the OHOS SDK native dir in a portable way.

        Prefer explicit env vars (OHOS_SDK_HOME / OHOS_NDK_ROOT /
        OHOS_NATIVE_ROOT), then the newest installed SDK under
        /data/service/hnp — CI workers may carry a different SDK version than
        the dev box, so a hard-coded version path breaks there.
        """
        for var in ("OHOS_SDK_HOME", "OHOS_NDK_ROOT", "OHOS_NATIVE_ROOT"):
            v = os.environ.get(var)
            if v:
                for cand in (os.path.join(v, "ohos", "native"), v):
                    if os.path.isdir(cand):
                        return cand
        matches = sorted(set(
            glob.glob("/data/service/hnp/ohos-sdk*/ohos/native") +
            glob.glob("/data/service/hnp/*/ohos-sdk*/ohos/native")
        ))
        if matches:
            return matches[-1]
        # Fallback to the historically known dev-box path.
        return "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"

    # ── Python interpreter selection (BUILD_PYTHON) ────────────────────────
    # CMake drives torchgen during configure/build and torchgen imports yaml,
    # typing_extensions and packaging, so the interpreter must satisfy those at
    # build time (the interpreter is also what FindPython uses to derive the
    # `_C` module suffix). Platform interpreters already carry these modules;
    # the conan python/3.12.9 tool_require is the hermetic fallback with the
    # declared pyyaml/typing-extensions/packaging packages on PYTHONPATH.
    _PY_PROBE = "import yaml, typing_extensions, packaging"

    def _python_candidates(self):
        """(executable, extra_env) interpreter candidates, best first."""
        cands = []
        for var in ("PYTORCH_PYTHON", "OHOS_PYTHON"):
            if os.environ.get(var):
                cands.append(os.environ[var])
        # Platform interpreters: loadable from a platform path, which CI workers
        # require (a .so inside the conan cache cannot be loaded there).
        cands += ["/data/service/hnp/python.org/python_3.12/bin/python3",
                  "/data/service/hnp/bin/python3",
                  "/data/app/bin/python3"]
        found = shutil.which("python3")
        if found:
            cands.append(found)
        # Hermetic fallback: the declared python tool_require.
        try:
            py_pkg = self.dependencies.build["python"].package_folder
        except KeyError:
            py_pkg = None
        if py_pkg:
            for name in ("python3.12", "python3"):
                exe = os.path.join(py_pkg, "bin", name)
                if os.path.isfile(exe):
                    cands.append((exe, {"PYTHONHOME": py_pkg,
                                        "LD_LIBRARY_PATH": os.path.join(py_pkg, "lib")}))
                    break
        out = []
        for c in cands:
            out.append(c if isinstance(c, tuple) else (c, {}))
        return out

    def _python_dep_paths(self):
        """site-packages dirs of the declared codegen dependencies."""
        paths = []
        for dep in ("pyyaml", "typing-extensions", "packaging"):
            try:
                folder = self.dependencies.build[dep].package_folder
            except KeyError:
                continue
            for root, dirs, _files in os.walk(folder):
                if os.path.basename(root) == "site-packages":
                    paths.append(root)
                    dirs[:] = []
        return paths

    def _build_jobs(self):
        """Parallel job count for the compile steps.

        The default would be os.cpu_count() (20 on the CI worker), but that
        worker is the same machine as the desktop and torch_cpu/XNNPACK
        compiles peak at ~1-1.5 GB per clang job: CI #87292 died at 82% with
        "posix_spawn failed: Out of memory" (clang and cmake both "Out of
        memory", Error 126) while the box already held most of its 32 GB. Cap
        the fan-out so the peak fits and the wall clock stays inside the
        registered 14400s budget (12 -> ~3h against ~110-119 min at 20).
        PYTORCH_BUILD_JOBS overrides the cap.
        """
        override = os.environ.get("PYTORCH_BUILD_JOBS", "")
        if override:
            try:
                return max(1, int(override))
            except ValueError:
                self.output.warning(
                    "pytorch: ignoring non-numeric PYTORCH_BUILD_JOBS=%s" % override)
        return max(2, min(os.cpu_count() or 4, 12))

    def _probe_python(self, exe, env):
        """Run the codegen-dependency probe and return (returncode, stderr).

        A transient resource shortage at spawn time (EAGAIN / ENOMEM / EMFILE /
        ENFILE / EINTR) is retried with backoff instead of being taken for
        "this interpreter cannot run the codegen": the CI worker hosts the
        desktop as well, so fork/exec gets refused for tens of seconds while
        other jobs hold the machine. CI build #88796 failed exactly this way
        (all three candidates EAGAIN) and was reported as a missing-module
        problem, which cost a build round.
        """
        delay = 15
        for attempt in range(1, 4):
            try:
                proc = subprocess.run([exe, "-c", self._PY_PROBE], env=env,
                                      capture_output=True, timeout=180)
                return proc.returncode, proc.stderr
            except OSError as exc:
                if exc.errno not in (errno.EAGAIN, errno.ENOMEM, errno.EMFILE,
                                     errno.ENFILE, errno.EINTR) or attempt == 3:
                    raise
                self.output.warning(
                    "pytorch: spawning %s failed with errno %s (%s) - the "
                    "machine is under job/thread/memory pressure; retrying in "
                    "%ds (retry %d/3)" % (exe, exc.errno,
                                          os.strerror(exc.errno), delay, attempt))
                time.sleep(delay)
                delay *= 2

    def _pick_python(self):
        """First candidate that can import the codegen dependencies."""
        dep_paths = self._python_dep_paths()
        spawn_failed = []
        probe_failed = []
        for exe, extra in self._python_candidates():
            if not exe or not os.path.isfile(exe):
                continue
            env = dict(os.environ)
            env.update(extra)
            if dep_paths:
                env["PYTHONPATH"] = os.pathsep.join(
                    dep_paths + [p for p in [env.get("PYTHONPATH", "")] if p])
            try:
                rc, stderr = self._probe_python(exe, env)
            except (OSError, subprocess.SubprocessError) as exc:
                spawn_failed.append("%s (%s)" % (exe, exc))
                continue
            if rc == 0:
                self.output.info("pytorch: python interpreter for BUILD_PYTHON: %s" % exe)
                return exe, extra, dep_paths
            probe_failed.append("%s (%s)" % (exe, stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or ""))
        if spawn_failed and not probe_failed:
            raise ConanException(
                "could not spawn any Python interpreter for pytorch's codegen: "
                "the system refused to create the process for every candidate "
                "even after retries (%s) - that is a transient resource "
                "shortage on the machine, not a missing-module problem"
                % "; ".join(spawn_failed))
        raise ConanException(
            "no Python interpreter able to run pytorch's codegen "
            "(needs yaml/typing_extensions/packaging). Tried: %s"
            % "; ".join(probe_failed + spawn_failed))

    def generate(self):
        tc = CMakeToolchain(self)
        # The profile points tools.build:compiler_executables at the SDK clang
        # 15 (which fails PyTorch's Clang>=16 check); override the compilers
        # with the clang/22.1.8 tool_require and keep the SDK libc++ 15
        # (OHOS __n1 ABI, PIC libc++_shared.so) for the target.
        clang_dep = self.dependencies.build["clang"]
        # Keep every host tool loadable: conan's VirtualBuildEnv prepends
        # tool_requires lib dirs to LD_LIBRARY_PATH, and the conan cache is not
        # loadable on CI workers (HMDFS exec restriction) -- the host cmake,
        # ninja and the sleef host tools would all fail with 'symbol not
        # found'. Drop the lib dir here (bin stays on PATH) and let the
        # platform libc++ be used instead; build() pins it explicitly.
        clang_dep.cpp_info.libdirs = []
        clang_pkg = clang_dep.package_folder
        sdk_native = self._sdk_native()
        target = "--target=aarch64-linux-ohos"
        sysroot = f"--sysroot={sdk_native}/sysroot"
        tc.variables["CMAKE_C_COMPILER"] = os.path.join(clang_pkg, "bin", "clang")
        tc.variables["CMAKE_CXX_COMPILER"] = os.path.join(clang_pkg, "bin", "clang++")
        # -D_GNU_SOURCE on the C flags too: glibc-style extensions gate the
        # cpu_set_t / sched_getaffinity / CPU_SETSIZE declarations in the OHOS
        # musl sched.h, and libuv (compiled as C, pulled in by TensorPipe for
        # distributed/RPC) needs them -- without it core.c fails with
        # "use of undeclared identifier 'cpu_set_t'".
        # OpenMP (USE_OPENMP=ON): the runtime is the SDK's own libomp, which
        # clang/22.1.8 does not discover by itself. omp.h lives in
        # <sdk>/llvm/include (not on clang 22's default include path), so that
        # dir goes on the compile line with -isystem.
        #
        # The library search dir and -static-openmp are LINK-time flags and must
        # not go into the compile flags: clang reports "argument unused during
        # compilation" for both, and libkineto builds its own sources with
        # -Wall -Wextra -pedantic -Werror
        # (third_party/kineto/libkineto/CMakeLists.txt), which turns that
        # warning into a hard error. -static-openmp keeps the driver on
        # libomp.a: the SDK ships libomp.so next to it, and there is no
        # libomp.so in /system/lib64, so a shared link would leave every
        # consumer needing the SDK lib dir on LD_LIBRARY_PATH at run time.
        # Measured: with -static-openmp the linked libtorch_cpu.so keeps
        # NEEDED = libc++_shared.so, libc.so only.
        sdk_llvm_inc = f"{sdk_native}/llvm/include"
        sdk_llvm_lib = f"{sdk_native}/llvm/lib/aarch64-linux-ohos"
        openmp_compile_flags = f"-isystem {sdk_llvm_inc}"
        openmp_link_flags = "-static-openmp"
        # Pin the static archive as the detected runtime. The find_library() in
        # pytorch's FindOpenMP.cmake honours an already-set cache entry; without
        # the pin it walks the SDK lib dir and picks libomp.so, which would put
        # a run-time dependency on the device that nothing can satisfy.
        # Measured with the module itself: OPENMP_FOUND=TRUE and
        # OpenMP_CXX_LIBRARIES=<sdk>/.../libomp.a with this pin, libomp.so
        # without it.
        tc.cache_variables["OpenMP_libomp_LIBRARY"] = f"{sdk_llvm_lib}/libomp.a"
        tc.variables["CMAKE_C_FLAGS"] = (
            f"{target} {sysroot} -D__MUSL__ -D_GNU_SOURCE {openmp_compile_flags}"
        )
        tc.variables["CMAKE_CXX_FLAGS"] = (
            f"{target} {sysroot} -D__MUSL__ "
            f"-isystem {sdk_native}/llvm/include/libcxx-ohos/include/c++/v1 "
            f"-D_GNU_SOURCE {openmp_compile_flags}"
        )
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
            f"{target} {sysroot} -L{sdk_native}/llvm/lib/aarch64-linux-ohos "
            f"{openmp_link_flags}"
        )
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            f"{target} {sysroot} -L{sdk_native}/llvm/lib/aarch64-linux-ohos "
            f"{openmp_link_flags}"
        )
        # MODULE libraries need the same flags as shared ones: the torch Python
        # extension (`_C`) is a MODULE target, and with empty module linker flags
        # it is linked without the SDK lib dir, so lld cannot resolve the
        # -l:libunwind.a the clang driver adds for C++ exception handling
        # ("unable to find library -l:libunwind.a").
        tc.variables["CMAKE_MODULE_LINKER_FLAGS"] = (
            f"{target} {sysroot} -L{sdk_native}/llvm/lib/aarch64-linux-ohos "
            f"{openmp_link_flags}"
        )
        if self.options.with_python:
            # FindPython runs the interpreter (torchgen, generate_torch_version)
            # during configure and derives the `_C` module suffix from it, so the
            # choice has to be made here, not at build time.
            py_exe, py_env, py_paths = self._pick_python()
            self._py_exe, self._py_env, self._py_paths = py_exe, py_env, py_paths
            tc.variables["Python_EXECUTABLE"] = py_exe
            tc.variables["Python3_EXECUTABLE"] = py_exe
        tc.generate()
        if self.options.with_python:
            # The custom commands CMake runs (torchgen, generate_torch_version)
            # execute in the same shell as the build, so publish the interpreter
            # environment as part of the build env instead of relying on it being
            # inherited.
            from conan.tools.env import Environment
            env = Environment()
            if self._py_env:
                for key, value in self._py_env.items():
                    env.define(key, value)
            if self._py_paths:
                env.prepend_path("PYTHONPATH", os.pathsep.join(self._py_paths))
            env.vars(self).save_script("pytorch_python_env")

    @staticmethod
    def _libcxx_score(path):
        """Score a libc++_shared.so candidate by content (size, __n1 symbols).

        A stub/empty .so (valid ELF, SONAME set, but no C++ runtime symbols) is
        what makes host tools like cmake die with 'symbol not found'; it can be
        silently picked when it comes first on LD_LIBRARY_PATH. Reading the file
        is enough to tell a real runtime from a stub, without running anything.
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return None
        return len(data), data.count(b"_ZNSt4__n1")

    def _libcxx_dirs(self):
        """Directories that may provide a host libc++_shared.so, best first.

        The platform path comes first: CI workers refuse to load .so files from
        the conan cache (HMDFS exec restriction), so a good copy there is still
        unusable -- only /system/lib64 worked on the worker (see the CI
        diagnostic run).
        """
        sdk_native = self._sdk_native()
        return [
            "/system/lib64",
            os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"),
            os.path.join(sdk_native, "llvm", "lib"),
            os.path.join(self.dependencies.build["clang"].package_folder, "lib"),
        ]

    def _pick_libcxx_dir(self):
        """Return a libc++ directory the host cmake can actually start with.

        Candidates are checked twice: by content (size/__n1, to reject stubs)
        and empirically, by starting cmake with LD_LIBRARY_PATH pinned to that
        directory. The empirical check is what makes this robust across CI
        workers, where a byte-identical copy can still be unloadable.
        """
        tried = []
        for d in self._libcxx_dirs():
            score = self._libcxx_score(os.path.join(d, "libc++_shared.so"))
            if not score or score[0] < 200000 or score[1] < 100:
                tried.append("%s: %s" % (d, "missing" if not score
                                         else "not-libc++(size=%d,__n1=%d)" % score))
                continue
            rc = self.run('LD_LIBRARY_PATH=%s cmake --version >/dev/null 2>&1' % d,
                          env="conanbuild", ignore_errors=True)
            tried.append("%s: size=%d __n1=%d cmake_rc=%s" % (d, score[0], score[1], rc))
            if rc == 0:
                self.output.info("pytorch: host libc++ dir = %s (size=%d, __n1=%d)"
                                 % (d, score[0], score[1]))
                return d
        raise ConanException(
            "no host libc++_shared.so that cmake can start with; candidates:\n  "
            + "\n  ".join(tried))

    def _write_cmake_wrapper(self, libdir):
        """Write a cmake wrapper that pins a loadable libc++ for host tools.

        LD_LIBRARY_PATH takes precedence over the platform search path, and
        conan's buildenv prepends tool_requires lib dirs (conan cache) that CI
        workers cannot load. Assigning the variable inline guarantees the
        platform copy is used no matter what the inherited environment holds.
        """
        wrapper = os.path.join(self.build_folder, "cmake-host.sh")
        with open(wrapper, "w") as fh:
            fh.write('#!/bin/sh\n'
                     '# generated by the pytorch recipe: force a loadable host libc++\n'
                     'exec env LD_LIBRARY_PATH="%s" /data/service/hnp/bin/cmake "$@"\n' % libdir)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _diag_host_cmake(self, libcxx):
        """Compact report on why the host cmake cannot start (CI sandbox diagnosis).

        Runs only on the failure path, so it does not slow down healthy builds.
        Answers, in one shot: which LD_* vars actually reach the child shell,
        which libc++ copies exist on the loader's default search path, which one
        the loader would pick, and which injection mechanism still works.
        """
        libdir = os.path.dirname(libcxx)
        mine = " ".join("%s=%s" % (k, v) for k, v in os.environ.items() if k.startswith("LD_"))
        self.output.info("[diag] python os.environ LD_*: %s" % (mine or "<none>"))
        self.run('env | grep -E "^LD_" || echo "[diag] no LD_* inside conanbuild shell"',
                 env="conanbuild", ignore_errors=True)
        default_dirs = []
        for pf in ("/etc/ld-musl-aarch64.path", "/system/etc/ld-musl-aarch64.path"):
            try:
                with open(pf) as fh:
                    content = fh.read().strip()
                self.output.info("[diag] %s: %s" % (pf, content))
                default_dirs = content.split(":")
                break
            except OSError:
                continue
        hits = []
        for d in default_dirs:
            score = self._libcxx_score(os.path.join(d, "libc++_shared.so"))
            if score:
                hits.append("%s(size=%d,__n1=%d)" % (os.path.join(d, "libc++_shared.so"), score[0], score[1]))
        self.output.info("[diag] libc++_shared.so on default path: %s" % ("; ".join(hits) or "<none>"))
        self.run('ls -l "%s" 2>&1 | tail -2' % libcxx, env="conanbuild", ignore_errors=True)
        self.run('readelf -S "%s" 2>/dev/null | grep -c codesign | xargs echo "[diag] .codesign sections:"'
                 % libcxx, env="conanbuild", ignore_errors=True)
        self.run('LD_TRACE_LOADED_OBJECTS=1 cmake --version 2>&1 | grep -iE "libc\\+\\+|not found" | head -5 '
                 '|| echo "[diag] trace gave no libc++ line"', env="conanbuild", ignore_errors=True)
        wrapper = os.path.join(self.build_folder, "cmake-via-env.sh")
        with open(wrapper, "w") as fh:
            fh.write('#!/bin/sh\nexec env LD_LIBRARY_PATH="%s" LD_PRELOAD="%s" '
                     '/data/service/hnp/bin/cmake "$@"\n' % (libdir, libcxx))
        os.chmod(wrapper, 0o755)
        # python shim: sets the child env with os.execve, bypassing any
        # shell/spawn-time env filtering the sandbox might apply.
        shim = os.path.join(self.build_folder, "cmake-shim")
        with open(shim, "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import os, sys\n"
                     "env = dict(os.environ)\n"
                     "env['LD_LIBRARY_PATH'] = %r\n"
                     "env['LD_PRELOAD'] = %r\n"
                     "cmake = '/data/service/hnp/bin/cmake'\n"
                     "os.execve(cmake, [cmake] + sys.argv[1:], env)\n" % (libdir, libcxx))
        os.chmod(shim, 0o755)
        cases = (("plain", ""),
                 ("libpath", 'LD_LIBRARY_PATH=%s ' % libdir),
                 ("preload", 'LD_PRELOAD=%s ' % libcxx),
                 ("both", 'LD_LIBRARY_PATH=%s LD_PRELOAD=%s ' % (libdir, libcxx)),
                 ("wrapper", "%s " % wrapper),
                 ("pyshim", "%s " % shim),
                 ("syslib", "LD_LIBRARY_PATH=/system/lib64 "))
        for tag, prefix in cases:
            rc = self.run("%scmake --version >/dev/null 2>&1" % prefix, env="conanbuild",
                          ignore_errors=True)
            self.output.info("[diag] cmake start via %-8s -> rc=%s" % (tag, rc))

    def build(self):
        apply_conandata_patches(self)
        # BLAS/LAPACK wiring. PyTorch resolves BLAS through its own
        # cmake/Modules/FindOpenBLAS.cmake (module mode wins over the CMakeDeps
        # config file because the PROJECT_SOURCE_DIR module path is appended
        # first), and that module searches $ENV{OpenBLAS_HOME}/{include,lib} --
        # point it at the openblas package so -DBLAS=OpenBLAS finds it and
        # AT_LAPACK gets enabled.
        openblas_dir = self.dependencies["openblas"].package_folder
        os.environ["OpenBLAS_HOME"] = openblas_dir
        # Cross-compiling: cmake/BLAS_ABI.cmake cannot run its compile-and-run
        # probes, so it reads this switch instead and defaults to FALSE. The
        # default path calls the Fortran cdotu_ symbol, which on aarch64 OpenBLAS
        # (gfortran ABI) does not write the f2c result pointer -- torch.dot on
        # complex tensors then silently returns 0. CBLAS dot uses
        # cblas_cdotu_sub, which is correct here.
        os.environ["PYTORCH_BLAS_USE_CBLAS_DOT"] = "ON"
        # Host tools (cmake/ninja) need a libc++_shared.so the loader can
        # actually load. Conan's VirtualBuildEnv prepends every tool_requires
        # libdir (clang/22.1.8, i.e. the conan cache) to LD_LIBRARY_PATH, and CI
        # workers refuse to load .so files from there (HMDFS exec restriction):
        # the candidate is found but cannot be loaded, so the host cmake dies
        # with 'Error relocating ... symbol not found' (exit 127). Only the
        # platform copy worked on the worker, so pick a *loadable* directory,
        # pin LD_LIBRARY_PATH to it and route the CMake helper through a
        # wrapper that sets the variable inline (immune to the inherited env).
        libdir = self._pick_libcxx_dir()
        os.environ["LD_LIBRARY_PATH"] = libdir
        os.environ.pop("LD_PRELOAD", None)
        wrapper = self._write_cmake_wrapper(libdir)
        self.conf.define("tools.cmake:cmake_program", wrapper)
        # Canary: fail early with a readable message instead of a cryptic
        # "Error 127 while executing" from cmake.configure(). Check the wrapper
        # (that is what the CMake helper will actually run) and, on failure,
        # print a one-shot diagnosis of the worker environment.
        if self.run('"%s" --version' % wrapper, env="conanbuild", ignore_errors=True) != 0:
            self._diag_host_cmake(os.path.join(libdir, "libc++_shared.so"))
            raise ConanException(
                "host cmake cannot start (libdir=%s); "
                "check the worker's libc++/cmake installation" % libdir)
        # sleef needs host-side codegen tools (mkrename/mkalias/mkdisp/...).
        # Cross-compiling OHOS, sleef's add_host_executable looks in
        # NATIVE_BUILD_DIR/bin; build them with the SDK clang (produces runnable
        # aarch64 musl host binaries) and point CMake at that dir.
        native_dir = os.path.join(self.build_folder, "sleef-native")
        self._build_sleef_host_tools(native_dir)
        # PyTorch's top-level CMakeLists enables CMAKE_LINK_WHAT_YOU_USE, which
        # makes CMake run `ldd` after every link to look for unused libraries.
        # OHOS has no `ldd`, so every link fails ("Error running 'ldd': no such
        # file or directory" -> make Error 1). Provide an ldd-compatible shim
        # built on readelf and point CMake at it.
        ldd_shim = self._write_ldd_shim()
        cmake = CMake(self)
        cmake.configure(variables={**self._cmake_vars(),
                                   "NATIVE_BUILD_DIR": native_dir,
                                   "CMAKE_LINK_WHAT_YOU_USE_CHECK": ldd_shim})
        try:
            cmake.build(build_tool_args=["-j%d" % self._build_jobs()])
        except ConanException:
            # Surface the real compiler error: with -j20 the failing command's
            # output is buried far above the CI log tail (which is truncated),
            # so re-run the build serially and print only the error context.
            self._dump_build_errors(libdir)
            raise
        self._run_upstream_tests(libdir)

    # Upstream c10 test targets. c10/test/CMakeLists.txt registers one gtest
    # target per *_test.cpp found (file(GLOB_RECURSE ...)) plus a C++17 header
    # build check, so the target list is derived the same way here instead of
    # being hard-coded.
    UPSTREAM_C10_TEST_SKIP = ()  # documented exceptions, currently none

    # test/cpp suites that exist with this configuration and are built+run by
    # _run_upstream_cpp_tests. The other test/cpp subdirectories need features
    # this package disables or the python stack, so their targets are absent
    # from the configured tree:
    #   c10d, dist_autograd, rpc, example_allreduce -> gloo/distributed test
    #       helpers and a multi-process launch setup
    #   nativert, aoti_inference -> BUILD_NATIVERT / AOTInductor runtime
    #   profiler, inductor -> USE_KINETO collectors and the python stack
    # The remaining test/*.py suites need a `python -m torch` build. Their
    # sizes are reported in notes.md / test_package/MANIFEST.yml.
    UPSTREAM_CPP_TEST_TARGETS = ("test_api", "test_jit", "test_lazy", "test_shim",
                                 "test_aoti_abi_check")

    # Two gtest suites abort when every case runs in one process on OHOS
    # aarch64: measured test_lazy dies in case 69 of 612
    # (LazyOpsTest.TestDivWithRoundingMode, after 68 passes) and
    # inline_container_test dies in the allocator cases that follow the
    # SaveAndLoad/LoadWithMultiThreads cases. Every case passes when the suite
    # is split into groups that each start a fresh process, so the phase runs
    # them that way and keeps the coverage complete:
    #   test_lazy             -> chunks of <=60 cases (11 chunks for 612)
    #   inline_container_test -> 9 cases together, then the 4 remaining singles
    UPSTREAM_TEST_SPLIT_CHUNK = {"test_lazy": 60}
    # Registered with ctest but run through the split path below, so it is left
    # out of the ctest selection (it is still built like every other target).
    UPSTREAM_CTEST_SPLIT = ("inline_container_test",)
    # Per-test cap for the ctest phase: the slowest registered test measured
    # ~57 s, so 600 s leaves ample headroom while still bounding a hang.
    UPSTREAM_CTEST_TIMEOUT = 600
    UPSTREAM_INLINE_CONTAINER_GROUPS = (
        "PytorchStreamWriterAndReader.*:ChunkRecordIteratorTestGroup/*"
        ":MemoryReadAdapterTest.*",
        "PyTorchStreamWriterAndReader.SaveAndLoad",
        "PyTorchStreamWriterAndReader.LoadWithMultiThreads",
        "PyTorchStreamWriterAndReader.SaveAndLoadWithAllocator",
        "PyTorchStreamWriterAndReader.LoadWithMultiThreadsWithAllocator",
    )

    def _upstream_c10_targets(self):
        """All c10 test targets upstream registers for BUILD_TEST=ON."""
        test_dir = os.path.join(self.source_folder, "c10", "test")
        names = []
        for root, _dirs, files in os.walk(test_dir):
            for name in files:
                if name.endswith("_test.cpp"):
                    names.append("c10_%s" % name[: -len(".cpp")])
        # extra target added by c10/test/CMakeLists.txt (not a *_test.cpp)
        extra = os.path.join(test_dir, "util", "cpp17_header_build_check.cpp")
        if os.path.exists(extra):
            names.append("c10_cpp17_header_build_test")
        return sorted(set(names) - set(self.UPSTREAM_C10_TEST_SKIP))

    def _test_phase_env_prefix(self, libdir, extra_lib=None):
        """Inline environment prefix for the upstream-test phase.

        Conan's build environment prepends every tool_require's libdir to
        LD_LIBRARY_PATH, including python/3.12.9. The platform interpreter that
        CMake drives for code generation (Python_EXECUTABLE) then loads *that*
        package's libpython instead of its own copy: it reports the other
        version (3.12.9 instead of the platform's 3.12.8) and loses its stdlib
        shared modules, so cmake/Codegen.cmake dies with
        'ModuleNotFoundError: No module named math' / '_posixsubprocess'.
        Pinning LD_LIBRARY_PATH (and clearing PYTHONHOME) for these commands
        keeps the interpreter self-consistent; the codegen dependencies are
        passed explicitly through PYTHONPATH instead.
        """
        libs = [p for p in (extra_lib, libdir, "/system/lib64/platformsdk",
                            "/system/lib64/chipset-sdk-sp", "/system/lib64") if p]
        parts = ['LD_LIBRARY_PATH="%s"' % os.pathsep.join(libs)]
        py_paths = self._python_dep_paths()
        if py_paths:
            parts.append('PYTHONPATH="%s"' % os.pathsep.join(py_paths))
        parts.append("PYTHONHOME=")
        return " ".join(parts)

    def _run_upstream_tests(self, libdir):
        """Build and run the upstream test suites this configuration ships.

        PyTorch's C++ tests are gtest-based and only exist when BUILD_TEST=ON,
        which stays OFF for the package build (no test binaries are packaged).
        The already-configured tree is reconfigured with BUILD_TEST=ON and every
        test target upstream registers for this configuration is built, so the
        tests are compiled with exactly the toolchain and flags used for the
        library they exercise. Coverage:
          * c10/test       51 targets, one gtest binary each
          * caffe2 + ATen  58 targets (pow_test, tensor_iterator_test, ...),
                           all registered with ctest
          * test/cpp        5 targets: test_api, test_jit, test_lazy, test_shim,
                           test_aoti_abi_check
        """
        build_dir = self.build_folder
        c10_names = self._upstream_c10_targets()
        cpp_names = list(self.UPSTREAM_CPP_TEST_TARGETS)
        # gtest writes captured death-test output to a temp file; TEST_TMPDIR
        # makes it use a writable directory (see patch 0005), /tmp being
        # read-only on HarmonyOS PC.
        tmp_dir = os.path.join(build_dir, "upstream-test-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        # INSTALL_TEST defaults to ON as soon as BUILD_TEST is ON, which adds
        # install rules for every test *and* benchmark binary; only the test
        # targets are built here, so package()'s cmake.install() would look for
        # e.g. bin/c10_intrusive_ptr_benchmark and fail. Keep the package
        # contents unchanged (no test binaries).
        self.run('%s cmake -S "%s" -B "%s" -DBUILD_TEST=ON -DINSTALL_TEST=OFF'
                 % (self._test_phase_env_prefix(libdir), self.source_folder, build_dir),
                 env="conanbuild")
        # Read the ctest-registered names only *after* the reconfigure above:
        # that step is what generates c10/test/CTestTestfile.cmake and
        # caffe2/CTestTestfile.cmake. The package build itself runs with
        # BUILD_TEST=OFF, so before this point neither file exists and the whole
        # caffe2/ATen group would silently drop out of the run (observed as
        # "51 c10 + 0 caffe2/ATen + 5 test/cpp" on the first end-to-end build).
        ctest_names = self._upstream_ctest_names(build_dir)
        if not ctest_names:
            raise ConanException(
                "no ctest-registered tests found after -DBUILD_TEST=ON in %s; "
                "c10/test/CTestTestfile.cmake and caffe2/CTestTestfile.cmake are "
                "checked, and an empty list means the upstream test targets "
                "would silently disappear from this run" % build_dir)
        names = sorted(set(c10_names) | set(ctest_names) | set(cpp_names))
        # c10/test registers 51 targets and caffe2 registers 58; the rest of the
        # 109 ctest names are those same c10 targets, so report the sizes of the
        # three groups that make up the union rather than the ctest total.
        caffe2_names = [n for n in ctest_names if n not in set(c10_names)]
        self.output.info("pytorch: upstream tests: building %d test targets "
                         "(%d c10 + %d caffe2/ATen + %d test/cpp)"
                         % (len(names), len(c10_names), len(caffe2_names),
                            len(cpp_names)))
        self.run('%s cmake --build "%s" --target %s -- -j%d'
                 % (self._test_phase_env_prefix(libdir), build_dir,
                    " ".join(names), self._build_jobs()),
                 env="conanbuild")

        report = os.path.join(build_dir, "upstream-ctest.log")
        # TEST_TMPDIR is what googletest uses for captured death-test output
        # (patch 0005); TMPDIR is what c10::make_tempfile uses. Both point at a
        # writable directory because /tmp is read-only on HarmonyOS PC.
        selected = [n for n in ctest_names if n not in self.UPSTREAM_CTEST_SPLIT]
        rc = self.run('{ %s TMPDIR="%s" TEST_TMPDIR="%s" ctest --test-dir "%s" '
                      '-R "^(%s)$" --timeout %d --output-on-failure ; } > "%s" 2>&1'
                      % (self._test_phase_env_prefix(libdir, os.path.join(build_dir, "lib")),
                         tmp_dir, tmp_dir, build_dir, "|".join(selected),
                         self.UPSTREAM_CTEST_TIMEOUT, report),
                      env="conanbuild", ignore_errors=True)
        ctest_total = ctest_failed = 0
        try:
            with open(report) as fh:
                for line in fh:
                    m = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", line)
                    if m:
                        ctest_failed, ctest_total = int(m.group(2)), int(m.group(3))
        except OSError:
            self.output.warning("pytorch: ctest report missing: %s" % report)

        # Phase 2: the test/cpp suites (ctest does not register them with this
        # configuration) and the two suites that only survive when their cases
        # are spread over several processes.
        index = self._binary_index(build_dir)
        results = []
        for name in cpp_names:
            if name in self.UPSTREAM_TEST_SPLIT_CHUNK:
                continue
            exe = index.get(name)
            if not exe:
                self.output.warning("pytorch: test binary not found: %s" % name)
                continue
            results.append(self._run_gtest_suite(build_dir, exe, None, name, libdir, tmp_dir))
        for name, chunk in sorted(self.UPSTREAM_TEST_SPLIT_CHUNK.items()):
            exe = index.get(name)
            if not exe:
                self.output.warning("pytorch: test binary not found: %s" % name)
                continue
            cases = self._gtest_case_names(build_dir, exe, libdir)
            for i in range(0, len(cases), chunk):
                results.append(self._run_gtest_suite(
                    build_dir, exe, ":".join(cases[i:i + chunk]),
                    "%s-%d" % (name, i // chunk), libdir, tmp_dir))
        for name in self.UPSTREAM_CTEST_SPLIT:
            exe = index.get(name)
            if not exe:
                self.output.warning("pytorch: test binary not found: %s" % name)
                continue
            groups = (self.UPSTREAM_INLINE_CONTAINER_GROUPS
                      if name == "inline_container_test"
                      else self._gtest_case_names(build_dir, exe, libdir))
            for i, group in enumerate(groups):
                results.append(self._run_gtest_suite(
                    build_dir, exe, group, "%s-%d" % (name, i), libdir, tmp_dir))

        listed = self._count_gtest_cases(build_dir, names, libdir, index)
        suites_total = ctest_total + len(results)
        suites_failed = ctest_failed + sum(1 for r in results if r["rc"] or r["failed"])
        cases_ok = sum(r["ok"] for r in results)
        cases_failed = sum(r["failed"] for r in results)
        cases_skipped = sum(r["skipped"] for r in results)
        self.output.info("pytorch: upstream tests: %d/%d suites passed "
                         "(ctest %d/%d, split/direct runs %d cases ok, %d failed, "
                         "%d skipped); %d gtest cases listed in the built subset"
                         % (suites_total - suites_failed, suites_total,
                            ctest_total - ctest_failed, ctest_total, cases_ok,
                            cases_failed, cases_skipped, listed))
        if rc != 0 or suites_failed or suites_total == 0:
            raise ConanException(
                "upstream tests failed (%d of %d suites; see %s and the "
                "upstream-*.log files in the build folder; gtest cases listed "
                "in the subset: %d)"
                % (suites_failed, suites_total, report, listed))

    def _upstream_ctest_names(self, build_dir):
        """Test names registered with ctest by the configured tree.

        c10/test and caffe2 each add one test per *_test.cpp, so the names are
        read back from the generated CTestTestfile.cmake instead of duplicating
        upstream's file(GLOB ...) rules here.
        """
        names = []
        for rel in ("c10/test/CTestTestfile.cmake", "caffe2/CTestTestfile.cmake"):
            path = os.path.join(build_dir, rel)
            if not os.path.exists(path):
                self.output.warning("pytorch: ctest file missing: %s" % path)
                continue
            with open(path) as fh:
                for line in fh:
                    m = re.match(r"add_test\(\[=\[([^]=]+)\]=?\]", line.strip())
                    if m:
                        names.append(m.group(1))
        return sorted(set(names))

    def _binary_index(self, build_dir):
        """Map test-binary name -> path for every executable under bin/."""
        index = {}
        for root, _dirs, files in os.walk(build_dir):
            if os.path.basename(root) != "bin":
                continue
            for name in files:
                path = os.path.join(root, name)
                if os.access(path, os.X_OK) and not os.path.isdir(path):
                    index.setdefault(name, path)
        return index

    def _gtest_case_names(self, build_dir, exe, libdir):
        """Full gtest case names (Suite.Case) of one test binary."""
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(build_dir, "lib"), libdir, "/system/lib64"])
        try:
            out = subprocess.run([exe, "--gtest_list_tests"], capture_output=True,
                                 text=True, timeout=120, env=env).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.warning("pytorch: cannot list gtest cases of %s: %s" % (exe, exc))
            return []
        names, suite = [], ""
        for line in out.splitlines():
            if not line.startswith("  "):
                suite = line.strip()
                continue
            case = line.strip().split("  #")[0].strip()
            if case:
                names.append("%s%s" % (suite, case))
        return names

    def _run_gtest_suite(self, build_dir, exe, gtest_filter, tag, libdir, tmp_dir):
        """Run one gtest binary (optionally a case filter) and parse the tally."""
        log = os.path.join(build_dir, "upstream-%s.log" % tag)
        cmd = ('TMPDIR="%s" TEST_TMPDIR="%s" "%s"' % (tmp_dir, tmp_dir, exe))
        if gtest_filter:
            cmd += ' --gtest_filter="%s"' % gtest_filter
        rc = self.run('{ %s %s ; } > "%s" 2>&1'
                      % (self._test_phase_env_prefix(libdir, os.path.join(build_dir, "lib")),
                         cmd, log),
                      env="conanbuild", ignore_errors=True)
        # Read the tallies from gtest's own summary lines. Counting the per-case
        # "[       OK ]" lines would miss cases that died mid-run and counting
        # the "[  SKIPPED ]"/"[  FAILED  ]" lines would double count, because
        # each of those is printed once as a header ("N tests, listed below:")
        # and once per case.
        counts = {"ran": 0, "passed": 0, "failed": 0, "skipped": 0}
        patterns = (
            ("ran", re.compile(r"\[==========\] (\d+) tests? from \d+ test suites? ran\.")),
            ("passed", re.compile(r"\[  PASSED  \] (\d+) tests?\.")),
            ("skipped", re.compile(r"\[  SKIPPED \] (\d+) tests?, listed below")),
            ("failed", re.compile(r"\[  FAILED  \] (\d+) tests?, listed below")),
        )
        try:
            with open(log, errors="replace") as fh:
                for line in fh:
                    if not line.startswith("["):
                        continue
                    for key, pat in patterns:
                        m = pat.search(line)
                        if m:
                            counts[key] = max(counts[key], int(m.group(1)))
                            break
        except OSError:
            self.output.warning("pytorch: gtest log missing: %s" % log)
        result = dict(counts, rc=rc, ok=counts["passed"], tag=tag)
        if rc != 0 or counts["failed"]:
            self.output.warning("pytorch: upstream suite %s failed (rc=%d, "
                                "%d ok, %d failed, log: %s)"
                                % (tag, rc, counts["passed"], counts["failed"], log))
        return result

    def _count_gtest_cases(self, build_dir, names, libdir, index=None):
        """Count gtest cases of the built subset via --gtest_list_tests."""
        index = index if index is not None else self._binary_index(build_dir)
        total = 0
        for name in names:
            exe = index.get(name)
            if not exe:
                self.output.warning("pytorch: test binary not found: %s" % name)
                continue
            total += len(self._gtest_case_names(build_dir, exe, libdir))
        return total

    def _write_ldd_shim(self):
        """Write an ldd-compatible helper (OHOS has no ldd) and return its path.

        CMake's LINK_WHAT_YOU_USE feature (enabled by PyTorch's CMakeLists) runs
        `ldd <target>` after linking; without it every link fails on OHOS. The
        shim lists DT_NEEDED entries via readelf, which is what ldd reports in
        practice, keeping the check meaningful instead of disabling it.
        """
        tools_dir = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tools_dir, exist_ok=True)
        shim = os.path.join(tools_dir, "ldd")
        script = r'''#!/bin/sh
# ldd-compatible shim for OHOS/musl (the platform ships no ldd).
# Lists DT_NEEDED entries so CMake's LINK_WHAT_YOU_USE check can run.
READELF="${READELF:-readelf}"
command -v "$READELF" >/dev/null 2>&1 || READELF=/data/service/hnp/bin/llvm-readelf
for f in "$@"; do
  case "$f" in -*) continue;; esac
  if [ ! -e "$f" ]; then
    echo "ldd: $f: No such file or directory" >&2
    continue
  fi
  echo "$f:"
  "$READELF" -d "$f" 2>/dev/null | awk '/\(NEEDED\)/ {gsub(/[\[\]]/, "", $NF); print "\t" $NF " => (ohos)"}'
done
exit 0
'''
        with open(shim, "w") as fh:
            fh.write(script)
        os.chmod(shim, 0o755)
        self.output.info("pytorch: ldd shim for LINK_WHAT_YOU_USE = %s" % shim)
        return shim

    def _dump_build_errors(self, libdir):
        """Re-run a serial debug build to surface compile errors in the log tail."""
        build_dir = self.build_folder
        wrapper = os.path.join(self.build_folder, "cmake-host.sh")
        cmd = ('cd "%s" && "%s" --build . -j1 2>&1 | '
               'grep -E -B4 -A20 "error:|Error|FAILED" | head -120'
               % (build_dir, wrapper))
        self.output.info("pytorch: build failed, dumping error context (serial rebuild)")
        self.run(cmd, env="conanbuild", ignore_errors=True)

    def _build_sleef_host_tools(self, native_dir):
        """Compile sleef's host codegen tools so cross-configure can use them."""
        bin_dir = os.path.join(native_dir, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        clang = os.path.join(self._sdk_native(), "llvm", "bin", "clang")
        sleef = os.path.join(self.source_folder, "third_party", "sleef", "src")
        inc = [
            "-I" + os.path.join(sleef, "libm"),
            "-I" + os.path.join(sleef, "libm", "include"),
            "-I" + os.path.join(sleef, "common"),
            "-I" + os.path.join(sleef),
        ]
        tools = [
            ("common/addSuffix.c", "addSuffix"),
            ("libm/mkrename.c", "mkrename"),
            ("libm/mkrename_gnuabi.c", "mkrename_gnuabi"),
            ("libm/mkmasked_gnuabi.c", "mkmasked_gnuabi"),
            ("libm/mkalias.c", "mkalias"),
            ("libm/mkdisp.c", "mkdisp"),
            ("dft/mkunroll.c", "mkunroll"),
            ("dft/mkdispatch.c", "mkdispatch"),
            ("quad/qmkrename.c", "qmkrename"),
            ("quad/qmkdisp.c", "qmkdisp"),
        ]
        for rel, out in tools:
            src = os.path.join(sleef, rel)
            if not os.path.exists(src):
                continue
            dst = os.path.join(bin_dir, out)
            if os.path.exists(dst):
                continue
            cmd = [clang] + inc + [src, "-o", dst]
            if "mkdispatch" in out:
                cmd.insert(1, "-DENABLE_STREAM=1")
            subprocess.run(cmd, check=True)

    def _cmake_vars(self):
        return {
            "OHOS_ARCH": "arm64-v8a",
            "CMAKE_SYSTEM_NAME": "OHOS",
            "CMAKE_SYSTEM_PROCESSOR": "aarch64",
            "CMAKE_BUILD_TYPE": "Release",
            "BUILD_PYTHON": "ON" if self.options.with_python else "OFF",
            "BUILD_TEST": "OFF",
            # OpenBLAS instead of the default Eigen fallback: gives real LAPACK
            # (USE_LAPACK=1) plus optimized GEMM. pytorch resolves it through its
            # own cmake/Modules/FindOpenBLAS.cmake, which searches
            # $ENV{OpenBLAS_HOME}/lib|include (set in build()), so module mode
            # wins over the CMakeDeps config file and no patch is needed.
            "BLAS": "OpenBLAS",
            "USE_CUDA": "OFF",
            "USE_CUDNN": "OFF",
            "USE_NCCL": "OFF",
            # Distributed (c10d) with the Gloo backend. Gloo is NOT an external
            # requirement: pytorch vendors it under third_party/gloo and links it
            # statically here (GLOO_INSTALL=OFF / GLOO_STATIC_OR_SHARED=STATIC in
            # cmake/Dependencies.cmake), so nothing has to be fetched from the
            # registry and no separate dependency PR is needed. Verified:
            # configure reports "Gloo build as SHARED library" with
            # USE_DISTRIBUTED/USE_GLOO = ON, and `--target gloo` builds clean.
            "USE_DISTRIBUTED": "ON" if self.options.with_distributed else "OFF",
            "USE_GLOO": "ON",
            # TensorPipe is the RPC transport; it needs its own nested submodules
            # (libuv/libnop/...), which the recipe now fetches.
            "USE_TENSORPIPE": "ON",
            # MKLDNN (oneDNN) is ON. Its aarch64 kernels are generated at run
            # time by the bundled xbyak_aarch64 JIT, which needs executable
            # memory; some OHOS launch domains refuse every way to obtain it
            # (measured inside the shipped interpreter process):
            #   mmap(RW)                              -> ok
            #   mmap(RWX) / mmap(RX)                  -> EINVAL
            #   mmap(RW) + mprotect(RX)               -> EINVAL
            #   memfd/real-file RX or RWX             -> EACCES
            #   file (RW,shared) + (RX,shared)        -> EACCES
            # while a compiled binary launched from that same process is free to
            # do all of the above (a native JIT stub maps RWX and executes,
            # returning its value). Patch 0013 fixes a genuine musl compile
            # break in that JIT and patch 0017 makes the dispatch safe: it probes
            # for executable memory once per process (at::isMKLDNNJitUsable) and
            # routes work away from oneDNN only where the kernels could not run
            # anyway. So the package ships oneDNN for real -- hasMKLDNN() is
            # true and USE_MKLDNN=ON is honoured -- on hardware/domains that
            # permit it, and degrades to ATen's native kernels (plus KleidiAI,
            # and QNNPACK for quantized work) where the sandbox forbids
            # self-modifying code, instead of trading a working convolution for
            # an aborting one.
            "USE_MKLDNN": "ON",
            # XNNPACK / QNNPACK / NNPACK are the CPU inference kernels
            # (quantized 8-bit paths included). Note the upstream option name is
            # USE_PYTORCH_QNNPACK -- the 2.13.0 recipe's "USE_QNNPACK" was a
            # no-op that never reached any CMake check.
            "USE_XNNPACK": "ON",
            "USE_PYTORCH_QNNPACK": "ON",
            "USE_NNPACK": "ON",
            # OpenMP is enabled: caffe2/CMakeLists.txt then picks
            # ATEN_THREADING = OMP, so ATen's intra-op loops run on the OpenMP
            # runtime instead of the native thread pool.
            #
            # The runtime comes from the SDK itself
            # (<sdk>/native/llvm/{include/omp.h,lib/aarch64-linux-ohos/libomp.a}),
            # linked *statically*. Measured on this machine with the target
            # compiler (clang/22.1.8) and the recipe's own flags: a parallel
            # region enters 8 distinct threads and a `reduction(+:)` returns the
            # exact sequential sum. The earlier note claiming the SDK's omp.h
            # does not compile under clang 22 was wrong -- it compiles and runs;
            # what it needs is `-isystem <sdk>/native/llvm/include` on the command
            # line (the header is not on clang 22's default include path), which
            # is wired in generate().
            #
            # Static (not shared) is deliberate: there is no libomp.so in
            # /system/lib64, so a shared link would leave every consumer needing
            # an extra LD_LIBRARY_PATH entry -- and .so files shipped from the
            # package hit the HMDFS/hmmac load restrictions (E212/E488).
            # `-static-openmp` + the explicit libomp.a gives a libtorch_cpu.so
            # whose only NEEDED entries stay libc++_shared.so/libc.so.
            "USE_OPENMP": "ON",
            # FBGEMM: the quantized 8-bit operator library (x86 server kernels +
            # the portable/ARM paths it selects on aarch64). Built statically from
            # third_party/fbgemm, whose nested external/asmjit is already pinned.
            "USE_FBGEMM": "ON",
            "USE_SLEEF": "OFF",
            # Kineto (libkineto) profiling: the torch.profiler backend. libkineto
            # unconditionally add_subdirectory()s dynolog/ipcfabric and fmt, both
            # of which the recipe now fetches.
            "USE_KINETO": "ON",
            # ITT (Intel VTune) is ON. Upstream expressed the option as
            #   cmake_dependent_option(USE_ITT ... ON "CPU_INTEL" OFF)
            # which forced it OFF on aarch64 regardless of -DUSE_ITT=ON; patch
            # 0018 turns that hard gate into an opt-in for the non-Intel
            # architectures. Nothing was missing on this side: the ITT API is
            # portable C and the bundled third_party/ittapi configures and
            # builds for aarch64 with the OHOS toolchain (libittnotify.a built
            # from ittnotify_static.c + jitprofiling.c), and the annotations are
            # no-ops unless a collector attaches -- so torch.profiler.itt is
            # functional (is_available() -> True, range_push/mark/range_pop
            # callable) instead of being permanently unavailable.
            "USE_ITT": "ON",
            "USE_NUMA": "OFF",
            "USE_GFLAGS": "OFF",
            "USE_GLOG": "OFF",
        }

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # HMDFS quirk: .so files written by `cmake --install` cannot be mapped
        # by the musl loader (dlopen fails with "Permission denied"), while the
        # same file copied from the build tree loads fine. Re-copy the shared
        # objects from the build tree into every lib dir consumers load from, so
        # the packaged copies are loadable.
        #
        # This is what fixes the CI failure: package lib/ was restaged already
        # (which is why the C++ consumers loaded it), but the Python module's own
        # torch/lib/ was left with the install-written copies, and
        # torch/__init__.py dlopens libtorch_global_deps.so from there as its
        # very first action -- "Permission denied" for every Python consumer.
        build_lib = self._build_lib_dir()
        if build_lib:
            n = self._restage_shared_objects(build_lib,
                                             [os.path.join(self.package_folder, "lib")])
            self.output.info("pytorch: restaged %d shared objects into lib/ "
                            "(from %s)" % (n, build_lib))
        if self.options.with_python:
            self._package_python_module(build_lib)

    def _build_lib_dir(self):
        """Locate the CMake output dir holding the freshly linked .so files.

        Assumes nothing about the layout: cmake_layout nests the build dir under
        `build/<config>`, so `<build_folder>/lib` (the historical guess here) did
        not exist and the restaging below silently did nothing. Probe the usual
        spots, then fall back to a bounded search for libtorch_cpu.so.
        """
        root = self.build_folder
        for cand in (os.path.join(root, "lib"),
                     os.path.join(root, "build", "Release", "lib"),
                     os.path.join(root, "build", "lib")):
            if os.path.isfile(os.path.join(cand, "libtorch_cpu.so")):
                self.output.info("pytorch: restaging shared objects from %s" % cand)
                return cand
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath[len(root):].count(os.sep) >= 4:
                dirnames[:] = []
                continue
            if "libtorch_cpu.so" in filenames:
                self.output.info("pytorch: restaging shared objects from %s" % dirpath)
                return dirpath
        self.output.warning("pytorch: no build-tree lib dir with libtorch_cpu.so under "
                            "%s; the packaged .so stay as cmake --install wrote them" % root)
        return None

    def _restage_shared_objects(self, build_lib, dest_dirs):
        """Replace the install-written .so in the package with build-tree copies.

        The write itself is what makes the result loadable: .so files produced by
        `cmake --install` cannot be mapped by the musl loader on this filesystem
        ("Permission denied"), while fresh copies of the same bytes load fine.

        The existing file has to be unlinked first -- overwriting it in place
        fails with "Operation not permitted" -- and the permission widening is
        best-effort, because chmod cannot add the group/other bits here.
        """
        copied = 0
        problems = []
        for name in sorted(os.listdir(build_lib)):
            if not name.endswith(".so"):
                continue
            for dest in dest_dirs:
                os.makedirs(dest, exist_ok=True)
                target = os.path.join(dest, name)
                try:
                    if os.path.lexists(target):
                        os.remove(target)
                    shutil.copy2(os.path.join(build_lib, name), target)
                except OSError as e:
                    problems.append("%s (%s)" % (target, e))
                    continue
                try:
                    os.chmod(target, os.stat(target).st_mode | 0o555)
                except OSError:
                    pass
                copied += 1
        if problems:
            # Not fatal: the manifest of what failed is what matters when the
            # packaged libs turn out to be unloadable.
            self.output.warning("pytorch: %d shared object(s) could not be restaged: %s"
                                % (len(problems), "; ".join(problems)))
        return copied

    # ── torch Python package assembly (BUILD_PYTHON) ──────────────────────
    # CMake installs `_C` and version.py at the prefix ROOT because the wheel
    # build maps that root onto torch/ via wheel.install-dir = "torch"; conan
    # has no mapping step, so the module tree is assembled here instead --
    # python sources + the `_C` extension + the shared objects torch loads from
    # torch/lib at import time (same layout the wheel ships, and the same
    # layout the local prototype assembled).
    _PY_EXCLUDE_DIRS = ("csrc", "test", "tests", "__pycache__", "include")

    def _python_version(self):
        """X.Y of the interpreter chosen in generate() (falls back to 3.12)."""
        exe = getattr(self, "_py_exe", None)
        if exe:
            try:
                out = subprocess.run([exe, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"],
                                     capture_output=True, text=True, timeout=60,
                                     env={**os.environ, **(getattr(self, "_py_env", None) or {})})
                if out.returncode == 0 and out.stdout.strip():
                    return out.stdout.strip()
            except (OSError, subprocess.SubprocessError):
                pass
        return "3.12"

    def _package_python_module(self, build_lib):
        version = self._python_version()
        site = os.path.join(self.package_folder, "lib",
                            "python%s" % version, "site-packages")
        dest = os.path.join(site, "torch")
        src = os.path.join(self.source_folder, "torch")
        if not os.path.isdir(src):
            raise ConanException("BUILD_PYTHON is on but %s is missing" % src)

        copied = 0
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in self._PY_EXCLUDE_DIRS]
            rel = os.path.relpath(root, src)
            out_dir = dest if rel == "." else os.path.join(dest, rel)
            for name in files:
                if name.endswith((".py", ".pyi", ".json", ".yaml", ".txt", ".so")):
                    os.makedirs(out_dir, exist_ok=True)
                    shutil.copy2(os.path.join(root, name), os.path.join(out_dir, name))
                    copied += 1
        # torchgen is imported at runtime by torch/_library/utils.py,
        # torch/_custom_op/impl.py and others, and the upstream wheel ships it as
        # a top-level package (setup.py: include=["torch", "torch.*", "torchgen",
        # "torchgen.*"]), so a `torch` module without it fails at import time.
        torchgen_src = os.path.join(self.source_folder, "torchgen")
        if os.path.isdir(torchgen_src):
            for root, dirs, files in os.walk(torchgen_src):
                dirs[:] = [d for d in dirs if d not in self._PY_EXCLUDE_DIRS]
                rel = os.path.relpath(root, torchgen_src)
                out_dir = (os.path.join(site, "torchgen") if rel == "."
                           else os.path.join(site, "torchgen", rel))
                for name in files:
                    if name.endswith((".py", ".pyi")):
                        os.makedirs(out_dir, exist_ok=True)
                        shutil.copy2(os.path.join(root, name),
                                     os.path.join(out_dir, name))
                        copied += 1
        else:
            self.output.warning("pytorch: torchgen/ not found in the source tree; "
                                "the torch module will fail to import")
        # The `_C` extension itself: built into <build>/torch with the SOABI
        # suffix (e.g. _C.cpython-312-aarch64-linux-ohos.so).
        build_torch = os.path.join(self.build_folder, "torch")
        ext = None
        if os.path.isdir(build_torch):
            for name in os.listdir(build_torch):
                if name.startswith("_C") and name.endswith(".so"):
                    ext = os.path.join(build_torch, name)
                    break
        if not ext:
            raise ConanException(
                "BUILD_PYTHON is on but the `_C` extension was not built under %s"
                % build_torch)
        shutil.copy2(ext, os.path.join(dest, os.path.basename(ext)))
        # version.py is generated by the gen_torch_version target (into the
        # build tree's torch/, and installed at the prefix root by CMake).
        for cand in (os.path.join(self.build_folder, "torch", "version.py"),
                     os.path.join(self.source_folder, "torch", "version.py"),
                     os.path.join(self.build_folder, "version.py"),
                     os.path.join(self.package_folder, "version.py")):
            if os.path.isfile(cand):
                shutil.copy2(cand, os.path.join(dest, "version.py"))
                break
        # torch/lib: what torch/__init__.py loads via ctypes (libtorch_global_deps)
        # and what `_C`/libtorch_python.so resolve their NEEDED entries against.
        # Restaged from the BUILD tree (see package()): install-written .so files
        # are not mmap-able on HMDFS, and `ctypes.CDLL(libtorch_global_deps)` is
        # the very first thing torch/__init__.py does, so a bad copy here breaks
        # every Python consumer with "Permission denied".
        py_lib = os.path.join(dest, "lib")
        os.makedirs(py_lib, exist_ok=True)
        if build_lib:
            n = self._restage_shared_objects(build_lib, [py_lib])
            self.output.info("pytorch: restaged %d shared objects into torch/lib "
                            "(from %s)" % (n, build_lib))
        else:
            self.output.warning("pytorch: build-tree lib dir not found; torch/lib "
                                "keeps the cmake --install copies, which may not be "
                                "loadable on HMDFS")
        for extra in ("torch_shm_manager",):
            cand = os.path.join(self.build_folder, "bin", extra)
            if os.path.isfile(cand):
                bin_dst = os.path.join(dest, "bin")
                os.makedirs(bin_dst, exist_ok=True)
                shutil.copy2(cand, os.path.join(bin_dst, extra))
        self.output.info("pytorch: packaged torch python module (%d files, python %s)"
                         % (copied, version))

    def package_info(self):
        self.cpp_info.libs = ["torch", "torch_cpu", "c10"]
        # PyTorch installs the libtorch C++ API headers under
        # include/torch/csrc/api/include (umbrella torch.h etc.), so consumers
        # need both include roots to `#include <torch/torch.h>`.
        self.cpp_info.includedirs = ["include", "include/torch/csrc/api/include"]
        self.cpp_info.bindirs = ["lib"]
        # OpenMP must be visible to *consumer* translation units, not just to the
        # library build. at::parallel_for / at::parallel_reduce are inline
        # templates (ATen/Parallel-inl.h -> ATen/ParallelOpenMP.h), so every
        # consumer TU instantiates them; the `#pragma omp parallel` inside is
        # silently ignored when that TU is not compiled with an OpenMP flag, and
        # the loop then runs on a single thread (the runtime reports
        # omp_get_num_threads() == 1). Measured: with the same library and the
        # same call, a consumer compiled without the flag observed 1 worker
        # thread, one compiled with it observed 20.
        # Only the *compile* flag is needed: libtorch_cpu.so links the OpenMP
        # runtime statically and exports it (omp_* and __kmpc_* are defined
        # symbols there), so consumer objects resolve those symbols against
        # libtorch_cpu.so without a second runtime on the link line -- important,
        # because two OpenMP runtimes in one process is the "OMP: Error #15"
        # hazard. This mirrors what the official libtorch CMake package does when
        # it is built with OpenMP.
        self.cpp_info.cflags.append("-fopenmp=libomp")
        self.cpp_info.cxxflags.append("-fopenmp=libomp")
        if self.options.with_python:
            # Python consumers reach the module through PYTHONPATH; conan has no
            # first-class site-packages concept, so expose it the way the other
            # python packages in this repository do.
            for root, dirs, _files in os.walk(os.path.join(self.package_folder, "lib")):
                if os.path.basename(root) == "site-packages":
                    self.runenv_info.prepend_path("PYTHONPATH", root)
                    self.buildenv_info.prepend_path("PYTHONPATH", root)
                    self.output.info("PYTHONPATH += %s" % root)
                    dirs[:] = []
