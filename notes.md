## gstreamer-dev

- package test of msys2/cci.latest fails after initial build (it succeeded
  during the initial build?)
- gst-plugins-good fail because `hls` is required even if
  gst-plugins-good/*:adaptivedemux2=False:
  https://github.com/GStreamer/gstreamer/blob/344b93aba7866f305d97db99c66a48065bc2f120/subprojects/gst-plugins-good/ext/adaptivedemux2/meson.build#L96
  Fix:
  - Enable gst-plugins-good/*:adaptivedemux2=True OR
  - Patch gst-plugins-good: `git apply C:\Users\azureuser\conan-center-index\recipes\gst-plugins-good\all\patches\1.26\001-conan-deps.patch --directory subprojects/gst-plugins-good`
  - Fix code and create a new patch: `cd subprojects/gst-plugins-good` and `git diff HEAD~1 --relative`
- CMake 4 breaks some package builds because it requires a high enough
  `CMAKE_MINIMUM_REQUIRED_VERSION`. Thus, the CMake 3.x is installed in the 
  playbook
- Line 419 of the gst-plugins-good recipe with `gst-plugins-good/*:qt6=True`
  breaks the package test
- Activating options which require external packages in plugins bad, i.e.
  `gst-plugins-bad/*:*=True`, leads to conflicts of the glib version. One has to
  patch the recipes of `harfbuzz`, `cairo` and `pango` such that 
  `glib/[>=2.78.3 <3]` is required instead of `glib/2.78.3`
- `gst-plugins-bad/*:aom=True` breaks the build and was disabled
- `gst-plugins-bad/*:curl=True` breaks the build:
  `Invalid: -o curl=True is not compatible with MSVC`
- `gst-plugins-bad/*:rsvg=True` depends on `librsvg` which is not part of
  conan-center-main and which requires GDK etc. Attempting to resolve all missing dependencies led to a conflict: 
  ```
  Options conflicts
    gstreamer/1.26.0:shared=True (current value)
        gst-plugins-base/1.26.0->shared=False
    pango/1.54.0:with_freetype=False (current value)
        librsvg/2.60.0->with_freetype=True
    It is recommended to define options values in profiles, not in recipes
  WARN: risk: There are options conflicts in the dependency graph
  ```
- `gst-plugins-bad/*:svtjpegxs=True` fails to build because of
  `fatal error C1083: Cannot open include file: 'SvtJpegxsEnc.h': No such file or directory`
- `gst-plugins-bad/*:zxing=True` fails to build because of
  because of `zxing/gstzxing.cpp(436): error C2121: '#': invalid character: possibly the result of a macro expansion`
- `gst-plugins-bad/*:opencv=True` leads to `ERROR: Version conflict: Conflict between libpng/1.6.40 and libpng/1.6.47 in the graph.`
- FluentWinUI3 style was added with Qt 6.8. This leads to the CMake warning
  ```
  CMake Warning in qtdeclarative/src/quickcontrols/fluentwinui3/impl/CMakeLists.txt:
    The object file directory
  
      C:/Users/runneradmin/.conan2/p/b/qt57c45963ec0ee/b/build/qtdeclarative/src/quickcontrols/fluentwinui3/impl/CMakeFiles/qtquickcontrols2fluentwinui3styleimplplugin.dir/./
  
    has 168 characters.  The maximum full path to an object file is 250
    characters (see CMAKE_OBJECT_PATH_MAX).  Object file
  
      qtquickcontrols2fluentwinui3styleimplplugin_QtQuickControls2FluentWinUI3StyleImplPlugin.cpp.obj
  
    cannot be safely placed under this directory.  The build may not work
    correctly.
  ```
  and to the build error `C:\Users\runneradmin\.conan2\p\b\qt57c45963ec0ee\b\build\qtdeclarative\src\quickcontrols\fluentwinui3\impl\qtquickcontrols2fluentwinui3styleimplplugin_QtQuickControls2FluentWinUI3StyleImplPlugin.cpp : fatal error C1083: Cannot open compiler generated file: '': Invalid argument`.
  Setting `core.cache:storage_path = C:\p` fixes the problem
- `gst-plugins-bad/*:svtav1` requires `libsvtav1`. This package is also required
  by `ffmpeg`. To avoid version conflicts both (`gst-plugins-bad` and `ffmpeg`)
  must require the same version. Currently this is `libsvtav1/2.1.0`
- `gst-plugins-base` requires `opus/1.4` instead of a version range. Otherwise
  there is a dependency conflict with `ffmpeg` when resolving dependencies via
  `cci`
- `cairo, fontconfig, fribid` must use version ranges for their dependency on
  `meson` because the specific `meson` versions were removed by
  https://github.com/conan-io/conan-center-index/pull/27650
- Create a patch of upstream GStreamer: `git diff HEAD~1 > 001-use-conan-deps.patch`
- `libsvtav1 > 2.1.0` removes the option `libsvtav1/*:build_decoder`. This
  breaks the GStreamer build because the Conan component `libsvtav1::decoder` is
  not found
- Set `gst-plugins-rs/*:validate=False` because the GStreamer devtools are not
  built by the `gstreamer` package. An option `gstreamer:devtools` should be
  implemented at some point

## use-cci

- `libnice/0.1.23` is only available for `glib/2.85.3` (as opposed to `2.86`).
  This blocks WebRTC plugins
- There are *no* pre-built packages for `theora/1.1.1`. This blocks `-o theora`

