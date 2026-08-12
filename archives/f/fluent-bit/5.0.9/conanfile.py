#!/usr/bin/env python3
"""Conan recipe for fluent-bit 5.0.9.

This recipe intentionally moves away from the historical zero-dependency
HarmonyOS build.  The first validation target is a real-dependency core build:
TLS through OpenSSL, SQLDB through sqlite3, YAML config through libyaml, and
BSD fts through musl-fts.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.gnu import PkgConfigDeps


class FluentBitConan(ConanFile):
    name = "fluent-bit"
    version = "5.0.9"
    description = "Fast and lightweight log processor and forwarder"
    license = "Apache-2.0"
    homepage = "https://fluentbit.io"
    url = "https://github.com/fluent/fluent-bit"
    topics = ("logging", "log-processor", "observability", "ohos")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "debug": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "debug": False,
        "with_tests": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("openssl/3.5.6.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libyaml/0.2.5")
        self.requires("musl-fts/1.2.7")

    def source(self):
        source = self.conan_data["sources"]
        expected_sha = source["sha256"]
        for candidate in self._source_candidates(expected_sha):
            if self._sha256(candidate) == expected_sha:
                self.output.info(f"Using local verified source archive: {candidate}")
                unzip(self, candidate, strip_root=True)
                return
        get(self, **source, strip_root=True)

    def _source_candidates(self, expected_sha):
        return [
            os.environ.get("FLUENT_BIT_SOURCE_ARCHIVE", ""),
            os.path.join(os.path.expanduser("~"), ".conan2", "downloads", expected_sha),
        ]

    @staticmethod
    def _sha256(path):
        if not os.path.isfile(path):
            return ""
        import hashlib

        h = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        pkg = PkgConfigDeps(self)
        pkg.generate()

        tc = CMakeToolchain(self)

        libyaml = self.dependencies.get("libyaml")
        if libyaml is not None and libyaml.package_folder:
            tc.cache_variables["FLB_LIBYAML_DIR"] = libyaml.package_folder

        sqlite = self.dependencies.get("sqlite3")
        if sqlite is not None and sqlite.package_folder:
            tc.cache_variables["FLB_PREFER_SYSTEM_LIB_SQLITE"] = "On"
            tc.cache_variables["SQLITE_FOUND"] = "On"
            tc.cache_variables["SQLITE_INCLUDE_DIRS"] = os.path.join(
                sqlite.package_folder, "include"
            )
            tc.cache_variables["SQLITE_LIBRARY_DIRS"] = os.path.join(
                sqlite.package_folder, "lib"
            )
            tc.cache_variables["SQLITE_LIBRARIES"] = "sqlite3"

        fts = self.dependencies.get("musl-fts")
        if fts is not None and fts.package_folder:
            tc.cache_variables["FTS_INCLUDE_DIR"] = os.path.join(
                fts.package_folder, "include"
            )
            tc.cache_variables["FTS_LIBRARY_DIR"] = os.path.join(
                fts.package_folder, "lib"
            )
            tc.cache_variables["FTS_LIBRARY"] = os.path.join(
                fts.package_folder, "lib", "libfts.so.0.0.0"
            )

        openssl = self.dependencies.get("openssl")
        if openssl is not None and openssl.package_folder:
            openssl_include = os.path.join(openssl.package_folder, "include")
            openssl_lib = os.path.join(openssl.package_folder, "lib")
            tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl.package_folder
            tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl_include
            tc.cache_variables["OPENSSL_INCLUDE_DIRS"] = openssl_include
            tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(
                openssl_lib, "libssl.a"
            )
            tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
                openssl_lib, "libcrypto.a"
            )

        opts = {
            "FLB_DEBUG": "On" if self.options.debug else "Off",
            "FLB_RELEASE": "Off" if self.options.debug else "On",
            "FLB_MINIMAL": "On",
            "FLB_EXAMPLES": "Off",
            "FLB_TESTS_INTERNAL": "On" if self.options.with_tests else "Off",
            "FLB_TESTS_RUNTIME": "On" if self.options.with_tests else "Off",
            "FLB_TESTS_OSSFUZZ": "Off",
            "FLB_TLS": "On",
            "FLB_HTTP_SERVER": "On",
            "FLB_SQLDB": "On",
            "FLB_SIGNV4": "Off",
            "FLB_CONFIG_YAML": "On",
            "FLB_AWS": "Off",
            "FLB_AWS_ERROR_REPORTER": "Off",
            "FLB_KAFKA": "Off",
            "FLB_LUAJIT": "Off",
            "FLB_BACKTRACE": "Off",
            "FLB_WASM": "Off",
            "FLB_AVRO_ENCODER": "Off",
            "FLB_ARROW": "Off",
            "FLB_PARSER": "On",
            "FLB_RECORD_ACCESSOR": "Off",
            "FLB_STREAM_PROCESSOR": "Off",
            "FLB_REGEX": "On",
            "FLB_UTF8_ENCODER": "Off",
            "FLB_UNICODE_ENCODER": "Off",
            "FLB_JEMALLOC": "Off",
            "FLB_VALGRIND": "Off",
            "FLB_SHARED_LIB": "Off",
            "FLB_BINARY": "On",
            "FLB_IN_HTTP": "On",
            "FLB_IN_ELASTICSEARCH": "Off",
            "FLB_IN_OPENTELEMETRY": "Off",
            "FLB_IN_SPLUNK": "Off",
            "FLB_IN_KAFKA": "Off",
            "FLB_IN_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_IN_PROMETHEUS_SCRAPE": "Off",
            "FLB_IN_PROMETHEUS_TEXTFILE": "Off",
            "FLB_IN_DOCKER": "Off",
            "FLB_IN_DOCKER_EVENTS": "Off",
            "FLB_IN_MQTT": "Off",
            "FLB_IN_NGINX_EXPORTER_METRICS": "Off",
            "FLB_IN_NODE_EXPORTER_METRICS": "Off",
            "FLB_IN_KUBERNETES_EVENTS": "Off",
            "FLB_IN_BLOB": "Off",
            "FLB_OUT_HTTP": "On",
            "FLB_OUT_TD": "Off",
            "FLB_OUT_KAFKA": "Off",
            "FLB_OUT_KAFKA_REST": "Off",
            "FLB_OUT_OPENTELEMETRY": "Off",
            "FLB_OUT_PROMETHEUS_EXPORTER": "Off",
            "FLB_OUT_PROMETHEUS_REMOTE_WRITE": "Off",
            "FLB_OUT_SPLUNK": "Off",
            "FLB_OUT_VIVO_EXPORTER": "Off",
            "FLB_OUT_AZURE": "Off",
            "FLB_OUT_AZURE_BLOB": "Off",
            "FLB_OUT_AZURE_KUSTO": "Off",
            "FLB_OUT_AZURE_LOGS_INGESTION": "Off",
            "FLB_OUT_CLOUDWATCH_LOGS": "Off",
            "FLB_OUT_DATADOG": "Off",
            "FLB_OUT_KINESIS_FIREHOSE": "Off",
            "FLB_OUT_KINESIS_STREAMS": "Off",
            "FLB_OUT_LOKI": "Off",
            "FLB_OUT_S3": "Off",
            "FLB_OUT_STACKDRIVER": "Off",
            "FLB_OUT_BIGQUERY": "Off",
            "FLB_OUT_CHRONICLE": "Off",
            "FLB_OUT_GELF": "Off",
            "FLB_OUT_INFLUXDB": "Off",
            "FLB_OUT_LOGDNA": "Off",
            "FLB_OUT_NATS": "Off",
            "FLB_OUT_NRLOGS": "Off",
            "FLB_OUT_OPENSEARCH": "Off",
            "FLB_OUT_ES": "Off",
            "FLB_OUT_CALYPTIA": "Off",
            "FLB_OUT_FORWARD": "Off",
            "FLB_FILTER_AWS": "Off",
            "FLB_FILTER_ECS": "Off",
            "FLB_FILTER_GEOIP2": "Off",
            "FLB_FILTER_KUBERNETES": "Off",
            "FLB_FILTER_LUA": "Off",
            "FLB_FILTER_WASM": "Off",
            "FLB_PROCESSOR_CONTENT_MODIFIER": "Off",
            "FLB_PROCESSOR_CUMULATIVE_TO_DELTA": "Off",
            "FLB_PROCESSOR_LABELS": "Off",
            "FLB_PROCESSOR_METRICS_SELECTOR": "Off",
            "FLB_PROCESSOR_OPENTELEMETRY_ENVELOPE": "Off",
            "FLB_PROCESSOR_SAMPLING": "Off",
            "FLB_PROCESSOR_SQL": "Off",
            "FLB_PROCESSOR_TDA": "Off",
            "FLB_PROCESSOR_TEMPLATE": "Off",
        }
        for key, value in opts.items():
            tc.cache_variables[key] = value
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
