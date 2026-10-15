#include <wx/app.h>
#include <cstdio>

extern "C" wxAppConsole *wx_state_from_dso();

int main()
{
    wxAppConsole app;
    wxAppConsole::SetInstance(&app);
    const bool shared = wx_state_from_dso() == &app;
    wxAppConsole::SetInstance(nullptr);
    if (!shared)
    {
        std::fprintf(stderr, "wxApp state differs between executable and shared module\n");
        return 1;
    }
    std::puts("wxApp state is shared across executable and module: OK");
    return 0;
}
