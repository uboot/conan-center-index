#include <gst/gst.h>
#include <gst/gstplugin.h>

#include <iostream>

#ifdef GST_STATIC_COMPILATION
extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(audiotestsrc);
    GST_PLUGIN_STATIC_DECLARE(videotestsrc);
}
#endif

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(audiotestsrc);
    GST_PLUGIN_STATIC_REGISTER(videotestsrc);
#endif

    GstElement * audiotestsrc = gst_element_factory_make("audiotestsrc", NULL);
    if (!audiotestsrc) {
        std::cerr << "failed to create audiotestsrc element" << std::endl;
        return -1;
    } else {
        std::cout << "audiotestsrc has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(audiotestsrc));
    GstElement * videotestsrc = gst_element_factory_make("videotestsrc", NULL);
    if (!videotestsrc) {
        std::cerr << "failed to create videotestsrc element" << std::endl;
        return -1;
    } else {
        std::cout << "videotestsrc has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(videotestsrc));
    return 0;
}
