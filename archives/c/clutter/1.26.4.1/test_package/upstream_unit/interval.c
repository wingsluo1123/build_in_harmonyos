#include <clutter/clutter.h>

static void
interval_initial_state (void)
{
  ClutterInterval *interval;
  int initial, final;
  const GValue *value;

  interval = clutter_interval_new (G_TYPE_INT, 0, 100);
  g_assert (CLUTTER_IS_INTERVAL (interval));
  g_assert (clutter_interval_get_value_type (interval) == G_TYPE_INT);

  clutter_interval_get_interval (interval, &initial, &final);
  g_assert_cmpint (initial, ==, 0);
  g_assert_cmpint (final, ==, 100);

  value = clutter_interval_compute (interval, 0);
  g_assert (G_VALUE_HOLDS_INT (value));
  g_assert_cmpint (g_value_get_int (value), ==, 0);

  value = clutter_interval_compute (interval, 1);
  g_assert (G_VALUE_HOLDS_INT (value));
  g_assert_cmpint (g_value_get_int (value), ==, 100);

  value = clutter_interval_compute (interval, 0.5);
  g_assert (G_VALUE_HOLDS_INT (value));
  g_assert_cmpint (g_value_get_int (value), ==, 50);

  clutter_interval_set_final (interval, 200);
  value = clutter_interval_peek_final_value (interval);
  g_assert (G_VALUE_HOLDS_INT (value));
  g_assert_cmpint (g_value_get_int (value), ==, 200);

  g_object_unref (interval);
}

static void
interval_transform (void)
{
  ClutterInterval *interval;
  GValue value = G_VALUE_INIT;
  const GValue *value_p = NULL;

  interval = clutter_interval_new_with_values (G_TYPE_FLOAT, NULL, NULL);

  g_value_init (&value, G_TYPE_DOUBLE);

  g_value_set_double (&value, 0.0);
  clutter_interval_set_initial_value (interval, &value);

  g_value_set_double (&value, 100.0);
  clutter_interval_set_final_value (interval, &value);

  g_value_unset (&value);

  value_p = clutter_interval_peek_initial_value (interval);
  g_assert (G_VALUE_HOLDS_FLOAT (value_p));
  g_assert_cmpfloat (g_value_get_float (value_p), ==, 0.f);

  value_p = clutter_interval_peek_final_value (interval);
  g_assert (G_VALUE_HOLDS_FLOAT (value_p));
  g_assert_cmpfloat (g_value_get_float (value_p), ==, 100.f);

  g_object_unref (interval);
}

static void
interval_from_script (void)
{
  ClutterScript *script = clutter_script_new ();
  ClutterInterval *interval;
  gchar *test_file;
  GError *error = NULL;
  GValue *initial, *final;

  test_file = g_strdup ("scripts/test-script-interval.json");
  clutter_script_load_from_file (script, test_file, &error);
  if (g_test_verbose () && error)
    g_printerr ("\tError: %s", error->message);

  g_assert_no_error (error);

  interval = CLUTTER_INTERVAL (clutter_script_get_object (script, "int-1"));
  initial = clutter_interval_peek_initial_value (interval);
  if (g_test_verbose ())
    g_test_message ("\tinitial ['%s'] = '%.2f'",
                    g_type_name (G_VALUE_TYPE (initial)),
                    g_value_get_float (initial));
  g_assert (G_VALUE_HOLDS (initial, G_TYPE_FLOAT));
  g_assert_cmpfloat (g_value_get_float (initial), ==, 23.3f);
  final = clutter_interval_peek_final_value (interval);
  if (g_test_verbose ())
    g_test_message ("\tfinal ['%s'] = '%.2f'",
                    g_type_name (G_VALUE_TYPE (final)),
                    g_value_get_float (final));
  g_assert (G_VALUE_HOLDS (final, G_TYPE_FLOAT));
  g_assert_cmpfloat (g_value_get_float (final), ==, 42.2f);

  interval = CLUTTER_INTERVAL (clutter_script_get_object (script, "int-2"));
  initial = clutter_interval_peek_initial_value (interval);
  g_assert (G_VALUE_HOLDS (initial, CLUTTER_TYPE_COLOR));
  final = clutter_interval_peek_final_value (interval);
  g_assert (G_VALUE_HOLDS (final, CLUTTER_TYPE_COLOR));

  g_object_unref (script);
  g_free (test_file);
}

/* OHOS 适配运行器：上游 CLUTTER_TEST_SUITE 展开的 main 会经
 * clutter_test_init → clutter_init 需 EGL 显示服务（OHOS 不可行），
 * 改为顺序调用上游测试函数（纯 CPU 路径）；script 数据用相对路径。
 */
#include <stdio.h>
int main (int argc, char **argv)
{
  (void) argc; (void) argv;
  interval_initial_state ();
  printf ("PASS /interval/initial-state\n");
  interval_transform ();
  printf ("PASS /interval/transform\n");
  interval_from_script ();
  printf ("PASS /interval/from-script\n");
  printf ("ALL 3 UNITS PASS\n");
  return 0;
}
