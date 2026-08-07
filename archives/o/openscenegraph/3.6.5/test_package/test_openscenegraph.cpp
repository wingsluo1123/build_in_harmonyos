// Test OpenSceneGraph package: verify library linking and core API functionality.
#include <osg/Version>
#include <osg/Group>
#include <osg/ref_ptr>
#include <cstdio>

// OpenThreadsGetVersion is declared in the generated OpenThreads/Version header
extern "C" const char* OpenThreadsGetVersion();

int main(void) {
    // Verify OSG library is linked and functional
    printf("OpenSceneGraph version: %s\n", osgGetVersion());
    printf("OpenSceneGraph SO version: %s\n", osgGetSOVersion());
    printf("OpenThreads version: %s\n", OpenThreadsGetVersion());

    // Create an osg::Group (concrete subclass of osg::Object) to verify core functionality
    osg::ref_ptr<osg::Group> group = new osg::Group;
    if (group.valid()) {
        printf("osg::Group created successfully\n");
        printf("Group name: %s\n", group->getName().c_str());
    } else {
        printf("FAIL: osg::Group creation failed\n");
        return 1;
    }

    printf("test openscenegraph 3.6.5: OK\n");
    return 0;
}
