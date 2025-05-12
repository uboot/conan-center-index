#include <gst/gst.h>
#include <gst/gstplugin.h>
#include <gst/rtsp-server/rtsp-server.h>

#ifdef GST_STATIC_COMPILATION

extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(rtspclientsink);
}

#endif

#include <iostream>

void create_server()
{
  GstRTSPServer *server;
  GstRTSPMountPoints *mounts;
  GstRTSPMediaFactory *factory;

  server = gst_rtsp_server_new ();
  mounts = gst_rtsp_server_get_mount_points (server);
  factory = gst_rtsp_media_factory_new ();
  gst_rtsp_media_factory_set_launch (factory,
      "( videotestsrc is-live=1 ! x264enc ! rtph264pay name=pay0 pt=96 )");

  gst_rtsp_media_factory_set_shared (factory, TRUE);
  gst_rtsp_mount_points_add_factory (mounts, "/test", factory);
  std::cout << "RTSP server created successfully" << std::endl;

  g_object_unref (mounts);
  g_object_unref (server);
  std::cout << "RTSP server destroyed successfully" << std::endl;
}

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

    create_server();

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(rtspclientsink);
#endif

    GstElement * rtspclientsink = gst_element_factory_make("rtspclientsink", NULL);
    if (!rtspclientsink) {
        std::cerr << "failed to create rtspclientsink element" << std::endl;
        return -1;
    } else {
        std::cout << "rtspclientsink has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(rtspclientsink));
    return 0;
}
