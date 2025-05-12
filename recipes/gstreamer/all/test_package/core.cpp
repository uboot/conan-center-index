#include <gst/gst.h>

#include <iostream>

#ifdef GST_STATIC_COMPILATION
extern "C"
{
    GST_PLUGIN_STATIC_DECLARE(coreelements);
}
#endif

static gint compare_plugins_by_name(gconstpointer plugin_a, gconstpointer plugin_b)
{
    GstPlugin *a = const_cast<GstPlugin *>(GST_PLUGIN(plugin_a));
    GstPlugin *b = const_cast<GstPlugin *>(GST_PLUGIN(plugin_b));
    return g_strcmp0(gst_plugin_get_name(a), gst_plugin_get_name(b));
}

void list_plugins()
{
    GstRegistry *registry = gst_registry_get();
    if (!registry) {
        std::cerr << "Failed to get GStreamer registry" << std::endl;
        exit(-1);
    }
    GList *plugins = gst_registry_get_plugin_list(registry);
    plugins = g_list_sort(plugins, compare_plugins_by_name);
    std::cout << "Found plugins:" << std::endl;
    for (GList *plugin_item = plugins; plugin_item != nullptr; plugin_item = plugin_item->next) {
        GstPlugin *plugin = GST_PLUGIN(plugin_item->data);
        const gchar *name = gst_plugin_get_name(plugin);
        const gchar *desc = gst_plugin_get_description(plugin);
        std::cout << "- " << name;
        if (desc) {
            std::cout << " (" << desc << ")";
        }
        std::cout << std::endl;
    }
    gst_plugin_list_free(plugins);
}

int main(int argc, char * argv[])
{
    gst_init(&argc, &argv);
    printf("GStreamer version: %s\n", gst_version_string());

#ifdef GST_STATIC_COMPILATION
    GST_PLUGIN_STATIC_REGISTER(coreelements);
#endif

    list_plugins();

    GstElement * fakesink = gst_element_factory_make("fakesink", NULL);
    if (!fakesink) {
        std::cerr << "failed to create fakesink element" << std::endl;
        return EXIT_FAILURE;
    } else {
        std::cout << "fakesink has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(fakesink));
    GstElement * fakesrc = gst_element_factory_make("fakesrc", NULL);
    if (!fakesrc) {
        std::cerr << "failed to create fakesrc element" << std::endl;
        return EXIT_FAILURE;
    } else {
        std::cout << "fakesrc has been created successfully" << std::endl;
    }
    gst_object_unref(GST_OBJECT(fakesrc));

    return EXIT_SUCCESS;
}
