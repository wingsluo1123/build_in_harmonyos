#include <ittnotify.h>
#include <jitprofiling.h>

int main(void)
{
    __itt_domain *domain = __itt_domain_create("ohpcd.ittapi.consumer");
    __itt_string_handle *name = __itt_string_handle_create("smoke-task");

    if (domain == 0 || name == 0) {
        return 1;
    }

    __itt_task_begin(domain, __itt_null, __itt_null, name);
    __itt_task_end(domain);
    (void)iJIT_IsProfilingActive();
    return 0;
}
