#include <gst/gst.h>
#include <gst/gstplugin.h>

#include <iostream>

#ifdef GST_STATIC_COMPILATION
extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(asf);
}
#endif

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(asf);
#endif

    GstElement * asfdemux = gst_element_factory_make("asfdemux", NULL);
    if (!asfdemux) {
        std::cerr << "failed to create asfdemux element" << std::endl;
        return -1;
    } else {
        std::cout << "asfdemux has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(asfdemux));
    return 0;
}
