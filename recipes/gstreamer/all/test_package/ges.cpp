#include <gst/gst.h>
#include <gst/gstplugin.h>
#include <ges/ges.h>

#ifdef GST_STATIC_COMPILATION

extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(audiomixer);
    GST_PLUGIN_STATIC_DECLARE(compositor);
    GST_PLUGIN_STATIC_DECLARE(coreelements);
    GST_PLUGIN_STATIC_DECLARE(encoding);
    GST_PLUGIN_STATIC_DECLARE(playback);
    GST_PLUGIN_STATIC_DECLARE(videoconvertscale);
    GST_PLUGIN_STATIC_DECLARE(ges);
    GST_PLUGIN_STATIC_DECLARE(nle);
}

#endif

#include <iostream>

void create_ges_pipeline()
{
    GESTimeline *timeline;
    GESPipeline *pipeline;

    timeline = ges_timeline_new_audio_video();
    pipeline = ges_pipeline_new();
    if (!ges_pipeline_set_timeline (pipeline, timeline)) {
        std::cout << "Failed to set timeline" << std::endl;
        exit(-1);
    }
    std::cout << "GES pipeline created successfully" << std::endl;

    g_object_unref (pipeline);
    std::cout << "GES pipeline destroyed successfully" << std::endl;
}

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(audiomixer);
    GST_PLUGIN_STATIC_REGISTER(compositor);
    GST_PLUGIN_STATIC_REGISTER(coreelements);
    GST_PLUGIN_STATIC_REGISTER(encoding);
    GST_PLUGIN_STATIC_REGISTER(playback);
    GST_PLUGIN_STATIC_REGISTER(videoconvertscale);
    GST_PLUGIN_STATIC_REGISTER(ges);
    GST_PLUGIN_STATIC_REGISTER(nle);
#endif

    ges_init();

    create_ges_pipeline();

    GstElement * gessrc = gst_element_factory_make("gessrc", NULL);
    if (!gessrc) {
        std::cerr << "failed to create gessrc element" << std::endl;
        return -1;
    } else {
        std::cout << "gessrc has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(gessrc));
    return 0;
}
