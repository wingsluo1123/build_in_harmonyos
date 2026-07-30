import cairo


assert cairo.version_info == (1, 29, 0)

surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 2, 2)
context = cairo.Context(surface)
context.set_source_rgba(0.25, 0.5, 0.75, 1.0)
context.paint()
surface.flush()

assert surface.get_width() == 2
assert surface.get_height() == 2
assert surface.get_stride() >= 8
assert len(surface.get_data()) >= 16
assert any(surface.get_data())

print("pycairo functional checks passed: 6")
