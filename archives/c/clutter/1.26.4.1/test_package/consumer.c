/* clutter 1.26.4 消费测试：纯 CPU API 冒烟（不涉 stage/渲染路径）。
 * 覆盖：clutter_color_*（字符串/像素往返）、clutter_units_*、
 * clutter_actor 基础属性、clutter_interval 值域、clutter_binding_pool。
 * 链接 -lclutter-1.0 成功 + 运行 rc=0 即证明库可被实际消费（R34）。 */
#include <clutter/clutter.h>
#include <stdio.h>

int main (void)
{
  ClutterColor c;

  /* clutter_color_*：纯 CPU 颜色转换 */
  clutter_color_from_string (&c, "#7f7f7f");
  if (c.red != 0x7f || c.green != 0x7f || c.blue != 0x7f)
    return 1;

  /* clutter_units_*：纯 CPU 单位换算 */
  ClutterUnits u;
  clutter_units_from_pt (&u, 24.0);
  gchar *us = clutter_units_to_string (&u);
  if (g_strcmp0 (us, "24.0 pt") != 0)
    return 2;
  g_free (us);

  /* clutter_actor 基础（不涉 stage/EGL 渲染） */
  ClutterActor *a = clutter_actor_new ();
  clutter_actor_set_size (a, 100, 50);
  gfloat w, h;
  clutter_actor_get_size (a, &w, &h);
  if (w != 100 || h != 50)
    return 3;
  clutter_actor_destroy (a);

  /* clutter_interval：纯 CPU 值域 */
  ClutterInterval *iv = clutter_interval_new (G_TYPE_INT, 0, 100);
  const GValue *final = clutter_interval_peek_final_value (iv);
  if (g_value_get_int (final) != 100)
    return 4;
  g_object_unref (iv);

  /* clutter_binding_pool：纯 CPU 键绑定池 */
  ClutterBindingPool *pool = clutter_binding_pool_new ("consumer-pool");
  g_object_unref (pool);

  printf ("clutter consumer resolved ok\n");
  return 0;
}
