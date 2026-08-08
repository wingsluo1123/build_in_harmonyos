#!/usr/bin/env python3
"""Conan recipe — fluent-bit 5.0.9 (CMake project).

HarmonyOS (OHOS) aarch64 build.  All optional features that pull in external
libraries unavailable on OHOS (TLS, HTTP server, AWS, Kafka, SQLDB, WASM, Lua,
regex, Avro/Arrow, many input/output plugins) are disabled via CMake options,
so the recipe has ZERO Conan requires — it builds a standalone core binary.

Stub headers (openssl, sqlite3, fts) and stub monkey generated headers
(mk_core_info.h, mk_info.h, mk_env.h) are injected from a plain-text stub
tree (patches/stubs) that materialises them under ${BUILD_FOLDER}/include/.
A link-time stubs source provides empty implementations for the few symbols
referenced by callers when the corresponding subsystem is compiled out.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class FluentBitConan(ConanFile):
    name = "fluent-bit"
    version = "5.0.9"
    description = "Fast and Lightweight Log processor and forwarder for Linux, BSD and OSX"
    license = "Apache-2.0"
    homepage = "https://fluentbit.io"
    url = "https://github.com/fluent/fluent-bit"
    topics = ("logging", "log-processor", "observability", "ohos")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared":           [True, False],
        "debug":            [True, False],
    }
    default_options = {
        "shared":           False,
        "debug":            False,
    }

    def export_sources(self):
        export_conandata_patches(self)
        # Manually copy the OHOS stub sources (headers + link-time stubs file)
        # listed under the custom `stubs:` key (NOT under patches: — conan 2.x
        # apply_conandata_patches would try to parse every entry as a .patch).
        # The stub tree is kept as plain text files in git (no binary tar.gz)
        # so PR diffs remain text-only and CI's `git apply` succeeds.
        import os, shutil
        stubs = self.conan_data.get("stubs", {}) or {}
        stub_dir = stubs.get("dir") if isinstance(stubs, dict) else None
        if stub_dir:
            src = os.path.join(self.recipe_folder, stub_dir)
            if os.path.isdir(src):
                dst = os.path.join(self.export_sources_folder, stub_dir)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # OHOS build is self-contained: every optional dep is disabled below.
        pass

    def source(self):
        # OHOS CI: avoid flaky ghfast.top mirror timeouts by preferring a local
        # copy of the upstream tarball when present in the downloads cache.
        import os, shutil, hashlib
        src = self.conan_data["sources"]
        url = src["url"]
        expected_sha = src["sha256"]
        # NOTE: Conan 2.x ConanFile has no `cache_folder` attribute, so only
        # the ~/.conan2/downloads candidate is real (AI review P3: dead code).
        candidates = [
            os.path.join(os.path.expanduser("~/.conan2/downloads"), expected_sha),
        ]
        local = next((p for p in candidates if os.path.isfile(p)), None)
        if local:
            self.output.info(f"Using local cached tarball: {local}")
            dest = os.path.join(self.source_folder, "fluent-bit-5.0.9.tar.gz")
            shutil.copy(local, dest)
            # verify sha256
            h = hashlib.sha256()
            with open(dest, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != expected_sha:
                raise ConanException(f"sha256 mismatch for local tarball {local}")
            from conan.tools.files import unzip
            unzip(self, dest, strip_root=True)
        else:
            get(self, **src, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # --- Disable every optional subsystem that needs an unavailable dep ---
        opts = {
            "FLB_DEBUG":                    "Off",
            "FLB_RELEASE":                  "On",
            "FLB_EXAMPLES":                 "Off",
            "FLB_TESTS_INTERNAL":           "Off",
            "FLB_TESTS_RUNTIME":            "Off",
            "FLB_TESTS_OSSFUZZ":            "Off",
            "FLB_TLS":                      "Off",
            "FLB_HTTP_SERVER":              "Off",
            "FLB_AWS":                      "Off",
            "FLB_AWS_ERROR_REPORTER":       "Off",
            "FLB_SIGNV4":                   "Off",
            "FLB_KAFKA":                    "Off",
            "FLB_LUAJIT":                   "Off",
            "FLB_SQLDB":                    "Off",
            "FLB_BACKTRACE":                "Off",
            "FLB_WASM":                     "Off",
            "FLB_AVRO_ENCODER":             "Off",
            "FLB_ARROW":                    "Off",
            "FLB_REGEX":                    "Off",
            "FLB_UTF8_ENCODER":             "Off",
            "FLB_UNICODE_ENCODER":         "Off",
            "FLB_JEMALLOC":                 "Off",
            "FLB_VALGRIND":                 "Off",
            "FLB_SHARED_LIB":               "Off",
            "FLB_BINARY":                   "On",
            "FLB_CONFIG_YAML":              "Off",
            # --- input plugins needing external deps ---
            "FLB_IN_HTTP":                  "Off",
            "FLB_IN_ELASTICSEARCH":         "Off",
            "FLB_IN_OPENTELEMETRY":         "Off",
            "FLB_IN_SPLUNK":                "Off",
            "FLB_IN_KAFKA":                 "Off",
            "FLB_IN_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_IN_PROMETHEUS_SCRAPE":     "Off",
            "FLB_IN_PROMETHEUS_TEXTFILE":   "Off",
            "FLB_IN_DOCKER":                "Off",
            "FLB_IN_DOCKER_EVENTS":         "Off",
            "FLB_IN_MQTT":                  "Off",
            "FLB_IN_NGINX_EXPORTER_METRICS": "Off",
            "FLB_IN_NODE_EXPORTER_METRICS": "Off",
            "FLB_IN_KUBERNETES_EVENTS":     "Off",
            "FLB_IN_BLOB":                  "Off",
            # --- output plugins needing external deps ---
            "FLB_OUT_HTTP":                 "Off",
            # FLB_OUT_TD defaults ON and forces set(FLB_TLS ON), which would
            # re-enable TLS sources (tls/flb_tls.c, flb_oauth2*.c) even with
            # -DFLB_TLS=Off; disable it to keep the OHOS zero-dep build.
            "FLB_OUT_TD":                   "Off",
            "FLB_OUT_KAFKA":                "Off",
            "FLB_OUT_KAFKA_REST":           "Off",
            "FLB_OUT_OPENTELEMETRY":        "Off",
            "FLB_OUT_PROMETHEUS_EXPORTER":  "Off",
            "FLB_OUT_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_OUT_SPLUNK":               "Off",
            "FLB_OUT_VIVO_EXPORTER":        "Off",
            "FLB_OUT_AZURE":                "Off",
            "FLB_OUT_AZURE_BLOB":           "Off",
            "FLB_OUT_AZURE_KUSTO":          "Off",
            "FLB_OUT_AZURE_LOGS_INGESTION": "Off",
            "FLB_OUT_CLOUDWATCH_LOGS":      "Off",
            "FLB_OUT_DATADOG":              "Off",
            "FLB_OUT_KINESIS_FIREHOSE":     "Off",
            "FLB_OUT_KINESIS_STREAMS":      "Off",
            "FLB_OUT_LOKI":                 "Off",
            "FLB_OUT_S3":                   "Off",
            "FLB_OUT_STACKDRIVER":          "Off",
            "FLB_OUT_BIGQUERY":             "Off",
            "FLB_OUT_CHRONICLE":            "Off",
            "FLB_OUT_GELF":                 "Off",
            "FLB_OUT_INFLUXDB":             "Off",
            "FLB_OUT_LOGDNA":               "Off",
            "FLB_OUT_NATS":                 "Off",
            "FLB_OUT_NRLOGS":               "Off",
            "FLB_OUT_OPENSEARCH":           "Off",
            "FLB_OUT_ES":                   "Off",
            "FLB_OUT_CALYPTIA":             "Off",
            # out_forward: io_net_write/io_net_read are static helpers defined
            # inside `#ifdef FLB_HAVE_TLS`; they cannot be satisfied by the
            # link-time stub, so the plugin must stay off when FLB_TLS=Off.
            "FLB_OUT_FORWARD":              "Off",
            # --- filter plugins needing external deps ---
            "FLB_FILTER_AWS":               "Off",
            "FLB_FILTER_ECS":               "Off",
            "FLB_FILTER_GEOIP2":            "Off",
            "FLB_FILTER_KUBERNETES":        "Off",
            "FLB_FILTER_LUA":               "Off",
            "FLB_FILTER_WASM":              "Off",
        }
        for k, v in opts.items():
            tc.cache_variables[k] = v
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Materialise OHOS stub sources (headers + link-time stubs file) under
        # the build folder before cmake.configure runs. The stub tree lives
        # under the custom `stubs:` conandata key (NOT patches:) so apply
        # skipped it. It is plain text (no binary tar.gz) so PR diffs stay
        # text-only and CI `git apply` can apply them.
        import os, shutil
        stubs = self.conan_data.get("stubs", {}) or {}
        stub_dir = stubs.get("dir") if isinstance(stubs, dict) else None
        if stub_dir:
            candidates = [
                os.path.join(self.export_sources_folder, stub_dir),
                os.path.join(self.recipe_folder, stub_dir),
            ]
            stub_root = next((p for p in candidates if os.path.isdir(p)), None)
            if not stub_root:
                raise ConanException(
                    f"OHOS stubs dir not found: {stub_dir} — "
                    f"place it at patches/stubs (see conandata.yml stubs:)")
            # Copy the whole stub tree into the build folder: include/ lands at
            # ${BUILD_FOLDER}/include/ (stub headers + generated monkey headers)
            # and ohos_link_stubs.c at ${BUILD_FOLDER}/ohos_link_stubs.c, which
            # the source patch adds to src/CMakeLists.txt.
            for root, dirs, files in os.walk(stub_root):
                rel = os.path.relpath(root, stub_root)
                for f in files:
                    src_f = os.path.join(root, f)
                    dst_f = os.path.join(self.build_folder, rel, f)
                    os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                    shutil.copy(src_f, dst_f)
            self.output.info(f"Materialised OHOS stubs from: {stub_root}")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Application recipe: no libs to advertise, but advertise the bin/
        # directory so test_package can locate the installed fluent-bit
        # executable via cpp_info.bindirs.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
