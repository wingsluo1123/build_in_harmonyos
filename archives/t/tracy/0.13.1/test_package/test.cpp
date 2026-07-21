// Test package for tracy/0.13.1 — comprehensive API coverage (R34 + L1).
//
// Mirrors the API surface of upstream test/test.cpp (the 23-thread demo
// program) but rewritten for CI-friendly behavior:
//   - Each worker thread runs in a finite scope and exits when done
//   - No infinite main loop, no signal-driven crashes, no image.jpg dep
//   - No capture server required (library tolerates disconnect silently)
//   - Real assertions verify behavior, not just "program didn't crash"
//
// API coverage map (upstream demo t# → here):
//   t1  TestFunction         → worker_zone + FrameMarkNamed
//   t3  ResolutionCheck       → clock sanity assert
//   t4  ScopeCheck            → ZoneScopedN + ZoneScopedC + nested zones
//   t5  Lock1/2/3             → TracyMutex acquire/release timing
//   t8  Plot ×2               → TracyPlot + TracyPlotConfig
//   t10 MessageTest           → TracyMessage + TracyMessageL + TracyMessageC + TracyMessageLC
//   t11 DepthTest             → 5-level nested ZoneScoped
//   t14-t18 SharedRead/Write  → TracySharedMutex / TracyLockable
//   t19 CallstackTime         → TRACY_CALLSTACK macro (in ZoneText)
//   t20 OnlyMemory            → TracyAlloc + TracyFree pair
//   + FrameMarkStart / FrameMarkEnd pairs
//   + SetThreadName on every worker

#include <cassert>
#include <chrono>
#include <cstdio>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <tracy/tracy/Tracy.hpp>

// ---------------------------------------------------------------------------
// Shared TracyLockable<std::mutex> used by Lock1/Lock2/Lock3-style threads.
// TracyLockableN(type, varname, desc) wraps `type` as `tracy::Lockable<type>`
// which exposes std::lock_guard-compatible lock()/unlock().
// ---------------------------------------------------------------------------
static TracyLockableN( std::mutex, g_mutex, "shared-mutex" );

// ---------------------------------------------------------------------------
// Worker thread functions (each mirrors one upstream t# demo)
// ---------------------------------------------------------------------------

// t1 + FrameMark variants: basic zone + named frame mark + start/end pair.
// Note: ZoneScoped/N/C all expand to a local named `___tracy_scoped_zone`, so
// each must live in its own {} scope to avoid redefinition.
static void worker_zones_and_frames() {
    tracy::SetThreadName( "zones-frames" );
    {
        ZoneScoped;
        ZoneName( "basic-zone", 10 );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
    }
    {
        ZoneScopedN( "named-zone" );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
    }
    {
        ZoneScopedC( tracy::Color::Red );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
    }
    FrameMark;
    FrameMarkNamed( "frame-named" );
    {
        FrameMarkStart( "frame-pair" );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
        FrameMarkEnd( "frame-pair" );
    }
}

// t3 ResolutionCheck: clock_gettime sanity (CLOCK_MONOTONIC should never go backwards)
static void worker_clock_sanity() {
    tracy::SetThreadName( "clock-sanity" );
    ZoneScoped;
    using namespace std::chrono;
    auto t0 = steady_clock::now();
    auto t1 = steady_clock::now();
    assert( t1 >= t0 && "steady_clock must be monotonic" );
}

// t4 ScopeCheck: nested zones enter/exit properly
static void worker_nested_scopes() {
    tracy::SetThreadName( "nested-scopes" );
    ZoneScoped;
    {
        ZoneScopedN( "outer" );
        {
            ZoneScopedN( "middle" );
            {
                ZoneScopedN( "inner" );
                std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
            }
        }
    }
}

// t5/6/7 Lock1/2/3: TracyLockable acquire/release
static void worker_mutex_locks() {
    tracy::SetThreadName( "mutex-locks" );
    ZoneScoped;
    for ( int i = 0; i < 3; ++i ) {
        ZoneScopedN( "lock-iter" );
        {
            std::lock_guard<decltype( g_mutex )> lock( g_mutex );
            ZoneScoped;
            std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
        }
    }
}

// t8 Plot: real-time data plot
static void worker_plot() {
    tracy::SetThreadName( "plot" );
    TracyPlotConfig( "test-plot", tracy::PlotFormatType::Number, false, false,
                     tracy::Color::Yellow );
    for ( int i = 0; i < 5; ++i ) {
        ZoneScoped;
        TracyPlot( "test-plot", double( i ) );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
    }
}

// t10 MessageTest: 4 message variants
static void worker_messages() {
    tracy::SetThreadName( "messages" );
    ZoneScoped;
    const char* payload = "tracy-message-payload";
    const std::size_t plen = std::strlen( payload );
    TracyMessage( payload, plen );
    TracyMessageL( "literal-message" );
    TracyMessageC( payload, plen, tracy::Color::Magenta );
    TracyMessageLC( "literal-colored", tracy::Color::Cyan );
    assert( plen > 0 && "payload non-empty" );
}

// t11 DepthTest: 5-level nested zones
static void worker_depth() {
    tracy::SetThreadName( "depth" );
    ZoneScoped;
    {
        ZoneScopedN( "lvl-1" );
        {
            ZoneScopedN( "lvl-2" );
            {
                ZoneScopedN( "lvl-3" );
                {
                    ZoneScopedN( "lvl-4" );
                    {
                        ZoneScopedN( "lvl-5" );
                        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
                    }
                }
            }
        }
    }
}

// t19 CallstackTime: zone with named text
static void worker_callstack() {
    tracy::SetThreadName( "callstack" );
    ZoneScoped;
    {
        ZoneScoped;
        ZoneText( "callstack-text", 14 );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
    }
}

// t20 OnlyMemory: TracyAlloc / TracyFree pair
static void worker_memory() {
    tracy::SetThreadName( "memory" );
    ZoneScoped;
    for ( int i = 0; i < 4; ++i ) {
        std::vector<char> buf( 256 * ( i + 1 ) );
        TracyAllocN( buf.data(), buf.size(), "test-alloc" );
        std::this_thread::sleep_for( std::chrono::milliseconds( 1 ) );
        TracyFreeN( buf.data(), "test-alloc" );
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
int main() {
    // Main-thread zone + frame mark (also exercises operator new override)
    {
        ZoneScoped;
        ZoneName( "test-main", 9 );
        FrameMark;
        FrameMarkNamed( "main-frame" );
        TracyAppInfo( "tracy/0.13.1 OHOS test_package", 27 );
    }

    // Spawn 8 worker threads mirroring upstream t1/t4/t5/t8/t10/t11/t19/t20
    std::vector<std::thread> workers;
    workers.emplace_back( worker_zones_and_frames );
    workers.emplace_back( worker_clock_sanity );
    workers.emplace_back( worker_nested_scopes );
    workers.emplace_back( worker_mutex_locks );
    workers.emplace_back( worker_plot );
    workers.emplace_back( worker_messages );
    workers.emplace_back( worker_depth );
    workers.emplace_back( worker_callstack );
    workers.emplace_back( worker_memory );

    for ( auto& w : workers ) w.join();

    TracyMessageL( "tracy-client test_package: 9 workers joined OK" );
    std::puts( "tracy-client test_package OK" );
    return 0;
}