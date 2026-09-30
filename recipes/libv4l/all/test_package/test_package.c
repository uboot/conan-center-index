#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <fcntl.h>
#include <libv4l2.h>

int main(void) {
    int fd = v4l2_open("/dev/conan-libv4l-test-nonexistent", O_RDONLY);
    if (fd >= 0) {
        v4l2_close(fd);
        fprintf(stderr, "Unexpectedly opened a nonexistent video device.\n");
        return EXIT_FAILURE;
    }

    if (errno != ENOENT) {
        fprintf(stderr, "Opening a nonexistent device did not report ENOENT.\n");
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
