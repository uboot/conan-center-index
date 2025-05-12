cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(GStreamer REQUIRED CONFIG)

add_executable(core core.cpp)

if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
    target_link_libraries(core PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstreamer-base-1.0
        GStreamer::gstreamer-controller-1.0
        GStreamer::gstreamer-net-1.0
        GStreamer::gstreamer-check-1.0
        GStreamer::gstcoreelements
    )
else()
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(gstreamer-1.0 REQUIRED IMPORTED_TARGET gstreamer-1.0)
    pkg_check_modules(gstreamer-base-1.0 REQUIRED IMPORTED_TARGET gstreamer-base-1.0)
    pkg_check_modules(gstreamer-controller-1.0 REQUIRED IMPORTED_TARGET gstreamer-controller-1.0)
    pkg_check_modules(gstreamer-net-1.0 REQUIRED IMPORTED_TARGET gstreamer-net-1.0)
    pkg_check_modules(gstreamer-check-1.0 REQUIRED IMPORTED_TARGET gstreamer-check-1.0)
    pkg_check_modules(gstcoreelements IMPORTED_TARGET gstcoreelements)
    target_link_libraries(core PRIVATE
        PkgConfig::gstreamer-1.0
        PkgConfig::gstreamer-base-1.0
        PkgConfig::gstreamer-controller-1.0
        PkgConfig::gstreamer-net-1.0
        PkgConfig::gstreamer-check-1.0
        PkgConfig::gstcoreelements
    )
endif()

if (STATIC)
    add_compile_definitions(GST_STATIC_COMPILATION)
endif()

if (BASE)
    add_executable(base base.cpp)

    target_link_libraries(base PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstaudiotestsrc
        GStreamer::gstvideotestsrc
    )
endif()

if (GOOD)
    add_executable(good good.cpp)

    target_link_libraries(good PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstwavparse
    )
endif()

if (BAD)
    add_executable(bad bad.cpp)

    target_link_libraries(bad PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstmpegpsdemux
    )
endif()

if (UGLY)
    add_executable(ugly ugly.cpp)

    target_link_libraries(ugly PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstasf
    )
endif()

if (LIBAV)
    add_executable(libav libav.cpp)

    target_link_libraries(libav PRIVATE
        GStreamer::gstreamer-1.0
        GStreamer::gstlibav
    )
endif()

if (GES)
    add_executable(ges ges.cpp)

    target_link_libraries(ges PRIVATE
        GStreamer::gstreamer-ges-1.0
        GStreamer::gstaudiomixer
        GStreamer::gstcompositor
        GStreamer::gstcoreelements
        GStreamer::gstencoding
        GStreamer::gstplayback
        GStreamer::gstvideoconvertscale
        GStreamer::gstges
        GStreamer::gstnle
    )
endif()

if (RTSP_SERVER)
    add_executable(rtsp_server rtsp_server.cpp)

    target_link_libraries(rtsp_server PRIVATE
        GStreamer::gstreamer-rtspserver-1.0
        GStreamer::gstrtspclientsink
    )
endif()
