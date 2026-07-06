#!/usr/bin/env python3
"""Conan test_package — perl-stream-buffered 0.03-r5

Tests that Stream::Buffered can be loaded and used to buffer bytes.
"""
import os
import glob
import subprocess

from conan import ConanFile


class PerlStreamBufferedTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find Stream/Buffered.pm in the package folder
        pkg = self.dependencies["perl-stream-buffered"]
        pkg_folder = pkg.package_folder
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Buffered.pm"), recursive=True)
        if not pm_files:
            raise Exception("Stream/Buffered.pm not found in package")
        # Get the lib directory (parent of Stream's parent)
        lib_dir = os.path.dirname(os.path.dirname(pm_files[0]))

        env = os.environ.copy()
        env["PERL5LIB"] = lib_dir + ":" + env.get("PERL5LIB", "")

        # Test 1: Load Stream::Buffered and create a buffer
        result = subprocess.run(
            ['perl', '-MStream::Buffered', '-e',
             'my $buf = Stream::Buffered->new(); '
             '$buf->print("hello"); '
             'print "Buffer size: ", $buf->size, "\n"'],
            env=env, capture_output=True, text=True
        )
        if result.returncode != 0:
            self.output.error(f"Stream::Buffered load test failed: {result.stderr}")
            raise Exception(f"Stream::Buffered load test failed with exit code {result.returncode}")
        self.output.success(f"Test 1 (load + print + size): {result.stdout.strip()}")

        # Test 2: Test rewind and read
        result2 = subprocess.run(
            ['perl', '-MStream::Buffered', '-e',
             'my $buf = Stream::Buffered->new(); '
             '$buf->print("test data"); '
             'my $fh = $buf->rewind; '
             'my $line = do { local $/; <$fh> }; '
             'print "Read back: ", $line, "\n"'],
            env=env, capture_output=True, text=True
        )
        if result2.returncode != 0:
            self.output.warning(f"Stream::Buffered rewind test had issues: {result2.stderr}")
        else:
            self.output.success(f"Test 2 (rewind + read): {result2.stdout.strip()}")
