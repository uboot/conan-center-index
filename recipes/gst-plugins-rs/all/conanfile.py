import os
import re
import shutil
from functools import cached_property, lru_cache
from pathlib import Path

import yaml
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import *
from conan.tools.gnu import PkgConfigDeps, GnuToolchain
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=2.4"
_versions = ["1.26", "1.28"]

class GStPluginsRsConan(ConanFile):
    name = "gst-plugins-rs"
    description = "GStreamer plugins written in Rust"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs"
    topics = ("gstreamer", "multimedia", "video", "audio", "broadcasting", "framework", "media")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "webrtc_aws": [True, False],
        "webrtc_livekit": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,

        # Plugins can be enabled using the same option names as in meson_options.txt

        # webrtc plugin options
        "webrtc_aws": False,
        "webrtc_livekit": False,
    }
    languages = ["C"]

    @cached_property
    def _requirements(self):
        return yaml.safe_load(Path(self.recipe_folder, "requirements.yml").read_text())

    @cached_property
    def _plugin_infos(self):
        plugins = {}
        for v in _versions:
            plugins[v] = yaml.safe_load(Path(self.recipe_folder, "plugins", f"{v}.yml").read_text())
        return plugins

    @cached_property
    def _option_infos(self):
        options = {}
        for v in _versions:
            plugins = self._plugin_infos[v]
            options[v] = {plugins[info].get("options", [info])[0]: plugins[info] for info in plugins}
        return options

    @property
    def _current_version(self):
        version = Version(self.version)
        return f"{version.major}.{version.minor}"

    def init(self):
        def _compute_default_options(option_infos):
            def _default_option(option_info, option_infos):
                def _is_external_dep(dep):
                    if "::" not in dep:
                        return False
                    return dep.split("::")[0] not in ["glib", "gst-orc"]

                for option in option_info.get("options", [])[1:]:
                    if not _default_option(option_infos[option], option_infos):
                        return False
                return not any(_is_external_dep(r) for r in option_info["requires"])

            return {info: _default_option(option_infos[info], option_infos) for info in option_infos}

        options = {}
        defaults = {}
        for v in _versions:
            option_defaults = _compute_default_options(self._option_infos[v])
            options.update({o: [True, False] for o in option_defaults})
            for o in option_defaults:
                defaults[o] = defaults.get(o, True) and option_defaults[o]
        self.options.update(options, defaults)

    def export(self):
        copy(self, "requirements.yml", self.recipe_folder, self.export_folder)
        copy(self, "plugins/*.yml", self.recipe_folder, self.export_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.options["gstreamer"].shared = self.options.shared
        if self.options.webrtc:
            self.options.rtp = True
        else:
            self.options.rm_safe("webrtc_aws")
            self.options.rm_safe("webrtc_livekit")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires(f"gstreamer/{self.version}", transitive_headers=True, transitive_libs=True)
        self.requires("glib/[^2.70.0]", transitive_headers=True, transitive_libs=True)

        reqs = set()
        option_infos = self._option_infos[self._current_version]
        for option in option_infos:
            if self.options.get_safe(option, False):
                if option in {"glib", "gst-orc"}:
                    continue
                elif option == "skia" and self.settings.os == "Windows":
                    # skia has no depencencies on Windows
                    continue
                reqs.update(r.split("::")[0] for r in option_infos[option].get("requires", []) if "::" in r)

        for req in reqs:
            if req == "cairo":
                self.requires("pango/[^1.54.0]", options={"with_cairo": True})
            else:
                self.requires(f"{req}/{self._requirements[req]}")
            
    def validate(self):
        if not self.dependencies["glib"].options.shared and self.options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("shared GStreamer cannot link to static GLib")
        if self.options.shared != self.dependencies["gstreamer"].options.shared:
            # https://gitlab.freedesktop.org/gstreamer/gst-build/-/issues/133
            raise ConanInvalidConfiguration("GStreamer and plugins must be either all shared, or all static")
        if self.settings.os == "Windows" and not self.options.shared:
            # static build fails with an internal linker error on Windows
            raise ConanInvalidConfiguration("Linking a static build of GstPluginsRs fails on Windows")

        
        for option, option_info in self._option_infos[self._current_version].items():
            if self.options.get_safe(option):
                unsatisfied_options = [o for o in option_info.get("options", []) if not self.options.get_safe(o)]
                if any(unsatisfied_options):
                    raise ConanInvalidConfiguration(f"-o {option}=True requires -o {unsatisfied_options[0]}=True")
                
        if self.options.get_safe("webrtc"):
            if not self.dependencies["gstreamer"].options.get_safe("webrtc"):
                raise ConanInvalidConfiguration("-o webrtc=True requires -o gstreamer:webrtc=True")
            if not (self.dependencies["gstreamer"].options.get_safe("dtls")):
                raise ConanInvalidConfiguration("-o webrtc=True requires -o gstreamer:dtls=True")
            if not (self.dependencies["gstreamer"].options.get_safe("sctp")):
                raise ConanInvalidConfiguration("-o webrtc=True requires -o gstreamer:sctp=True")
            if not (self.dependencies["gstreamer"].options.get_safe("srtp")):
                raise ConanInvalidConfiguration("-o webrtc=True requires -o gstreamer:srtp=True")
            
        if self.options.get_safe("validate"):
            if not self.dependencies.get("gstreamer").options.get_safe("devtools"):
                raise ConanInvalidConfiguration("-o validate=True requires -o gstreamer:devtools=True")

    def build_requirements(self):
        self.tool_requires("meson/[>=1.2.3 <2]")
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/[>=2.2 <3]")
        self.tool_requires("glib/<host_version>")
        self.tool_requires("rust/[^1.93]")
        self.tool_requires("cargo-c/[^0.10]")
        if self.options.rav1e:
            self.tool_requires("nasm/[^2.16]")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _define_rust_env(self, env, scope="host", cflags=None):
        target = self.conf.get(f"user.rust:target_{scope}", check_type=str).replace("-", "_")
        cc = GnuToolchain(self).extra_env.vars(self).get("CC" if scope == "host" else "CC_FOR_BUILD", "cc")
        env.define_path(f"CARGO_TARGET_{target.upper()}_LINKER", cc)
        env.define_path(f"CC_{target}", cc)
        if cflags:
            env.append(f"CFLAGS_{target}", cflags)

    def generate(self):
        env = Environment()
        self._define_rust_env(env, "host")
        if cross_building(self):
            self._define_rust_env(env, "build")
            env.define_path("CARGO_HOME", os.path.join(self.build_folder, "cargo"))
        env.vars(self).save_script("cargo_paths")

        def feature(v):
            return "enabled" if v else "disabled"

        tc = MesonToolchain(self)
        tc.project_options["auto_features"] = "enabled"
        
        for opt in self._option_infos[self._current_version].keys():
            tc.project_options[opt] = feature(self.options.get_safe(opt))
        tc.project_options["doc"] = "disabled"
        tc.project_options["examples"] = "disabled"
        tc.project_options["tests"] = "disabled"
        tc.project_options["sodium-source"] = "system"
        tc.project_options["webrtc-aws"] = feature(self.options.get_safe("webrtc_aws"))
        tc.project_options["webrtc-livekit"] = feature(self.options.get_safe("webrtc_livekit"))
        tc.generate()

        if cross_building(self):
            rust_target = self.conf.get(f"user.rust:target_host", check_type=str)
            replace_in_file(self, "conan_meson_cross.ini",
                            "[binaries]",
                            f"[binaries]\nrust = ['rustc', '--target', '{rust_target}']")

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def _fix_library_names(self, path):
        if is_msvc(self):
            for filename_old in Path(path).glob("*.a"):
                filename_new = str(filename_old)[:-2] + ".lib"
                shutil.move(filename_old, filename_new)

    def package(self):
        copy(self, "LICENSE-*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        meson = Meson(self)
        meson.install()
        self._fix_library_names(os.path.join(self.package_folder, "lib"))
        self._fix_library_names(os.path.join(self.package_folder, "lib", "gstreamer-1.0"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "gstreamer-1.0", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        if self.options.shared:
            self.runenv_info.define_path("GST_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "gstreamer-1.0"))

        def _define_plugin(plugin, plugin_info):
            plugin_name = f"gst{plugin}"
            extra_requires = []
            for req in plugin_info.get("requires", []):
                m = re.fullmatch("gstreamer-(.+)-1.0", req)
                if m and m[1] in _gstreamer_libs:
                    extra_requires.append(f"gstreamer::{m[0]}")
                else:
                    extra_requires.append(req)
            component = self.cpp_info.components[plugin_name]
            component.requires = [
                "gstreamer::gstreamer-1.0",
                "gstreamer::gstreamer-base-1.0",
                "glib::gobject-2.0",
                "glib::glib-2.0",
                "glib::gio-2.0",
            ] + extra_requires
            component.includedirs = []
            component.bindirs = []
            component.resdirs = ["share"]
            component.set_property("pkg_config_name", plugin_name)
            component.set_property("cmake_target_name", f"GstPluginsRs::{plugin_name}")
            if self.options.shared:
                component.bindirs.append(os.path.join("lib", "gstreamer-1.0"))
            else:
                component.libs = [plugin_name]
                component.libdirs = [os.path.join("lib", "gstreamer-1.0")]
                if self.settings.os in ["Linux", "FreeBSD"]:
                    component.system_libs = ["m"]
                component.defines.append("GST_PLUGINS_RS_STATIC")
            return component
        
        def _is_enabled(plugin, plugin_info):
            required_options = plugin_info.get("options", [plugin])
            return all(self.options.get_safe(opt, False) for opt in required_options)
                
        self.cpp_info.set_property("cmake_file_name", "GstPluginsRs")
        self.cpp_info.set_property("cmake_target_name", "GstPluginsRs::GstPluginsRs")

        plugin_infos = self._plugin_infos[self._current_version]
        for plugin in plugin_infos:
            if _is_enabled(plugin, plugin_infos[plugin]):
                _define_plugin(plugin, plugin_infos[plugin])
                if plugin == "rsvalidate":
                    # gstrsvalidate is installed to the 'validate' subdirectory of the plugin directory
                    if self.options.get_safe("shared", True):
                        self.cpp_info.components["gstrsvalidate"].bindirs.append(os.path.join("lib", "gstreamer-1.0", "validate"))
                    else:
                        self.cpp_info.components["gstrsvalidate"].libdirs.append(os.path.join("lib", "gstreamer-1.0", "validate"))


_gstreamer_libs = {
    "base",
    "check",
    "controller",
    "net",
    "allocators",
    "app",
    "audio",
    "fft",
    "gl",
    "gl-egl",
    "gl-prototypes",
    "gl-wayland",
    "gl-x11",
    "pbutils",
    "plugins-base",
    "riff",
    "rtp",
    "rtsp",
    "sdp",
    "tag",
    "video",
    "adaptivedemux",
    "analytics",
    "bad-audio",
    "bad-base-camerabinsrc",
    "codecparsers",
    "codecs",
    "cuda",
    "d3d11",
    "downloader",
    "dxva",
    "insertbin",
    "isoff",
    "mpegts",
    "mse",
    "opencv",
    "photography",
    "play",
    "player",
    "sctp",
    "transcoder",
    "va",
    "validate",
    "vulkan",
    "vulkan-wayland",
    "vulkan-xcb",
    "wayland",
    "webrtc",
    "webrtc-nice",
    "winrt",
}
