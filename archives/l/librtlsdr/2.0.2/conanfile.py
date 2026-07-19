from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibrtlsdrConan(ConanFile):
    name = "librtlsdr"
    version = "2.0.2"
    description = "Software defined radio receiver for RTL2832U based DVB-T dongles"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/osmocom/rtl-sdr"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os == "OHOS":
            self.options.shared = False
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["INSTALL_UDEV_RULES"] = False
        tc.variables["DETACH_KERNEL_DRIVER"] = False
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
        self.cpp_info.libs = ["rtlsdr"]
        self.cpp_info.requires = ["libusb::libusb"]

    def requirements(self):
        self.requires("libusb/1.0.27")
