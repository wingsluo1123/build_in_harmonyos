#include "mir.h"
#include "mir-gen.h"
#include <inttypes.h>
#include <stdio.h>

static MIR_item_t load_add(MIR_context_t ctx) {
  MIR_scan_string(ctx, "m: module\n export add\n add: func i64, i64:a, i64:b\n local i64:r\n add r, a, b\n ret r\n endfunc\n endmodule\n");
  MIR_module_t module = DLIST_HEAD(MIR_module_t, *MIR_get_module_list(ctx));
  MIR_item_t item = DLIST_TAIL(MIR_item_t, module->items);
  MIR_load_module(ctx, module);
  return item;
}

int main(void) {
  const int64_t inputs[][2] = {{19, 23}, {-19, 23}, {0, 0}, {INT64_C(4294967296), 17}};
  MIR_context_t ctx = MIR_init();
  if (!ctx) return 1;
  MIR_item_t item = load_add(ctx);
  MIR_link(ctx, MIR_set_interp_interface, NULL);
  for (size_t i = 0; i < sizeof(inputs)/sizeof(inputs[0]); ++i) {
    MIR_val_t args[2], result;
    args[0].i = inputs[i][0]; args[1].i = inputs[i][1];
    MIR_interp_arr(ctx, item, &result, 2, args);
    if (result.i != inputs[i][0] + inputs[i][1]) return 2;
  }
  MIR_finish(ctx);
  /* Interpreter and generator own incompatible function item->data state.
     Each backend therefore uses its own freshly loaded public context. */
  for (int mode = 0; mode < 3; ++mode) {
    ctx = MIR_init();
    if (!ctx) return 3;
    item = load_add(ctx);
    MIR_gen_init(ctx);
    void (*interface)(MIR_context_t, MIR_item_t) = mode == 0 ? MIR_set_gen_interface
        : mode == 1 ? MIR_set_lazy_gen_interface : MIR_set_lazy_bb_gen_interface;
    MIR_link(ctx, interface, NULL);
    int64_t (*fn)(int64_t, int64_t) = (int64_t (*)(int64_t, int64_t))item->addr;
    if (!fn) return 4;
    /* First invocation enters the native lazy callback; later invocations
       exercise redirected generated code from the installed MIR package. */
    for (int repetition = 0; repetition < 2; ++repetition)
      for (size_t i = 0; i < sizeof(inputs)/sizeof(inputs[0]); ++i)
        if (fn(inputs[i][0], inputs[i][1]) != inputs[i][0] + inputs[i][1]) return 5 + mode;
    MIR_gen_finish(ctx);
    MIR_finish(ctx);
  }
  puts("CONSUMER_1_OF_1_PASS: installed interpreter + eager/lazy/lazy-BB signed OHOS ARM64 execution");
  return 0;
}
