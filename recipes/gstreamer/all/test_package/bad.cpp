#include <gst/gst.h>
#include <gst/gstplugin.h>

#include <iostream>

#ifdef GST_STATIC_COMPILATION
extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(mpegpsdemux);
}
#endif

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(mpegpsdemux);
#endif

    GstElement * mpegpsdemux = gst_element_factory_make("mpegpsdemux", NULL);
    if (!mpegpsdemux) {
        std::cerr << "failed to create mpegpsdemux element" << std::endl;
        return -1;
    } else {
        std::cout << "mpegpsdemux has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(mpegpsdemux));
    return 0;
}
