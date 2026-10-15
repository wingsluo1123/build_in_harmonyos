#include <wx/wx.h>
#include <wx/display.h>
#include <wx/graphics.h>
#include <wx/settings.h>
#include <glib.h>
#include <cstdio>

static unsigned pango_errors = 0;
static void RecordPangoError(const gchar*, GLogLevelFlags, const gchar* message, gpointer)
{
    ++pango_errors;
    std::fprintf(stderr, "Pango critical: %s\n", message);
}

class GuiTestApp : public wxApp {};
wxIMPLEMENT_APP_NO_MAIN(GuiTestApp);

int main(int argc, char** argv)
{
    if (!wxEntryStart(argc, argv))
    {
        std::fprintf(stderr, "GUI regression requires a working GTK display connection\n");
        return 1;
    }
    if (!wxTheApp->CallOnInit())
    {
        wxEntryCleanup();
        return 1;
    }
    bool ok = true;
    // Keep real errors visible on stderr without opening modal log dialogs.
    delete wxLog::SetActiveTarget(new wxLogStderr);
    const wxSize screen = wxGetDisplaySize();
    const wxRect area = wxDisplay().GetClientArea();
    if (screen.x <= 0 || screen.y <= 0 || area.width <= 0 || area.height <= 0)
    {
        std::fprintf(stderr, "Invalid display geometry: %d,%d workarea=%d,%d\n",
                     screen.x, screen.y, area.width, area.height);
        ok = false;
    }
    if (wxDisplay::GetFromPoint(wxPoint(screen.x / 2, screen.y / 2)) == wxNOT_FOUND)
    {
        std::fprintf(stderr, "Display does not contain its screen centre\n");
        ok = false;
    }
    {
        wxFrame frame(nullptr, wxID_ANY, "wx GTK regression");
        if (frame.GetSize().x <= 0 || frame.GetSize().y <= 0)
            ok = false;
        wxBitmap bitmap(160, 80);
        wxMemoryDC dc(bitmap);
        wxGraphicsContext* gc = wxGraphicsContext::Create(dc);
        const guint handler = g_log_set_handler("Pango", G_LOG_LEVEL_CRITICAL,
                                                RecordPangoError, nullptr);
        if (gc)
        {
            gc->SetFont(wxSystemSettings::GetFont(wxSYS_DEFAULT_GUI_FONT), *wxBLACK);
            wxDouble width = 0, height = 0;
            gc->GetTextExtent("HarmonyOS", &width, &height);
            if (width <= 0 || height <= 0)
                ok = false;
            delete gc;
        }
        else
            ok = false;
        g_log_remove_handler("Pango", handler);
        if (pango_errors != 0)
            ok = false;
    }
    wxTheApp->OnExit();
    wxEntryCleanup();
    std::printf("wx GTK GUI regressions: %s (Pango errors=%u)\n", ok ? "OK" : "FAILED", pango_errors);
    return ok ? 0 : 1;
}
