#include <gst/gst.h>
#include <gst/gstplugin.h>

#include <iostream>

#ifdef GST_STATIC_COMPILATION
extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(wavparse);
}
#endif

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(wavparse);
#endif

    GstElement * wavparse = gst_element_factory_make("wavparse", NULL);
    if (!wavparse) {
        std::cerr << "failed to create wavparse element" << std::endl;
        return -1;
    } else {
        std::cout << "wavparse has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(wavparse));
    return 0;
}
