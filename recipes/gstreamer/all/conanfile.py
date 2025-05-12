import os
import yaml

from functools import cached_property
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import is_apple_os, fix_apple_shared_install_name
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.microsoft import is_msvc, check_min_vs, is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=2.29"
_subprojects = ["bad", "base", "good", "ugly"]
_versions = ["1.26", "1.28"]

class GStreamerConan(ConanFile):
    name = "gstreamer"
    description = "GStreamer is a development framework for creating applications like media players, video editors, streaming media broadcasters and so on"
    topics = ("multimedia", "video", "audio", "broadcasting", "framework", "media")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gstreamer.freedesktop.org/"
    license = "LGPL-2.0-or-later"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "i18n": [True, False],
        "enable_backtrace": [True, False],
        "with_introspection": [True, False],
        "with_orc": [True, False],
        "tools": [True, False],
        "base": [True, False],
        "good": [True, False],
        "bad": [True, False],
        "ugly": [True, False],
        "libav": [True, False],
        "ges": [True, False],
        "rtsp_server": [True, False],
        "devtools": [True, False],

        # base
        "with_libdrm": [True, False],
        "with_libpng": [True, False],
        "with_libjpeg": [False, "libjpeg", "libjpeg-turbo", "mozjpeg"],
        "with_graphene": [True, False],
        "with_gl": [True, False],
        "with_egl": [True, False],
        "with_wayland": [True, False],
        "with_xorg": [True, False],

        # good
        "with_asm": [True, False],
        "with_egl": [True, False],
        "with_xorg": [True, False],

        # bad
        "with_cuda_nvmm": [True, False],
        "with_libssh2": [True, False],
        "with_libudev": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "i18n": False,
        "enable_backtrace": False,
        "with_introspection": False,
        "with_orc": False,
        "tools": True,  # required for gst-plugin-scanner
        "base": True,
        "good": True,
        "bad": True,
        "ugly": True,
        "libav": True,
        "ges": True,
        "rtsp_server": True,
        "devtools": True,

        # base
        "with_libdrm": False,
        "with_libpng": False,
        "with_libjpeg": False,
        "with_graphene": False,
        "with_gl": False,
        "with_egl": False,
        "with_wayland": False,
        "with_xorg": False,

        # good
        "with_asm": True,
        "with_egl": False,
        "with_xorg": False,

        # bad
        "with_cuda_nvmm": False,
        "with_libssh2": False,
        "with_libudev": False,
    }
    languages = "C", "C++"
    implements = ["auto_header_only"]

    @cached_property
    def _requirements(self):
        return yaml.safe_load(Path(self.recipe_folder, "requirements.yml").read_text())

    @cached_property
    def _plugin_infos(self):
        plugins = {}
        for v in _versions:
            plugins_for_version = {}
            for p in _subprojects:
                plugins_for_version[p] = yaml.safe_load(Path(self.recipe_folder, "plugins", v, f"{p}.yml").read_text())
            plugins[v] = plugins_for_version
        return plugins

    @cached_property
    def _option_infos(self):
        options = {}
        for v in _versions:
            options_for_version = {}
            for p in _subprojects:
                plugins = self._plugin_infos[v][p]
                options_for_version[p] = {plugins[info].get("options", [info])[0]: plugins[info] for info in plugins}
            options[v] = options_for_version
        return options

    @property
    def _current_version(self):
        version = Version(self.version)
        return f"{version.major}.{version.minor}"

    @property
    def _with_qt(self):
        return self.options.get_safe("qt5") or self.options.get_safe("qt6")

    @property
    def _qt_options(self):
        opts = {}
        opts["qtdeclarative"] = True
        opts["qtshadertools"] = True
        if self.settings.os in ["Linux", "FreeBSD"]:
            opts["with_x11"] = self.options.with_xorg
            opts["with_egl"] = self.options.with_egl
            opts["qtwayland"] = self.options.with_wayland
        return opts

    def init(self):
        def _compute_default_options(option_infos):
            def _default_option(option_info, option_infos):
                def _is_external_dep(dep):
                    if "::" not in dep:
                        return False
                    
                    # glib and gst-orc are not considered "external" dependencies
                    return dep.split("::")[0] not in ["glib", "gst-orc"]

                # if the option or any dependency option has a default value of
                # False, then the option is not enabled by default
                for option in option_info.get("options", []):
                    if option in self.options and not self.default_options.get(option, False):
                        return False

                for option in option_info.get("options", [])[1:]:
                    if not _default_option(option_infos[option], option_infos):
                        return False
                return not any(_is_external_dep(r) for r in option_info["requires"])

            return {info: _default_option(option_infos[info], option_infos) for info in option_infos}

        options = {}
        defaults = {}
        for v in _versions:
            for p in _subprojects:
                option_defaults = _compute_default_options(self._option_infos[v][p])
                options.update({o: [True, False] for o in option_defaults})
                for o in option_defaults:
                    defaults[o] = defaults.get(o, True) and option_defaults[o]
        self.options.update(options, defaults)

    def export(self):
        copy(self, "requirements.yml", self.recipe_folder, self.export_folder)
        copy(self, "plugins/*", self.recipe_folder, self.export_folder)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.pulse
            del self.options.shm
            del self.options.unixfd
        else:
            del self.options.directsound
            del self.options.waveform
            del self.options.amfcodec
            del self.options.d3d11
            del self.options.d3d12
            del self.options.d3dvideosink
            del self.options.directshow
            del self.options.dwrite
            del self.options.mediafoundation
            del self.options.qt6d3d11
            del self.options.wasapi
            del self.options.wic
            del self.options.win32ipc
            del self.options.winks
            del self.options.winscreencap
        if not is_msvc(self):
            # the required winrt library component only supports MSVC as of v1.24.12
            del self.options.wasapi2
        if self.settings.os not in ["Linux", "FreeBSD", "Windows"]:
            del self.options.enable_backtrace
        if self.settings.os not in ["Linux", "FreeBSD"]:
            del self.options.alsa
            del self.options.with_libdrm
            del self.options.with_egl
            del self.options.with_wayland
            del self.options.with_xorg
            del self.options.oss
            del self.options.oss4
            del self.options.v4l2
            del self.options.ximagesrc
            del self.options.dc1394
            del self.options.dvb
            del self.options.fbdev
            del self.options.kms
            if not is_apple_os(self):
                del self.options.openni2
                del self.options.zbar
                self.options.gtk3 = False
        if not is_apple_os(self):
            del self.options.applemedia
        if self.settings.os != "Macos":
            del self.options.osxaudio
            del self.options.osxvideo
        if self.settings.arch != "x86_64":
            del self.options.with_asm
        if self.settings.os not in ["Linux", "Windows"]:
            del self.options.nvcodec
            del self.options.va
        if self.settings.os != "Android":
            del self.options.androidmedia

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_gl:
            self.options.rm_safe("with_egl")
            self.options.rm_safe("with_wayland")
            self.options.rm_safe("with_graphene")
            # self.options.rm_safe("with_libpng") # TODO: is also required by gst-plugins-good if -o png=True
            # self.options.rm_safe("with_libjpeg") # TODO: is also required by gst-plugins-good if -o jpeg=True
        if not self.options.base:
            self.options.rm_safe("with_libdrm")
            self.options.rm_safe("with_xorg")

        if not self.options.curl:
            del self.options.with_libssh2
        if not self.options.vulkan and not self.options.librfb:
            self.options.rm_safe("with_xorg")

        active_options = set()
        for p in _subprojects:
            if self.options.get_safe(p, "False"):
                active_options.update(self._option_infos[self._current_version][p].keys())

        for p in _subprojects:
            if not self.options.get_safe(p, "False"):
                for option in self._option_infos[self._current_version][p]:
                    if option not in active_options:
                        self.options.rm_safe(option)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)
        if self.options.with_introspection:
            self.requires("gobject-introspection/1.78.1")

        all_reqs = set()

        if self.options.devtools:
            all_reqs.add("json-glib")

        if self.options.get_safe("enable_backtrace"):
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.requires("libunwind/[^1.8.1]")
                self.requires("elfutils/[^0.191]")

        if self.options.get_safe("with_xorg"):
            self.requires("xorg/system")

        if self.options.with_orc:
            self.requires("gst-orc/[^0.4.42]")

        if self.options.base:
            all_reqs.add("zlib")
            if self.options.with_gl:
                self.requires("opengl/system", transitive_headers=True, transitive_libs=True)
                if self.settings.os == "Windows":
                    self.requires("wglext/cci.20200813", transitive_headers=True, transitive_libs=True)
                    self.requires("glext/cci.20210420", transitive_headers=True, transitive_libs=True)
                    self.requires("khrplatform/cci.20200529", transitive_headers=True, transitive_libs=True)
                if self.options.get_safe("with_egl"):
                    self.requires("egl/system", transitive_headers=True, transitive_libs=True)
                if self.options.get_safe("with_wayland"):
                    self.requires("wayland/[^1.22.0]", transitive_headers=True, transitive_libs=True)
                if self.options.with_graphene:
                    self.requires("graphene/[^1.10.8]")
                if self.options.with_libpng:
                    all_reqs.add("libpng")
                if self.options.with_libjpeg:
                    all_reqs.add("libjpeg")

        if self.options.bad:
            if self.options.get_safe("curl") and self.options.with_libssh2:
                self.requires("libssh2/[^1.11.1]", options={"shared": True})
            if self.options.get_safe("with_libdrm"):
                all_reqs.add("libdrm")
            if self.options.get_safe("va") and self.options.get_safe("with_libudev"):
                all_reqs.add("libgudev")
            if self.options.get_safe("va"):
                if self.settings.os not in ["Linux", "FreeBSD"]:
                    all_reqs.add("libva")
                else:
                    self.requires("vaapi/system")
            if self.options.get_safe("webrtc"):
                all_reqs.add("libnice")
        
        if self.options.libav:
            all_reqs.add("ffmpeg")

        def _plugin_reqs(subproject):
            reqs = set()
            option_infos = self._option_infos[self._current_version][subproject]
            for option in option_infos:
                if self.options.get_safe(option, False):
                    reqs.update(r.split("::")[0] for r in option_infos[option].get("requires", []) if "::" in r)

            # glib and gst-orc dependencies are handled explicitely
            return reqs - {"glib", "gst-orc"}

        for p in _subprojects:
            if self.options.get_safe(p, "False"):
                all_reqs.update(_plugin_reqs(p))

        for req in all_reqs:
            if req == "libjpeg":
                if self.options.with_libjpeg == "libjpeg":
                    self.requires("libjpeg/9f")
                elif self.options.with_libjpeg == "libjpeg-turbo":
                    self.requires("libjpeg-turbo/[^3.0.2]")
                elif self.options.with_jpeg == "mozjpeg":
                    self.requires("mozjpeg/[^4.1.5]")
            elif req == "qt":
                ref = "qt/[>=6.7 <7]" if self.options.qt6 else "qt/[~5.15]"
                self.requires(ref, options={
                    **self._qt_options,
                    "qttools": can_run(self)
                })
            elif req == "opencv":
                self.requires("opencv/[^4.14.0]", options={"contrib": True})
            elif req == "vulkan-loader":
                self.requires("vulkan-loader/[~1.4]")
                if self.options.get_safe("with_wayland") or self.options.get_safe("with_xorg"):
                    self.requires("xkbcommon/[^1.6.0]")
                if is_apple_os(self):
                    self.requires("moltenvk/[^1.2.2]")
            elif req == "opengl":
                pass # added above
            else:
                self.requires(f"{req}/{self._requirements[req]}")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("glib/<host_version>")
        if self.options.i18n:
            self.tool_requires("gettext/[>=0.21 <1]")
        if self.options.with_introspection:
            self.tool_requires("gobject-introspection/<host_version>")
        if self.settings_build.os == "Windows":
            self.tool_requires("winflexbison/[^2.5.25]")
        else:
            self.tool_requires("bison/[^3.8.2]")
            self.tool_requires("flex/[^2.6.4]")

        if self.options.with_orc:
            self.tool_requires("gst-orc/<host_version>")

        if self.options.base:
            if self.options.get_safe("with_wayland"):
                self.tool_requires("wayland/<host_version>")

        if self.options.good:
            if self.options.get_safe("with_asm"):
                self.tool_requires("nasm/[^2.16]")
        if self._with_qt and not can_run(self):
            self.tool_requires("qt/<host_version>", options={
                **self._qt_options,
                "qttools": True
            })

        if self.options.bad:
            if self.options.get_safe("vulkan"):
                self.tool_requires("shaderc/2025.3")

    def validate_build(self):
        if self.options.get_safe("qt6d3d11") or self.options.get_safe("zxing"):
            check_min_cppstd(self, 17)
        elif self.options.get_safe("nvcodec") or self.options.get_safe("soundtouch"):
            check_min_cppstd(self, 14)
        elif self.options.get_safe("opencv") or self.options.get_safe("applemedia"):
            check_min_cppstd(self, 11)

    def validate(self):
        if not self.dependencies.direct_host["glib"].options.shared and self.options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("shared GStreamer cannot link to static GLib")
        if self.options.with_introspection and not self.options.shared:
            raise ConanInvalidConfiguration("-o with_introspection=True requires -o shared=True")
        if Version(self.version) >= "1.18.2" and self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration(f"GStreamer {self.version} does not support gcc older than 5")
        if self.options.with_gl and self.options.get_safe("with_wayland") and not self.options.get_safe("with_egl"):
            raise ConanInvalidConfiguration("OpenGL support with Wayland requires 'with_egl' turned on!")
        if self.options.good and not self.options.base:
            raise ConanInvalidConfiguration("-o good=True requires -o base=True")
        if self.options.bad and not self.options.base:
            raise ConanInvalidConfiguration("-o bad=True requires -o base=True")
        if self.options.ugly and not self.options.base:
            raise ConanInvalidConfiguration("-o ugly=True requires -o base=True")
        if self.options.libav and not self.options.base:
            raise ConanInvalidConfiguration("-o libav=True requires -o base=True")
        if self.options.ges and not self.options.base:
            raise ConanInvalidConfiguration("-o ges=True requires -o base=True")
        if self.options.rtsp_server and not self.options.base:
            raise ConanInvalidConfiguration("-o rtsp_server=True requires -o base=True")
        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("shared build with static runtime is not supported due to the FlsAlloc limit")
        if self.options.get_safe("qt5") and self.options.get_safe("qt6"):
            raise ConanInvalidConfiguration("only one of with_qt=True and with_qt6=True can be enabled")
        if self._with_qt and not self.options.with_gl:
            raise ConanInvalidConfiguration("-o with_qt=True requires -o with_gl=True")
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "5":
            raise ConanInvalidConfiguration(f"{self.ref} does not support gcc older than 5")
        if self.options.get_safe("curl"):
            if is_msvc(self):
                # Requires unistd.h
                raise ConanInvalidConfiguration("-o curl=True is not compatible with MSVC")
            if self.options.with_libssh2 and not self.dependencies["libssh2"].options.shared:
                raise ConanInvalidConfiguration("libssh2 must be built as a shared library")
        if self.options.get_safe("directshow") and not is_msvc(self):
            raise ConanInvalidConfiguration("directshow plugin can only be built with MSVC")

        for project in self._option_infos[self._current_version]:
            for option, option_info in self._option_infos[self._current_version][project].items():
                if self.options.get_safe(option):
                    unsatisfied_options = [o for o in option_info.get("options", []) if not self.options.get_safe(o)]
                    if any(unsatisfied_options):
                        raise ConanInvalidConfiguration(f"-o {option}=True requires -o {unsatisfied_options[0]}=True")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _gl_config(self):
        gl_api = set()
        gl_platform = set()
        gl_winsys = set()  # TODO: winrt, dispamnx, surfaceless, viv-fb, gbm, android
        if self.options.get_safe("with_egl"):
            gl_api.add("opengl")
            gl_platform.add("egl")
            gl_winsys.add("egl")
        if self.options.get_safe("with_xorg"):
            gl_api.add("opengl")
            gl_platform.add("glx")
            gl_winsys.add("x11")
        if self.options.get_safe("with_wayland"):
            gl_api.add("opengl")
            gl_platform.add("egl")
            gl_winsys.add("wayland")
        if self.settings.os == "Macos":
            gl_api.add("opengl")
            gl_platform.add("cgl")
            gl_winsys.add("cocoa")
        elif is_apple_os(self):
            gl_api.add("gles2")
            gl_platform.add("eagl")
            gl_winsys.add("eagl")
        elif self.settings.os == "Windows":
            gl_api.add("opengl")
            gl_platform.add("wgl")
            gl_winsys.add("win32")
        return list(gl_api), list(gl_platform), list(gl_winsys)

    def generate(self):
        def feature(v):
            return "enabled" if v else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"

        if is_msvc(self) and not check_min_vs(self, 190, raise_invalid=False):
            tc.c_link_args.append("-Dsnprintf=_snprintf")
            tc.project_options["c_std"] = "c99"

        def feature(value):
            return "enabled" if value else "disabled"

        tc.project_options["gst-full"] = "disabled"
        tc.project_options["gst-full-target-type"] = "static_library"
        tc.project_options["base"] = feature(self.options.base)
        tc.project_options["good"] = feature(self.options.base)
        tc.project_options["bad"] = feature(self.options.bad)
        tc.project_options["ugly"] = feature(self.options.bad)
        tc.project_options["libav"] = feature(self.options.libav)
        tc.project_options["ges"] = feature(self.options.ges)
        tc.project_options["rtsp_server"] = feature(self.options.rtsp_server)
        tc.project_options["devtools"] = feature(self.options.devtools)
        tc.project_options["rs"] = "disabled"
        tc.project_options["gst-examples"] = "disabled"
        tc.project_options["python"] = "disabled"
        tc.project_options["python-exe"] = "disabled"
        tc.project_options["sharp"] = "disabled"
        tc.project_options["tls"] = "disabled"
        tc.project_options["libnice"] = "disabled"
        tc.project_options["build-tools-source"] = "system"
        tc.project_options["introspection"] = feature(self.options.with_introspection)
        tc.project_options["tools"] = feature(self.options.tools)
        tc.project_options["doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["benchmarks"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["nls"] = feature(self.options.i18n)
        tc.project_options["gpl"] = "enabled"  # only applies to libx264 and libx265 currently

        if self.version < "1.28":
            tc.project_options["vaapi"] = "disabled"

        ## gstreamer
        gstreamer_options = dict()
        gstreamer_options["check"] = "enabled"  # explicitly enable plugin
        gstreamer_options["coretracers"] = "enabled"  # explicitly enable plugin
        gstreamer_options["libunwind"] = feature(self.options.get_safe("enable_backtrace") and self.settings.os in ["Linux", "FreeBSD"])
        gstreamer_options["libdw"] = feature(self.options.get_safe("enable_backtrace") and self.settings.os in ["Linux", "FreeBSD"])
        gstreamer_options["dbghelp"] = feature(self.options.get_safe("enable_backtrace") and self.settings.os == "Windows")
        gstreamer_options["bash-completion"] = "disabled"
        gstreamer_options["ptp-helper"] = "disabled"  # requires rustc and libcap

        tc.subproject_options["gstreamer"] = [gstreamer_options]

        ## orc
        tc.project_options["orc"] = feature(self.options.with_orc)
        if self.version >= "1.28":
            tc.project_options["orc-compiler"] = feature(self.options.with_orc)
        tc.project_options["orc-source"] = "system"
        if self.options.with_orc:
            if not self.dependencies["gst-orc"].options.shared:
                # The define is not propagated correctly in the Meson build scripts
                tc.extra_defines.append("ORC_STATIC_COMPILATION")

        ## gst-plugins-base
        if self.options.base:
            base_options = dict()
            gl_api, gl_platform, gl_winsys = self._gl_config()
            for opt in self._option_infos[self._current_version]["base"].keys() - {"with_xorg"}:
                base_options[opt] = feature(self.options.get_safe(opt))

            # OpenGL integration library options
            base_options["gl_api"] = gl_api
            base_options["gl_platform"] = gl_platform
            base_options["gl_winsys"] = gl_winsys

            # Feature option for opengl plugin and integration library
            base_options["gl"] = feature(self.options.with_gl)
            base_options["gl-graphene"] = feature(self.options.with_gl and self.options.with_graphene)
            base_options["gl-jpeg"] = feature(self.options.with_gl and self.options.with_libjpeg)
            base_options["gl-png"] = feature(self.options.with_gl and self.options.with_libpng)

            # Feature options
            base_options["cdparanoia"] = "disabled"  # TODO: cdparanoia
            base_options["drm"] = feature(self.options.get_safe("with_libdrm"))
            base_options["libvisual"] = "disabled"  # TODO: libvisual
            base_options["tremor"] = "disabled"  # TODO: tremor - only useful on machines without floating-point support
            base_options["x11"] = feature(self.options.get_safe("with_xorg"))
            base_options["xshm"] = feature(self.options.get_safe("with_xorg"))
            base_options["xvideo"] = feature(self.options.get_safe("with_xorg"))
            base_options["xi"] = feature(self.options.get_safe("with_xorg"))

            # Common feature options
            base_options["iso-codes"] = "disabled"  # requires iso-codes package

            tc.subproject_options["gst-plugins-base"] = [base_options]

        if self.options.good:
            good_options = dict()
            for opt in self._option_infos[self._current_version]["good"].keys():
                good_options[opt] = feature(self.options.get_safe(opt))

            # Feature options for plugins with external deps
            good_options["aalib"] = "disabled"  # TODO: libaa1
            good_options["amrnb"] = "disabled"  # TODO: libopencore-amrnb
            good_options["amrwbdec"] = "disabled"  # TODO: libopencore-amrwbdec
            good_options["dv"] = "disabled"  # TODO: libdv4
            good_options["dv1394"] = "disabled"  # TODO: libraw1394, libavc1394, libiec61883
            good_options["jack"] = "enabled"  # requires libjack, but only via dlopen
            good_options["rpicamsrc"] = "disabled"  # Raspberry Pi camera module plugin
            good_options["shout2"] = "disabled"  # TODO: libshout
            good_options["speex"] = "disabled"  # TODO: libspeex
            good_options["twolame"] = "disabled"  # TODO: libtwolame
            good_options["wavpack"] = "disabled"  # TODO: libwavpack

            # HLS plugin options
            if self.options.adaptivedemux2:
                good_options["hls-crypto"] = "openssl"

            # Qt plugin options
            good_options["qt-method"] = "pkg-config"
            good_options["qt-egl"] = feature(self.options.get_safe("with_egl"))
            good_options["qt-wayland"] = feature(self.options.get_safe("with_wayland"))
            good_options["qt-x11"] = feature(self.options.get_safe("with_xorg"))

            # ximagesrc plugin options
            good_options["ximagesrc-xshm"] = feature(self.options.get_safe("ximagesrc"))
            good_options["ximagesrc-xfixes"] = feature(self.options.get_safe("ximagesrc"))
            good_options["ximagesrc-xdamage"] = feature(self.options.get_safe("ximagesrc"))
            good_options["ximagesrc-navigation"] = feature(self.options.get_safe("ximagesrc"))

            # Common feature options
            good_options["asm"] = feature(self.options.get_safe("with_asm"))

            tc.subproject_options["gst-plugins-good"] = [good_options]

        if self.options.bad:
            bad_options = dict()
            for opt in self._option_infos[self._current_version]["bad"].keys() - {"with_wayland"}:
                bad_options[opt] = feature(self.options.get_safe(opt))

            # Feature options for plugins that need external deps
            bad_options["aja"] = "disabled"  # libajantv2
            bad_options["asio"] = "disabled"  # proprietary
            bad_options["assrender"] = "disabled"  # libass
            bad_options["avtp"] = "disabled"  # avtp
            bad_options["bluez"] = "disabled"  # bluez
            bad_options["bs2b"] = "disabled"  # libbs2b
            bad_options["chromaprint"] = "disabled"  # libchromaprint
            bad_options["dts"] = "disabled"  # libdca (GPL)
            bad_options["faad"] = "disabled"  # faad2 (GPL)
            bad_options["flite"] = "disabled"  # flite
            bad_options["fluidsynth"] = "disabled"  # fluidsynth
            bad_options["gme"] = "disabled"  # gme
            bad_options["gsm"] = "disabled"  # libgsm1
            bad_options["iqa"] = "disabled"  # kornelski/dssim (GPL)
            bad_options["isac"] = "disabled"  # webrtc-audio-coding-1
            bad_options["ladspa"] = "disabled"  # ladspa-sdk
            bad_options["ladspa-rdf"] = "disabled"
            bad_options["lc3"] = "disabled"  # lc3
            if Version(self.version) >= "1.26":
                bad_options["lcevcdecoder"] = "disabled"  # lcevc
                bad_options["lcevcencoder"] = "disabled"  # lcevc
            bad_options["ldac"] = "disabled"  # ldacbt
            bad_options["lv2"] = "disabled"  # lilv
            bad_options["magicleap"] = "disabled"  # proprietary
            bad_options["microdns"] = "disabled"  # libmicrodns
            bad_options["mpeg2enc"] = "disabled"  # mjpegtools (GPL)
            bad_options["mplex"] = "disabled"  # mjpegtools (GPL)
            bad_options["msdk"] = "disabled"  # Intel Media SDK or oneVPL SDK
            bad_options["musepack"] = "disabled"  # libmpcdec
            bad_options["neon"] = "disabled"  # libneon27
            if Version(self.version) >= "1.26":
                bad_options["nvcomp"] = "disabled" # NVIDIA nvCOMP
                bad_options["nvdswrapper"] = "disabled" # NVIDIA DeepStream SDK
            bad_options["openaptx"] = "disabled"  # openaptx
            bad_options["openmpt"] = "disabled"  # openmpt
            bad_options["opensles"] = "disabled"  # opensles
            bad_options["resindvd"] = "disabled"  # dvdnav (GPL)
            bad_options["rtmp"] = "disabled"  # librtmp
            bad_options["sbc"] = "disabled" # libsbc
            bad_options["spandsp"] = "disabled"  # spandsp
            bad_options["svthevcenc"] = "disabled"  # svt-hevc
            bad_options["teletext"] = "disabled"  # zvbi
            bad_options["voaacenc"] = "disabled"  # vo-aacenc
            bad_options["webrtcdsp"] = "disabled"  # webrtc-audio-processing-1
            bad_options["webview2"] = "disabled"  # WebView2 Windows system lib
            bad_options["wpe"] = "disabled"  # wpe-webkit

            bad_options["cuda-nvmm"] = feature(self.options.with_cuda_nvmm)
            bad_options["drm"] = feature(self.options.get_safe("with_libdrm"))
            bad_options["udev"] = feature(self.options.get_safe("va") and self.options.get_safe("with_libudev"))
            bad_options["gl"] = feature(self.options.get_safe("with_gl"))
            bad_options["wayland"] = feature(self.options.get_safe("with_wayland"))
            bad_options["x11"] = feature(self.options.get_safe("with_xorg"))
            bad_options["curl-ssh2"] = feature(self.options.get_safe("with_libssh2"))
            bad_options["hls-crypto"] = "openssl"
            bad_options["vulkan-video"] = "enabled"
            bad_options["sctp-internal-usrsctp"] = "disabled"

            tc.subproject_options["gst-plugins-bad"] = [bad_options]

        if self.options.ugly:
            ugly_options = dict()
            for opt in self._option_infos[self._current_version]["ugly"].keys():
                ugly_options[opt] = feature(self.options.get_safe(opt))

            ugly_options["a52dec"] = "disabled"  # liba52
            ugly_options["cdio"] = "disabled"  # libcdio
            ugly_options["dvdread"] = "disabled"  # dvdread
            ugly_options["mpeg2dec"] = "disabled"  # libmpeg2
            ugly_options["sidplay"] = "disabled"  # sidplay

            tc.subproject_options["gst-plugins-ugly"] = [ugly_options]

        if self.options.ges:
            ges_options = dict()
       
            ges_options["bash-completion"] = "disabled"
            ges_options["xptv"] = "disabled"
            ges_options["python"] = "disabled"
            ges_options["validate"] = feature(self.options.devtools)

            tc.subproject_options["gst-editing-services"] = [ges_options]

        if self.options.devtools:
            devtools_options = dict()
       
            devtools_options["dots_viewer"] = "disabled"
            devtools_options["cairo"] = "disabled"
            devtools_options["debug_viewer"] = "disabled"

            tc.subproject_options["gst-devtools"] = [devtools_options]

        # make sure the GLib tools of the *build* dependency are used, not the ones from the host 
        glib_build_tools = [
            "gdbus-codegen",
            "gio-querymodules",
            "glib-compile-resources",
            "glib-compile-schemas",
            "glib-genmarshal",
            "glib-mkenums",
        ]
        tc.binaries = {
            tool: os.path.join(self.dependencies.build["glib"].package_folder, "bin", tool) for tool in glib_build_tools
        }
            
        tc.generate()

        deps = PkgConfigDeps(self)
        deps.set_property("libmp3lame", "pkg_config_name", "mp3lame")
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _fix_library_names(self, path):
        if is_msvc(self):
            for filename_old in Path(path).glob("*.a"):
                filename_new = str(filename_old)[:-2] + ".lib"
                rename(self, filename_old, filename_new)

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        self._fix_library_names(os.path.join(self.package_folder, "lib"))
        self._fix_library_names(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        rename(self, os.path.join(self.package_folder, "share"), os.path.join(self.package_folder, "res"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rm(self, "*.pdb", self.package_folder, recursive=True)
        fix_apple_shared_install_name(self)

    def package_info(self):
        def _define_library(name, extra_requires, interface=False, lib=None):
            component_name = f"gstreamer-{name}-1.0"
            component = self.cpp_info.components[component_name]
            component.set_property("pkg_config_name", component_name)
            component.set_property("cmake_target_name", f"GStreamer::{component_name}")
            component.set_property("pkg_config_name", component_name)
            if not self.options.with_orc:
                extra_requires = [r for r in extra_requires if r.split("::")[0] != "gst-orc"]
            component.requires = [
                                     "gstreamer-1.0",
                                     "gstreamer-base-1.0",
                                     "glib::gobject-2.0",
                                     "glib::glib-2.0",
                                 ] + extra_requires
            if not interface:
                component.libs = [lib or f"gst{name.replace('-', '')}-1.0"]
                component.includedirs = [os.path.join("include", "gstreamer-1.0")]
                component.set_property("pkg_config_custom_content", pkgconfig_custom_content)
                if self.settings.os in ["Linux", "FreeBSD"]:
                    component.system_libs = ["m"]
            return component

        def _define_plugin(plugin, plugin_info):
            plugin_name = f"gst{plugin}"

            extra_requires = plugin_info.get("requires", [])
            if not self.options.with_orc:
                extra_requires = [r for r in extra_requires if r.split("::")[0] != "gst-orc"]
                
            component = self.cpp_info.components[plugin_name]
            component.requires = [
                                     "gstreamer-1.0",
                                     "gstreamer-base-1.0",
                                     "glib::gobject-2.0",
                                     "glib::glib-2.0",
                                 ] + extra_requires
            component.includedirs = []
            component.bindirs = []
            component.resdirs = ["share"]
            component.set_property("pkg_config_name", plugin_name)
            component.set_property("cmake_target_name", f"GStreamer::{plugin_name}")
            if self.options.shared:
                component.bindirs.append(os.path.join("lib", "gstreamer-1.0"))
            else:
                component.libs = [plugin_name]
                component.libdirs = [os.path.join("lib", "gstreamer-1.0")]
                if self.settings.os in ["Linux", "FreeBSD"]:
                    component.system_libs = ["m", "dl"]
            return component

        def _is_enabled(plugin, plugin_info):
            required_options = plugin_info.get("options", [plugin])
            return all(self.options.get_safe(opt, False) for opt in required_options)

        pkgconfig_variables = {
            "exec_prefix": "${prefix}",
            "toolsdir": "${exec_prefix}/bin",
            "pluginsdir": "${prefix}/lib/gstreamer-1.0",
            "datarootdir": "${prefix}/share",
            "datadir": "${datarootdir}",
            "girdir": "${datadir}/gir-1.0",
            "typelibdir": "${prefix}/lib/girepository-1.0",
            "libexecdir": "${prefix}/libexec",
            "pluginscannerdir": "${libexecdir}/gstreamer-1.0",
        }
        pkgconfig_custom_content = "\n".join(f"{key}={value}" for key, value in pkgconfig_variables.items())

        self.cpp_info.set_property("cmake_file_name", "GStreamer")
        self.cpp_info.set_property("cmake_target_name", "GStreamer::GStreamer")

        self.cpp_info.components["gstreamer-1.0"].set_property("pkg_config_name", "gstreamer-1.0")
        self.cpp_info.components["gstreamer-1.0"].set_property("cmake_target_name", "GStreamer::gstreamer-1.0")
        self.cpp_info.components["gstreamer-1.0"].requires = ["glib::glib-2.0", "glib::gobject-2.0"]
        self.cpp_info.components["gstreamer-1.0"].libs = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        self.cpp_info.components["gstreamer-1.0"].bindirs = ["bin", os.path.join("bin", "gstreamer-1.0")]
        if not self.options.shared:
            self.cpp_info.components["gstreamer-1.0"].requires.append("glib::gmodule-no-export-2.0")
        if self.options.shared:
            self.cpp_info.components["gstreamer-1.0"].bindirs.append(os.path.join("lib", "gstreamer-1.0"))
        self.cpp_info.components["gstreamer-1.0"].resdirs = ["share"]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-1.0"].system_libs = ["m", "dl"]
        if self.options.get_safe("enable_backtrace"):
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["gstreamer-1.0"].requires.extend([
                    "libunwind::unwind",
                    "elfutils::libdw",
                ])
            elif self.settings.os == "Windows":
                self.cpp_info.components["gstreamer-1.0"].system_libs.append("dbghelp")
        self.cpp_info.components["gstreamer-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-base-1.0"].set_property("pkg_config_name", "gstreamer-base-1.0")
        self.cpp_info.components["gstreamer-base-1.0"].set_property("cmake_target_name", "GStreamer::gstreamer-base-1.0")
        self.cpp_info.components["gstreamer-base-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].libs = ["gstbase-1.0"]
        self.cpp_info.components["gstreamer-base-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        self.cpp_info.components["gstreamer-base-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-controller-1.0"].set_property("pkg_config_name", "gstreamer-controller-1.0")
        self.cpp_info.components["gstreamer-controller-1.0"].set_property("cmake_target_name", "GStreamer::gstreamer-controller-1.0")
        self.cpp_info.components["gstreamer-controller-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].libs = ["gstcontroller-1.0"]
        self.cpp_info.components["gstreamer-controller-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-controller-1.0"].system_libs = ["m"]
        self.cpp_info.components["gstreamer-controller-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-net-1.0"].set_property("pkg_config_name", "gstreamer-net-1.0")
        self.cpp_info.components["gstreamer-net-1.0"].set_property("cmake_target_name", "GStreamer::gstreamer-net-1.0")
        self.cpp_info.components["gstreamer-net-1.0"].requires = ["gstreamer-1.0", "glib::gio-2.0"]
        if Version(self.version) >= "1.21.1" and self.settings.os != "Windows":
            self.cpp_info.components["gstreamer-net-1.0"].requires.append("glib::gio-unix-2.0")
        self.cpp_info.components["gstreamer-net-1.0"].libs = ["gstnet-1.0"]
        self.cpp_info.components["gstreamer-net-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        self.cpp_info.components["gstreamer-net-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        self.cpp_info.components["gstreamer-check-1.0"].set_property("pkg_config_name", "gstreamer-check-1.0")
        self.cpp_info.components["gstreamer-check-1.0"].set_property("cmake_target_name", "GStreamer::gstreamer-check-1.0")
        self.cpp_info.components["gstreamer-check-1.0"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].libs = ["gstcheck-1.0"]
        self.cpp_info.components["gstreamer-check-1.0"].includedirs = [os.path.join("include", "gstreamer-1.0")]
        if self.settings.os == "Linux":
            self.cpp_info.components["gstreamer-check-1.0"].system_libs = ["rt", "m"]
        self.cpp_info.components["gstreamer-check-1.0"].set_property("pkg_config_custom_content", pkgconfig_custom_content)

        # gstcoreelements and gstcoretracers are plugins which should be loaded dynamically, and not linked to directly
        self.cpp_info.components["gstcoreelements"].set_property("pkg_config_name", "gstcoreelements")
        self.cpp_info.components["gstcoreelements"].set_property("cmake_target_name", "GStreamer::gstcoreelements")
        self.cpp_info.components["gstcoreelements"].requires = ["glib::gobject-2.0", "glib::glib-2.0", "gstreamer-1.0", "gstreamer-base-1.0"]
        self.cpp_info.components["gstcoreelements"].libdirs = [os.path.join("lib", "gstreamer-1.0")]
        if not self.options.shared:
            self.cpp_info.components["gstcoreelements"].libs = ["gstcoreelements"]

        self.cpp_info.components["gstcoretracers"].set_property("pkg_config_name", "gstcoretracers")
        self.cpp_info.components["gstcoretracers"].set_property("cmake_target_name", "GStreamer::gstcoretracers")
        self.cpp_info.components["gstcoretracers"].requires = ["gstreamer-1.0"]
        self.cpp_info.components["gstcoretracers"].libdirs = [os.path.join("lib", "gstreamer-1.0")]
        if not self.options.shared:
            self.cpp_info.components["gstcoretracers"].libs = ["gstcoretracers"]

        if self.options.shared:
            self.runenv_info.define_path("GST_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        gstreamer_root = self.package_folder
        gst_plugin_scanner = "gst-plugin-scanner.exe" if self.settings.os == "Windows" else "gst-plugin-scanner"
        gst_plugin_scanner = os.path.join(self.package_folder, "bin", "gstreamer-1.0", gst_plugin_scanner)
        self.runenv_info.define_path("GSTREAMER_ROOT", gstreamer_root)
        self.runenv_info.define_path("GST_PLUGIN_SCANNER", gst_plugin_scanner)
        if self.settings.arch == "x86":
            self.runenv_info.define_path("GSTREAMER_ROOT_X86", gstreamer_root)
        elif self.settings.arch == "x86_64":
            self.runenv_info.define_path("GSTREAMER_ROOT_X86_64", gstreamer_root)

        if self.options.with_introspection:
            self.cpp_info.components["gstreamer-1.0"].requires.append("gobject-introspection::gobject-introspection")
            self.buildenv_info.append_path("GI_GIR_PATH", os.path.join(self.package_folder, "share", "gir-1.0"))
            self.runenv_info.append_path("GI_TYPELIB_PATH", os.path.join(self.package_folder, "lib", "girepository-1.0"))

        aclocal_path = os.path.join(self.package_folder, "share", "aclocal")
        self.buildenv_info.append_path("ACLOCAL_PATH", aclocal_path)
        
        if self.options.devtools:
            _define_library("validate", [
                "gstreamer-app-1.0",
                "gstreamer-check-1.0",
                "gstreamer-controller-1.0",
                "gstreamer-pbutils-1.0",
                "json-glib::json-glib",
            ])

        if self.options.base:
            # Libraries
            gst_allocators = _define_library("allocators", [])
            if self.options.get_safe("with_libdrm"):
                gst_allocators.requires.append("libdrm::libdrm")
            _define_library("app", [])
            _define_library("audio", [
                "gstreamer-tag-1.0",
                "gst-orc::gst-orc",
            ])
            _define_library("fft", [])
            _define_library("pbutils", [
                "gstreamer-audio-1.0",
                "gstreamer-video-1.0",
                "gstreamer-tag-1.0",
            ])
            _define_library("riff", [
                "gstreamer-audio-1.0",
                "gstreamer-tag-1.0",
            ])
            _define_library("rtp", [
                "gstreamer-audio-1.0",
            ])
            gst_rtsp = _define_library("rtsp", [
                "gstreamer-sdp-1.0",
                "glib::gio-2.0",
            ])
            if self.settings.os == "Windows":
                gst_rtsp.system_libs = ["ws2_32"]
            _define_library("sdp", [
                "gstreamer-rtp-1.0",
                "gstreamer-pbutils-1.0",
                "glib::gio-2.0",
            ])
            _define_library("tag", [
                "zlib::zlib",
            ])
            _define_library("video", [
                "gst-orc::gst-orc",
            ])
            if self.options.with_gl:
                gst_gl = _define_library("gl", [
                    "gstreamer-allocators-1.0",
                    "gstreamer-video-1.0",
                    "glib::gmodule-no-export-2.0",
                    "opengl::opengl",
                    # TODO: bcm
                ])
                gst_gl.includedirs.append(os.path.join("lib", "gstreamer-1.0", "include"))
                gl_api, gl_platform, gl_winsys = self._gl_config()
                gl_variables = {
                    **pkgconfig_variables,
                    "gl_apis": " ".join(gl_api),
                    "gl_platforms": " ".join(gl_platform),
                    "gl_winsys": " ".join(gl_winsys),
                }
                gl_custom_content = "\n".join(f"{key}={value}" for key, value in gl_variables.items())
                gst_gl.set_property("pkg_config_custom_content", gl_custom_content)

                if self.options.get_safe("with_egl"):
                    gst_gl.requires += ["egl::egl"]
                if self.options.get_safe("with_xorg"):
                    gst_gl.requires += ["xorg::x11", "xorg::x11-xcb"]
                if self.options.get_safe("with_wayland"):
                    gst_gl.requires += [
                        "wayland::wayland-client",
                        "wayland::wayland-cursor",
                        "wayland::wayland-egl",
                    ]
                if self.settings.os == "Windows":
                    gst_gl.requires += [
                        "glext::glext",
                        "wglext::wglext",
                        "khrplatform::khrplatform",
                    ]
                    gst_gl.system_libs = ["gdi32"]
                if is_apple_os(self):
                    gst_gl.frameworks = [
                        "CoreFoundation",
                        "Foundation",
                        "QuartzCore",
                        "Cocoa",
                    ]
                if self.settings.os in ["iOS", "tvOS", "watchOS"]:
                    gst_gl.frameworks.extend(["CoreGraphics", "UIkit"])
                gst_gl.includedirs.append("include")
                gst_gl.includedirs.append(os.path.join("lib", "gstreamer-1.0", "include"))

                _define_library("gl-prototypes", [
                    "gstreamer-gl-1.0",
                    "opengl::opengl",
                ], interface=True)

                if self.options.get_safe("with_egl"):
                    _define_library("gl-egl", [
                        "gstreamer-gl-1.0",
                        "egl::egl",
                    ], interface=True)

                if self.options.get_safe("with_wayland"):
                    _define_library("gl-wayland", [
                        "gstreamer-gl-1.0",
                        "wayland::wayland-client",
                        "wayland::wayland-egl",
                    ], interface=True)

                if self.options.get_safe("with_xorg"):
                    _define_library("gl-x11", [
                        "gstreamer-gl-1.0",
                        "xorg::x11-xcb",
                    ], interface=True)

            plugin_infos = self._plugin_infos[self._current_version]["base"]
            for plugin in plugin_infos:
                if _is_enabled(plugin, plugin_infos[plugin]):
                    _define_plugin(plugin, plugin_infos[plugin])

            if self.options.with_gl:
                gstopengl = _define_plugin("opengl", {
                    "requires": [
                        "gstreamer-controller-1.0",
                        "gstreamer-video-1.0",
                        "gstreamer-allocators-1.0",
                        "opengl::opengl",
                        # TODO: bcm
                        # TODO: nvbuf_utils
                ]})
                if is_apple_os(self):
                    gstopengl.frameworks = ["CoreFoundation", "Foundation", "QuartzCore"]
                if self.options.with_graphene:
                    gstopengl.requires.append("graphene::graphene-gobject-1.0")
                if self.options.with_libpng:
                    gstopengl.requires.append("libpng::libpng")
                if self.options.with_libjpeg == "libjpeg":
                    gstopengl.requires.append("libjpeg::libjpeg")
                elif self.options.with_libjpeg == "libjpeg-turbo":
                    gstopengl.requires.append("libjpeg-turbo::libjpeg-turbo")
                elif self.options.with_libjpeg == "mozjpeg":
                    gstopengl.requires.append("mozjpeg::mozjpeg")
                if self.options.get_safe("with_xorg"):
                    gstopengl.requires.append("xorg::x11")

        if self.options.good:
            plugin_infos = self._plugin_infos[self._current_version]["good"]
            for plugin in plugin_infos:
                if _is_enabled(plugin, plugin_infos[plugin]):
                    _define_plugin(plugin, plugin_infos[plugin])

            # directsound
            if self.options.get_safe("directsound"):
                gst_directsound = self.cpp_info.components["gstdirectsound"]
                gst_directsound.system_libs = ["dsound", "winmm", "ole32"]

            # osxaudio
            if self.options.get_safe("osxaudio"):
                gst_osxaudio = self.cpp_info.components["gstosxaudio"]
                gst_osxaudio.frameworks = ["CoreAudio", "AudioToolbox"]
                if self.settings.os == "Macos":
                    gst_osxaudio.frameworks.extend(["AudioUnit", "CoreServices"])
                if self.settings.os == "iOS":
                    gst_osxaudio.frameworks.extend(["AVFAudio", "Foundation"])

            # osxvideo
            if self.options.get_safe("osxvideo"):
                gst_osxvideo = self.cpp_info.components["gstosxvideo"]
                gst_osxvideo.frameworks = ["OpenGL", "Cocoa"]

            # qml6
            if self._with_qt:
                qt_major = Version(self.dependencies["qt"].ref.version).major
                qt_plugin = self.cpp_info.components["gstqml6" if qt_major == 6 else "gstqmlgl"]
                if self.options.get_safe("with_xorg"):
                    qt_plugin.requires.append("gstreamer-gl-x11-1.0")
                if self.options.get_safe("with_wayland"):
                    qt_plugin.requires.append("gstreamer-gl-wayland-1.0")
                    qt_plugin.requires.append("qt::qtWaylandClient")
                if self.options.get_safe("with_egl"):
                    qt_plugin.requires.append("gstreamer-gl-egl-1.0")
                if self.settings.os == "Windows":
                    qt_plugin.system_libs.append("opengl32")
                if qt_major == 5:
                    if self.options.get_safe("with_xorg"):
                        qt_plugin.requires.append("qt::qtX11Extras")
                    if self.settings.os == "Android":
                        qt_plugin.requires.append("qt::qtAndroidExtras")
                        qt_plugin.system_libs.append("GLESv2")
                    if is_apple_os(self):
                        qt_plugin.requires.append("qt::qtMacExtras")

            # waveform
            if self.options.get_safe("waveform"):
                gst_wf = self.cpp_info.components["gstwaveform"]
                gst_wf.system_libs = ["winmm"]

        if self.options.bad:
            # Libraries

            # adaptivedemux
            _define_library("adaptivedemux", [
                "gstreamer-downloader-1.0",
            ])
            # analytics
            _define_library("analytics", [
                "gstreamer-video-1.0",
            ])
            # bad-audio
            _define_library("bad-audio", [
                "gstreamer-audio-1.0",
            ])
            # bad-base-camerabinsrc
            _define_library("bad-base-camerabinsrc", [
                "gstreamer-app-1.0",
            ], lib="gstbasecamerabinsrc-1.0")
            # codecparsers
            _define_library("codecparsers", [])
            # codecs
            _define_library("codecs", [
                "gstreamer-codecparsers-1.0",
                "gstreamer-video-1.0",
            ])
            # cuda
            if self.settings.os in ["Linux", "Windows"] and self.options.get_safe("with_gl"):
                gst_cuda = _define_library("cuda", [
                    "gstreamer-video-1.0",
                    "gstreamer-gl-prototypes-1.0",
                    "glib::gmodule-no-export-2.0",
                    "opengl::opengl",
                ])
                if self.options.with_cuda_nvmm:
                    gst_cuda.system_libs.append("nvbufsurface")
                if self.settings.os == "Linux" and self.settings.arch not in ["x86", "x86_64"]:
                    gst_cuda.system_libs.append("atomic")
                elif self.settings.os == "Windows":
                    gst_cuda.system_libs.append("advapi32")
                # Also links against nvbufsurface on Jetson, if found
            # d3d11
            if self.options.get_safe("d3d11"):
                gst_d3d11 = _define_library("d3d11", [
                    "gstreamer-video-1.0",
                ])
                gst_d3d11.includedirs.append(os.path.join("lib", "gstreamer-1.0", "include"))
                gst_d3d11.system_libs.extend([
                    "d3d11", "dxgi", "d3dcompiler", "runtimeobject",
                ])
                if Version(self.version) >= "1.26":
                    gst_d3d11.requires.append("gstreamer-d3dshader-1.0")
            # d3d11
            if self.options.get_safe("d3d12") and Version(self.version) >= "1.26":
                gst_d3d11 = _define_library("d3d12", [
                    "gstreamer-video-1.0",
                    "gstreamer-d3dshader-1.0",
                    "directx-headers::directx-headers",
                    "glib::gmodule-no-export-2.0",
                ])
                gst_d3d11.includedirs.append(os.path.join("lib", "gstreamer-1.0", "include"))
                gst_d3d11.system_libs.extend([
                    "d3d12", "dxgi", "directxmath",
                ])
            if self.settings.os == "Windows" and Version(self.version) >= "1.26":
                _define_library("d3dshader", [
                    "gstreamer-video-1.0",
                    "glib::gmodule-no-export-2.0",
                ])
            # downloader
            _define_library("downloader", [], lib="gsturidownloader-1.0")
            # dxva
            if self.settings.os == "Windows":
                _define_library("dxva", [
                    "gstreamer-video-1.0",
                    "gstreamer-codecs-1.0",
                ])
            # insertbin
            _define_library("insertbin", [])
            # isoff
            _define_library("isoff", [])
            # mpegts
            _define_library("mpegts", [])
            # mse
            _define_library("mse", [
                "gstreamer-app-1.0",
            ])
            # opencv
            if self.options.get_safe("opencv"):
                _define_library("opencv", [
                    "gstreamer-video-1.0",
                    "opencv::opencv_core",
                ])
            # photography
            _define_library("photography", [])
            # play
            _define_library("play", [
                "gstreamer-video-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-tag-1.0",
                "gstreamer-pbutils-1.0",
            ])
            # player
            _define_library("player", [
                "gstreamer-video-1.0",
                "gstreamer-audio-1.0",
                "gstreamer-tag-1.0",
                "gstreamer-pbutils-1.0",
                "gstreamer-play-1.0",
            ])
            # sctp
            _define_library("sctp", [])
            # transcoder
            _define_library("transcoder", [
                "gstreamer-pbutils-1.0",
            ])
            # va
            if self.options.get_safe("va"):
                gst_va = _define_library("va", [
                    "gstreamer-video-1.0",
                    "gstreamer-allocators-1.0",
                ])
                if self.options.get_safe("with_libdrm"):
                    gst_va.requires.extend([
                        "libdrm::libdrm_libdrm",
                    ])
                    if self.settings.os not in ["Linux", "FreeBSD"]:
                        gst_va.requires.append("libva::libva-drm")
                if self.settings.os not in ["Linux", "FreeBSD"]:
                    gst_va.requires.append("libva::libva_")
                else:
                    gst_va.requires.append("vaapi::vaapi")
                if self.settings.os == "Windows":
                    gst_va.requires.append("libva::libva-win32")
                    gst_va.system_libs.append("dxgi")
            # vulkan
            if self.options.get_safe("vulkan"):
                gst_vulkan = _define_library("vulkan", [
                    "gstreamer-video-1.0",
                    "vulkan-loader::vulkan-loader",
                ])
                if self.options.get_safe("with_wayland"):
                    gst_vulkan.requires.append("wayland::wayland-client")
                    _define_library("vulkan-wayland", [
                        "gstreamer-vulkan-1.0",
                        "wayland::wayland-client",
                    ], interface=True)
                if self.options.get_safe("with_xorg"):
                    gst_vulkan.requires.extend([
                        "xorg::xcb",
                        "xkbcommon::libxkbcommon",
                        "xkbcommon::libxkbcommon-x11",
                    ])
                    _define_library("vulkan-xcb", [
                        "gstreamer-vulkan-1.0",
                        "xorg::xcb",
                    ], interface=True)
                if is_apple_os(self):
                    gst_vulkan.requires.append("moltenvk::moltenvk")
                    gst_vulkan.frameworks.extend(["Foundation", "QuartzCore", "CoreFoundation"])
                    if self.settings.os == "Macos":
                        gst_vulkan.frameworks.append("Cocoa")
                    elif self.settings.os == "iOS":
                        gst_vulkan.frameworks.append("UIKit")
                        if Version(self.version) >= "1.26":
                            gst_vulkan.frameworks.extend(["IOSurface", "CoreGraphics", "Metal"])
                elif self.settings.os == "Windows":
                    gst_vulkan.system_libs.append("gdi32")
            # wayland
            if self.options.get_safe("with_wayland"):
                gst_wayland = _define_library("wayland", [
                    "gstreamer-allocators-1.0",
                    "gstreamer-video-1.0",
                    "wayland::wayland-client",
                ])
                if self.options.get_safe("with_libdrm"):
                    gst_wayland.requires.append("libdrm::libdrm_libdrm")
            # webrtc
            _define_library("webrtc", [
                "gstreamer-sdp-1.0",
            ])
            # webrtc-nice
            if self.options.get_safe("webrtc"):
                _define_library("webrtc-nice", [
                    "gstreamer-sdp-1.0",
                    "gstreamer-webrtc-1.0",
                    "libnice::libnice",
                    "glib::gio-2.0",
                ])
            # winrt
            if is_msvc(self):
                gst_winrt = _define_library("winrt", [])
                gst_winrt.system_libs.append("runtimeobject")

            # Plugins

            plugin_infos = self._plugin_infos[self._current_version]["bad"]
            for plugin in plugin_infos:
                if _is_enabled(plugin, plugin_infos[plugin]):
                    _define_plugin(plugin, plugin_infos[plugin])

            # amfcodec
            if self.options.get_safe("amfcodec"):
                gst_amfcodec = self.cpp_info.components["gstamfcodec"]
                gst_amfcodec.system_libs.append("winmm")
            # androidmedia
            if self.options.get_safe("androidmedia"):
                gst_am = self.cpp_info.components["gstandroidmedia"]
                gst_am.system_libs.extend(["android"])
            # applemedia
            if self.options.get_safe("applemedia"):
                gst_applemedia = self.cpp_info.components["gstapplemedia"]
                if self.options.vulkan:
                    gst_applemedia.requires.extend([
                        "gstreamer-vulkan-1.0",
                        "moltenvk::moltenvk",
                    ])
                gst_applemedia.frameworks.extend([
                    "AVFoundation", "AudioToolbox", "CoreFoundation", "CoreMedia",
                    "CoreVideo", "IOSurface", "Metal", "VideoToolbox",
                ])
                if self.settings.os == "Macos":
                    gst_applemedia.frameworks.extend(["Cocoa", "OpenGL"])
                else:
                    gst_applemedia.frameworks.extend(["Foundation", "AssetsLibrary"])
            # curl
            if self.options.get_safe("curl") and self.options.with_libssh2:
                gst_curl = self.cpp_info.components["gstcurl"]
                gst_curl.requires.append("libssh2::libssh2")
            # d3d
            if self.options.get_safe("d3d") and not self.options.shared:
                gst_d3d = self.cpp_info.components["gstd3d"]
                gst_d3d.system_libs.extend(["d3d9", "gdi32"])
            # d3d11
            if self.options.get_safe("d3d11") and not self.options.shared:
                gst_d3d11 = self.cpp_info.components["gstd3d11"]
                gst_d3d11.system_libs.extend([
                    "d2d1", "runtimeobject", "winmm", "dwmapi",
                ])
            # d3d12
            if self.options.get_safe("d3d12") and not self.options.shared:
                gst_d3d12 = self.cpp_info.components["gstd3d12"]
                if Version(self.version) >= "1.26":
                    gst_d3d12.system_libs.extend(["d3d11", "d2d1", "dwmapi", "directxmath"])
                    if self.options.get_safe("d3d11"):
                        gst_d3d12.requires.append("gstreamer-d3d11-1.0")
                else:
                    gst_d3d12.system_libs.extend(["d3d12", "d3d11", "d2d1", "dxgi"])
            # decklink
            if self.options.get_safe("decklink"):
                gst_decklink = self.cpp_info.components["gstdecklink"]
                if self.settings.os == "Windows":
                    gst_decklink.system_libs.append("comsuppw")
                elif is_apple_os(self):
                    gst_decklink.frameworks.append("CoreFoundation")
                elif self.settings.os in ["Linux", "FreeBSD"]:
                    gst_decklink.system_libs.extend(["pthread", "dl"])
            # directshow
            if self.options.get_safe("directshow") and not self.options.shared:
                gst_directshow = self.cpp_info.components["gstdirectshow"]
                gst_directshow.system_libs.extend([
                    "strmiids", "winmm", "dmoguids", "wmcodecdspuuid", "mfuuid", "rpcrt4",
                ])
            # directsoundsrc
            if self.options.get_safe("directsoundsrc") and not self.options.shared:
                gst_directsound = self.cpp_info.components["gstdirectsoundsrc"]
                gst_directsound.system_libs.extend(["dsound", "winmm", "ole32"])
            # dwrite
            if self.options.get_safe("dwrite") and self.options.get_safe("d3d11") and not self.options.shared:
                gst_dwrite = self.cpp_info.components["gstdwrite"]
                gst_dwrite.system_libs.extend(["d2d1", "dwrite", "windowscodecs"])
                if self.options.get_safe("d3d12") and Version(self.version) >= "1.26":
                    gst_dwrite.requires.append("gstreamer-d3d12-1.0")
            # kms
            if self.options.get_safe("kms") and self.options.get_safe("with_libdrm"):
                gst_kms = self.cpp_info.components["gstkms"]
                gst_kms.requires.append("libdrm::libdrm_libdrm")
            # mediafoundation
            if self.options.get_safe("mediafoundation"):
                gst_mf = self.cpp_info.components["gstmediafoundation"]
                if self.options.get_safe("d3d11"):
                    gst_mf.requires.append("gstreamer-d3d11-1.0")
                if not self.options.shared:
                    gst_mf.system_libs.extend([
                        "mf", "mfplat", "mfreadwrite", "mfuuid", "strmiids", "ole32", "runtimeobject",
                    ])
            # nvcodec
            if self.options.get_safe("nvcodec") and self.settings.os == "Windows":
                gst_nvcodec = self.cpp_info.components["gstnvcodec"]
                gst_nvcodec.requires.append("gstreamer-d3d11-1.0")
                if Version(self.version) >= "1.26" and self.options.get_safe("d3d12"):
                    gst_nvcodec.requires.append("gstreamer-d3d12-1.0")
            # onnx
            if self.options.get_safe("onnx") and self.settings.os in ["Linux", "Windows"]:
                gst_onnx = self.cpp_info.components["gstonnx"]
                gst_onnx.requires.append("gstreamer-cuda-1.0")
            if self.options.get_safe("rfbsrc") and self.options.get_safe("with_xorg"):
                gst_rfbsrc = self.cpp_info.components["gstrfbsrc"]
                gst_rfbsrc.requires.append("xorg::x11")
            # qsv
            if self.options.get_safe("qsv"):
                gst_qsv = self.cpp_info.components["gstqsv"]
                if self.settings.os in ["Linux", "FreeBSD"]:
                    gst_qsv.requires.append("gstreamer-va-1.0")
                    gst_qsv.system_libs.extend(["pthread", "dl"])
                elif self.settings.os == "Windows":
                    gst_qsv.requires.append("gstreamer-d3d11-1.0")
                    if Version(self.version) >= "1.26" and self.options.get_safe("d3d12"):
                        gst_qsv.requires.append("gstreamer-d3d12-1.0")
            # va
            if self.options.get_safe("va") and self.options.get_safe("with_libudev"):
                gst_va = self.cpp_info.components["gstva"]
                gst_va.requires.append("libgudev::libgudev")
            # wasapi
            if self.options.get_safe("wasapi") and not self.options.shared:
                gst_wasapi = self.cpp_info.components["gstwasapi"]
                gst_wasapi.system_libs.extend(["ole32", "ksuser"])
            # wasapi2
            if self.options.get_safe("wasapi2") and not self.options.shared:
                gst_wasapi = self.cpp_info.components["gstwasapi2"]
                gst_wasapi.system_libs.extend([
                    "ole32", "ksuser", "runtimeobject", "mmdevapi", "mfplat",
                ])
            # wic
            if self.options.get_safe("wic") and not self.options.shared:
                gst_wic = self.cpp_info.components["gstwic"]
                gst_wic.system_libs.extend(["windowscodecs"])
            # winks
            if self.options.get_safe("winks") and not self.options.shared:
                gst_winks = self.cpp_info.components["gstwinks"]
                gst_winks.system_libs.extend([
                    "ksuser", "uuid", "strmiids", "dxguid", "setupapi", "ole32",
                ])
            # winscreencap
            if self.options.get_safe("winscreencap") and not self.options.shared:
                gst_winscreencap = self.cpp_info.components["gstwinscreencap"]
                gst_winscreencap.system_libs.extend(["d3d9", "gdi32"])

        if self.options.ugly:
            plugin_infos = self._plugin_infos[self._current_version]["ugly"]
            for plugin in plugin_infos:
                if _is_enabled(plugin, plugin_infos[plugin]):
                    _define_plugin(plugin, plugin_infos[plugin])

        if self.options.libav:
            _define_plugin("libav", {
                "requires": [
                    "ffmpeg::avfilter",
                    "ffmpeg::avformat",
                    "ffmpeg::avcodec",
                    "gstreamer-video-1.0",
                    "gstreamer-audio-1.0",
                    "gstreamer-pbutils-1.0",
            ]})

        if self.options.ges:
            ges_extra_requires = [
                "gstreamer-controller-1.0",
                "gstreamer-pbutils-1.0",
                "gstreamer-video-1.0",
                "gstreamer-audio-1.0",
                "glib::gio-2.0",
            ]
            if self.options.devtools:
                ges_extra_requires.append("gstreamer-validate-1.0")
                
            _define_library("ges", ges_extra_requires, lib="ges-1.0")
            _define_plugin("ges", {
                "requires": [
                    "gstreamer-ges-1.0",
            ]})
            _define_plugin("nle", {
                "requires": [
                    "gstreamer-ges-1.0",
            ]})

        if self.options.rtsp_server:
            _define_library("rtspserver", [
                "gstreamer-app-1.0",
                "gstreamer-net-1.0",
                "gstreamer-video-1.0",
                "gstreamer-rtp-1.0",
                "gstreamer-rtsp-1.0",
                "gstreamer-sdp-1.0",
            ]
            )
            _define_plugin("rtspclientsink", {
                "requires": [
                    "gstreamer-rtspserver-1.0",
                    "gstreamer-sdp-1.0",
            ]})
