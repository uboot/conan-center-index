import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "PkgConfigDeps"

    @property
    def shared(self):
        return self.dependencies[self.tested_reference_str].options.shared

    @property
    def base(self):
        return self.dependencies[self.tested_reference_str].options.base

    @property
    def good(self):
        return self.dependencies[self.tested_reference_str].options.good

    @property
    def bad(self):
        return self.dependencies[self.tested_reference_str].options.bad

    @property
    def ugly(self):
        return self.dependencies[self.tested_reference_str].options.ugly

    @property
    def libav(self):
        return self.dependencies[self.tested_reference_str].options.libav

    @property
    def ges(self):
        return self.dependencies[self.tested_reference_str].options.ges

    @property
    def rtsp_server(self):
        return self.dependencies[self.tested_reference_str].options.rtsp_server

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")

    def generate(self):
        # Print debug information from gstreamer at runtime
        env = Environment()
        env.define("GST_DEBUG", "1")
        env.vars(self, scope="run").save_script("conanrun_gstdebug")

        tc = CMakeToolchain(self)
        tc.variables["STATIC"] = not self.shared
        tc.variables["BASE"] = self.base
        tc.variables["GOOD"] = self.good
        tc.variables["BAD"] = self.bad
        tc.variables["UGLY"] = self.ugly
        tc.variables["LIBAV"] = self.libav
        tc.variables["GES"] = self.ges
        tc.variables["RTSP_SERVER"] = self.rtsp_server
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindir, "core")
            self.run(bin_path, env="conanrun")

            if self.base:
                bin_path = os.path.join(self.cpp.build.bindir, "base")
                self.run(bin_path, env="conanrun")

            if self.good:
                bin_path = os.path.join(self.cpp.build.bindir, "good")
                self.run(bin_path, env="conanrun")

            if self.bad:
                bin_path = os.path.join(self.cpp.build.bindir, "bad")
                self.run(bin_path, env="conanrun")

            if self.ugly:
                bin_path = os.path.join(self.cpp.build.bindir, "ugly")
                self.run(bin_path, env="conanrun")

            if self.libav:
                bin_path = os.path.join(self.cpp.build.bindir, "libav")
                self.run(bin_path, env="conanrun")

            if self.ges:
                bin_path = os.path.join(self.cpp.build.bindir, "ges")
                self.run(bin_path, env="conanrun")

            if self.rtsp_server:
                bin_path = os.path.join(self.cpp.build.bindir, "rtsp_server")
                self.run(bin_path, env="conanrun")
