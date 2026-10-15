#include <wx/app.h>

extern "C" WXEXPORT wxAppConsole *wx_state_from_dso()
{
    return wxAppConsole::GetInstance();
}
