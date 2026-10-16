/* engine_flow.mjs — uBlock Origin @gorhill/ubo-core 消费者端到端用例
 *
 * 用法: node engine_flow.mjs <path-to-ubo-core/index.js>
 *
 * 真实驱动被测包 API（R34：非空壳）：enableWASM → StaticNetFilteringEngine.create
 * → useLists → matchRequest（block / exception / no-match / 类型限定）
 * → serialize → deserialize → 再次匹配。输出 ENGINE_FLOW=<passed>/<total>。
 */
import { pathToFileURL } from 'node:url';

const libPath = process.argv[2];
if (!libPath) {
    console.error('usage: engine_flow.mjs <path-to-ubo-core/index.js>');
    process.exit(2);
}

let pass = 0;
let fail = 0;
const check = (name, cond, detail = '') => {
    if (cond) { pass += 1; console.log(`  [ok] ${name}`); }
    else { fail += 1; console.log(`  [FAIL] ${name}${detail ? ' — ' + detail : ''}`); }
};

const mod = await import(pathToFileURL(libPath).href);

// 1. WebAssembly 制品可用（OHOS aarch64 node 上验证）
const wasmOk = await mod.enableWASM();
check('enableWASM() === true', wasmOk === true, `got ${wasmOk}`);

// 2. 静态网络过滤引擎：编译过滤列表并逐条匹配
const snfe = await mod.StaticNetFilteringEngine.create();
await snfe.useLists([{
    name: 'test',
    raw: '||example.net^\n@@||allowed.example.net^\n||ads.example.com^$script',
}]);
const match = (originURL, url, type) => snfe.matchRequest({ originURL, url, type });

check('block pure-hostname filter (||example.net^)',
      match('https://www.example.com/', 'https://sub.example.net/', 'image') === 1);
check('exception filter wins (@@||allowed.example.net^)',
      match('https://www.example.com/', 'https://allowed.example.net/', 'image') === 2);
check('no match for unrelated host (example.org)',
      match('https://www.example.com/', 'https://example.org/', 'image') === 0);
check('type-scoped block applies to script',
      match('https://example.com/', 'https://ads.example.com/a.js', 'script') === 1);
check('type-scoped block not applied to image',
      match('https://example.com/', 'https://ads.example.com/a.png', 'image') === 0);

// 3. 序列化 / 反序列化（引擎状态可持久化，OHOS 快速冷启动路径）
// 注意：上游 SNFE 只允许单个实例（index.js "Only a single instance is supported"），
// 故反序列化必须作用在同一实例上，不能再次 create()。
const serialized = await snfe.serialize();
check('serialize() returns non-empty string',
      typeof serialized === 'string' && serialized.length > 0);
await snfe.deserialize(serialized);
check('deserialized engine still blocks',
      snfe.matchRequest({
          originURL: 'https://www.example.com/',
          url: 'https://sub.example.net/',
          type: 'image',
      }) === 1);

console.log(`ENGINE_FLOW=${pass}/${pass + fail}`);
process.exit(fail === 0 ? 0 : 1);
