from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import PkgConfig
from conan.tools.system import package_manager

required_conan_version = ">=1.50.0"


class LibV4LConan(ConanFile):
    name = "libv4l"
    version = "system"
    description = "API for V4L (Video for Linux)"
    topics = ("devices",)
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://linuxtv.org/downloads/v4l-utils"
    license = "GPL-2.0-or-later"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        pass

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("libv4l is only supported on Linux.")

    def package_id(self):
        self.info.clear()

    def system_requirements(self):
        dnf = package_manager.Dnf(self)
        dnf.install(["libv4l-devel"], update=True, check=True)

        yum = package_manager.Yum(self)
        yum.install(["libv4l-devel"], update=True, check=True)

        apt = package_manager.Apt(self)
        apt.install(["libv4l-dev"], update=True, check=True)

        pacman = package_manager.PacMan(self)
        pacman.install(["libv4l"], update=True, check=True)

        zypper = package_manager.Zypper(self)
        zypper.install(["libv4l-devel"], update=True, check=True)

        alpine = package_manager.Apk(self)
        alpine.install(["libv4l-dev"], update=True, check=True)

    def package_info(self):
        for name in ['libv4l1', 'libv4l2']:
            pkg_config = PkgConfig(self, name)
            self.cpp_info.components[name].includedirs = []
            self.cpp_info.components[name].libdirs = []
            self.cpp_info.components[name].set_property("pkg_config_name", name)
            if pkg_config.version:
                self.cpp_info.components[name].set_property("component_version", pkg_config.version)
            pkg_config.fill_cpp_info(self.cpp_info.components[name],  is_system=True)
