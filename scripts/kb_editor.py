#!/usr/bin/env python3
"""kb_editor.py — 主编知识草稿审核统一工具

用法: python3 scripts/kb_editor.py <command> [options]

commands:
  pr-map [--refresh]                构建/增量更新 草稿→来源PR 映射表
  batch [--size N] [--start-offset N]  按 PR 编号升序构建批次清单
  audit --batch-file F              四维审核 → 决策表 TSV
  promote --decisions F             按决策表批量 promote 接纳草稿
  fix [--entries F]                 promote 后置字段修复（新 E 条目）
  report --decisions F --batch N    生成审核报告 Markdown
  publish --branch NAME [--push]    暂存 knowledge/ 并提交（可选推送）

流程文档: knowledge/operations/editor-review-workflow.md
依赖: graph promote / draft-review（scripts/ohc-run.py）
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DRAFTS = REPO / 'knowledge' / 'drafts'
GRAPH = REPO / 'knowledge' / 'graph'
STATE_DIR = REPO / '.ohc' / 'kb-editor'
PR_MAP_PATH = STATE_DIR / 'pr-map.json'

FIELD_RE = re.compile(r'^([a-z_0-9]+):\s*(.*)$')
GIT = 'git'
MERGE_RE = re.compile(r'^([0-9a-f]+) (!\d+) merge (feat/\S+) into main$')


def g(*args, cwd=None):
    r = subprocess.run([GIT] + list(args), capture_output=True, text=True,
                       cwd=str(cwd or REPO), timeout=600)
    return r.stdout.strip()


# ─────────────────────────── pr-map ───────────────────────────

def _load_adds(refresh=False):
    """全量导出草稿添加记录（缓存, origin/main 签名控制新鲜度）。

    返回 (adds, first_add, order):
      adds: [(h, src, an, ae, subj, files)] 按时间倒序
      first_add: {draft_name: (h, src, an, ae, subj)}
      order: 按添加时间正序的草稿名列表（≈PR 时间序, batch 排序用）
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    adds_cache = STATE_DIR / 'adds-raw.txt'
    sig = g('rev-parse', 'origin/main')
    need = refresh or not adds_cache.exists()
    if not need:
        head = adds_cache.read_text(encoding='utf-8', errors='replace').split('\n', 1)[0]
        need = head.strip() != f'#sig {sig}'
    if need:
        raw = g('log', '--all', '--source', '--diff-filter=A', '--name-only',
                '--format=%x00%H|%S|%an|%ae|%s', '--', 'knowledge/drafts/')
        adds_cache.write_text(f'#sig {sig}\n{raw}', encoding='utf-8')
    else:
        raw = adds_cache.read_text(encoding='utf-8', errors='replace').split('\n', 1)[1]
    adds = []
    for block in raw.split('\x00'):
        if not block.strip():
            continue
        lines = block.splitlines()
        if not lines:
            continue
        parts5 = lines[0].split('|', 4)
        if len(parts5) != 5:
            continue
        h, src, an, ae, subj = parts5
        files = [l.strip() for l in lines[1:] if l.strip().endswith('.kv')]
        adds.append((h, src, an, ae, subj, files))
    first_add, order = {}, []
    for h, src, an, ae, subj, files in adds:      # 倒序遍历, 后见者更早
        for f in files:
            n = Path(f).stem
            if n not in first_add:
                order.append(n)                    # 时间正序（倒序遍历中首见=最晚, 逆放）
            first_add[n] = (h, src, an, ae, subj)
    order.reverse()                                # 现为时间正序
    return adds, first_add, order


def _ancestry_pr(h):
    """单条 ancestry 查询（20s 超时, HMDFS IO 抖动保护）。返回 (pr, branch) 或 None。"""
    try:
        r = subprocess.run([GIT, 'log', '--ancestry-path', '--merges', '--oneline',
                            f'{h}..origin/main'], capture_output=True, text=True,
                           cwd=str(REPO), timeout=20)
        tail = [l for l in r.stdout.splitlines() if l.strip()]
        if tail:
            mm = MERGE_RE.match(tail[-1])
            if mm:
                return mm.group(2), mm.group(3)
        return None
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', ''


def _pr_api(number):
    """GitCode 单 PR 匿名 API（权威 title/author/branch/state）。失败返回 None（回退 commit 值）。"""
    import urllib.request
    url = f'https://gitcode.com/api/v5/repos/OpenHarmonyPCDeveloper/build_in_harmonyos/pulls/{number}'
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            d = json.loads(r.read().decode('utf-8'))
        return {'title': d.get('title', ''),
                'author': (d.get('user') or {}).get('login', ''),
                'branch': ((d.get('head') or {}).get('ref') or '').replace('feat/', ''),
                'state': d.get('state', '')}
    except Exception:
        return None


# ─────────────────────────── pr-info ───────────────────────────

def _pr_commit_email(number, login=''):
    """从 PR 分支 commit 反查提交者邮箱（GitCode API 不提供 email, 隐私保护）。

    !N merge commit 第二父链，三层匹配（GitCode noreply email 格式自带 login:
    `{random}.{login}@noreply.gitcode.com`）:
      1. email 后缀 `.{login}@noreply.gitcode.com`（本人 noreply, 最权威）
      2. author name == login 的最早 commit（本人真实邮箱, 如 liujsh2023@lzu.edu.cn）
      3. 最早普通 commit（fork 基线可能错配, 最后手段）
    """
    out = g('log', 'origin/main', '--format=%H', f'--grep=!{number} merge')
    mc = out.splitlines()[-1].strip() if out.strip() else ''
    if not mc:
        return ''
    rows = g('log', f'{mc}^2', '--format=%an|%ae|%s', '-20').splitlines()
    triples = []
    for r in rows:
        p = r.split('|', 2)
        if len(p) != 3:
            continue
        an, em, subj = p
        if not em or 'noreply.atomgit' in em:
            continue
        if subj.startswith('Merge') or subj.startswith('/') or subj.startswith('!'):
            continue
        triples.append((an, em))
    if not triples:
        return ''
    if login:
        for an, em in triples:
            if em.lower().endswith(f'.{login.lower()}@noreply.gitcode.com'):
                return em                          # 层1: 本人 noreply
        own = [(an, em) for an, em in triples if an.strip().lower() == login.strip().lower()]
        if own:
            return own[-1][1]                      # 层2: author name 匹配
    return ''                                      # 匹配不到宁缺毋滥（巨型基线分支回退必错配）


def cmd_pr_info(numbers, as_json=False, fix_map=False):
    """按 PR 号反查核对（GitCode 单 PR API）：标题/作者/状态/源分支。

    --fix-map: 将核对结果回写 pr-map 缓存中该 PR 的所有条目（标题/作者校正）。
    """
    out = {}
    for n in numbers:
        d = _pr_api(n)
        if not d:
            out[n] = {'error': 'API 不可达或 PR 不存在'}
            continue
        d['email'] = _pr_commit_email(n, d.get('author', ''))
        out[n] = d
    if fix_map and PR_MAP_PATH.exists():
        m = json.loads(PR_MAP_PATH.read_text(encoding='utf-8'))
        fixed = 0
        for k, v in m.items():
            hit = next((d for num, d in out.items() if f'!{num}' == v.get('pr')), None)
            if hit and hit.get('title') and hit['title'] != v.get('title'):
                v['title'] = hit['title']
                if hit.get('author'):
                    v['author'] = hit['author']
                if hit.get('email') and not v.get('email'):
                    v['email'] = hit['email']
                fixed += 1
        PR_MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'pr-map 回写校正 {fixed} 条')
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        for n, d in out.items():
            if 'error' in d:
                print(f'!{n}: {d["error"]}')
            else:
                em = f" <{d['email']}>" if d.get('email') else ''
                print(f"!{n}: [{d.get('state','')}] {d.get('author','')}{em} | {d.get('title','')}")


def cmd_pr_map(refresh=False, limit=0, batch_file=None):
    """草稿 → 来源 PR 映射（增量缓存）。

    反查算法: 最早添加 commit（feat commit, 标题=PR 标题, author=作者）
              → ancestry-path 最早 merge → !N
    注意: 草稿名里的数字段与 PR 编号无对应关系，不可作为反查依据。
    --batch-file F: 只查批次文件内的草稿（推荐, 全量较慢）。
    --limit N: 无批次文件时最多新查 N 条（分片累积）。
    """
    cache = {}
    if PR_MAP_PATH.exists() and not refresh:
        cache = json.loads(PR_MAP_PATH.read_text(encoding='utf-8'))

    _, first_add, _ = _load_adds(refresh)

    if batch_file:
        targets = [l.split('\t')[0] for l in Path(batch_file).read_text(encoding='utf-8')
                   .splitlines()[1:] if l.strip()]
    else:
        targets = sorted({p.stem for p in DRAFTS.glob('*.kv')})

    existing = {p.stem for p in DRAFTS.glob('*.kv')}
    result = {k: v for k, v in cache.items() if k in existing}
    api_cache = {}
    n_new = n_merge_query = n_timeout = 0
    budget = limit if (limit and not batch_file) else float('inf')
    for name in targets:
        if n_new >= budget:
            break
        if name in result:
            continue
        fa = first_add.get(name)
        if not fa:
            result[name] = {'pr': '', 'title': '', 'author': '', 'email': '',
                            'merged': False, 'branch': '', 'last_activity': '',
                            'note': 'git无添加记录(孤儿)'}
            n_new += 1
            continue
        h, src, an, ae, subj = fa
        n_merge_query += 1
        m = _ancestry_pr(h)
        if m == ('TIMEOUT', ''):
            result[name] = {'pr': '', 'branch': '', 'title': subj, 'author': an,
                            'email': ae, 'merged': False, 'last_activity': '',
                            'note': 'ancestry查询超时(下次重试)'}
            n_timeout += 1
        elif m:
            pr_no = m[0][1:]                      # '!13563' -> '13563'
            title, author, branch = subj, an, m[1]
            # API 校正：commit subject 可能是评论命令(/rebuild)或 Merge 文本; PR 标题/登录名更权威
            if pr_no not in api_cache:
                api_cache[pr_no] = _pr_api(pr_no)
            api = api_cache[pr_no]
            if api:
                if api.get('title'):
                    title = api['title']
                if api.get('author'):
                    author = api['author']
                if api.get('branch'):
                    branch = api['branch']
            result[name] = {'pr': m[0], 'branch': branch, 'title': title,
                            'author': author,
                            'email': _pr_commit_email(pr_no, author) or ae,
                            'merged': True,
                            'last_activity': '', 'note': ''}
        else:
            rb = src.replace('refs/remotes/origin/', '').replace('refs/heads/', '').strip()
            act = g('log', '-1', '--format=%ci', f'origin/{rb}') if rb and rb != 'main' else ''
            result[name] = {'pr': '', 'branch': rb, 'title': subj,
                            'author': an, 'email': ae, 'merged': False,
                            'last_activity': act[:10], 'note': '来源PR未合入main'}
        n_new += 1

    PR_MAP_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    merged = sum(1 for v in result.values() if v.get('merged'))
    print(f'映射表: {len(result)} 条 | 已合入 {merged} | 本次新查 {n_new} '
          f'(ancestry {n_merge_query}, 超时 {n_timeout})')
    print(f'缓存: {PR_MAP_PATH}')


# ─────────────────────────── batch ───────────────────────────

def cmd_batch(size=100, start_offset=0):
    """构建批次：按草稿添加时间正序（≈PR 时间序）取 N 条。

    pr-map 缓存中已确认未合入（merged=false）的草稿不进批次（DEFER 暂缓）；
    未精查的草稿进入批次, 由后续 pr-map --batch-file + audit 揭示并过滤。
    """
    cache = {}
    if PR_MAP_PATH.exists():
        cache = json.loads(PR_MAP_PATH.read_text(encoding='utf-8'))
    _, _, order = _load_adds()
    existing = {p.stem for p in DRAFTS.glob('*.kv')}
    pool, deferred = [], 0
    for name in order:
        if name not in existing:
            continue
        v = cache.get(name)
        if v and not v.get('merged') and v.get('note') == '来源PR未合入main':
            deferred += 1
            continue
        pool.append(name)
    for name in sorted(existing - set(order)):    # adds 无记录者垫底
        pool.append(name)
    batch = pool[start_offset:start_offset + size]
    out = STATE_DIR / f'batch-{size}-{start_offset}.tsv'
    with out.open('w', encoding='utf-8') as fp:
        fp.write('name\tpr\ttitle\tauthor\temail\tstatus\n')
        for n in batch:
            v = cache.get(n, {})
            st = 'OK' if v.get('merged') else 'PENDING_MAP'
            fp.write('\t'.join([n, v.get('pr', ''), v.get('title', '').replace('\t', ' '),
                                v.get('author', ''), v.get('email', ''), st]) + '\n')
    print(f'批次: {len(batch)} 条 (offset {start_offset}) | 预过滤 DEFER {deferred} | 输出 {out}')
    print(f'下一步: python3 scripts/kb_editor.py pr-map --batch-file {out}')


# ─────────────────────────── audit ───────────────────────────

PLACEHOLDER = re.compile(r'(\(请填写\)|<TODO>|TODO[:：]|待补|^["\']*\s*["\']?$|\bN/A\b)', re.I)
SEV_MAP = {'P0': '3', 'P1': '2', 'P2': '1', 'P3': '1', 'HIGH': '3', 'MEDIUM': '2', 'LOW': '1'}


def parse_kv(path):
    """解析 kv 文件。支持 YAML 多行块（| 与 >）：块内容并入字段值。"""
    d = {}
    try:
        lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return d
    i = 0
    while i < len(lines):
        mm = FIELD_RE.match(lines[i])
        if not mm:
            i += 1
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val in ('|', '>', '|-', '>-', '|+', '>+'):
            block = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == '':
                    block.append('')
                    j += 1
                    continue
                if not FIELD_RE.match(nxt) and (nxt.startswith(' ') or nxt.startswith('\t')):
                    block.append(nxt.strip())
                    j += 1
                else:
                    break
            while block and block[-1] == '':
                block.pop()
            d[key] = ' '.join(block).strip().strip('"')
            i = j
        else:
            d[key] = val.strip('"')
            i += 1
    return d


CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def is_emptyish(v):
    if not v:
        return True
    # CJK 字符信息密度高, 阈值 3; ASCII 阈值 8
    minlen = 3 if CJK_RE.search(v) else 8
    if len(v.strip()) < minlen:
        return True
    return bool(PLACEHOLDER.search(v))


def jaccard(a, b):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0


def cmd_audit(batch_file):
    """四维审核 → 决策表。需要先运行 ohc-run.py draft-review --json 生成全量预审。"""
    bf = Path(batch_file)
    if not bf.exists():
        sys.exit(f'批次文件不存在: {bf}')
    drv_path = STATE_DIR / 'draft-review-full.json'
    if not drv_path.exists():
        sys.exit('先运行: python3 scripts/ohc-run.py draft-review --json > '
                 f'{drv_path} （或手动重定向）')
    rv = {r['draft']: r for r in json.loads(drv_path.read_text(encoding='utf-8'))['reports']}

    formal = {}
    for f in GRAPH.glob('E*.kv'):
        kv = parse_kv(f)
        if kv.get('error_signature'):
            formal[f.stem] = kv['error_signature']

    rows = []
    pm = json.loads(PR_MAP_PATH.read_text(encoding='utf-8')) if PR_MAP_PATH.exists() else {}
    for line in bf.read_text(encoding='utf-8').splitlines()[1:]:
        p = line.split('\t')
        name = p[0]
        pv = pm.get(name) or {}
        if pv and not pv.get('merged') and pv.get('note') == '来源PR未合入main':
            rows.append(dict(name=name, decision='DEFER', reason='来源PR未合入main(暂缓)',
                             verdict='', top_id='', top_score=0.0, best_f='', best_s=0.0,
                             md=True, q_sig=False, q_rc=False, q_rec=False, sev=''))
            continue
        kv = parse_kv(DRAFTS / f'{name}.kv')
        sig, rc, rec = kv.get('error_signature', ''), kv.get('root_cause', ''), kv.get('rec_approach', '')
        r = rv.get(name, {})
        similar = r.get('similar', [])
        top = similar[0] if similar else None
        best_f, best_s = '', 0.0
        if sig:
            for eid, fsig in formal.items():
                s = jaccard(sig, fsig)
                if s > best_s:
                    best_f, best_s = eid, s
        rows.append(dict(name=name, md=bool((DRAFTS / f'{name}.md').exists()),
                         q_sig=bool(sig) and not is_emptyish(sig),
                         q_rc=bool(rc) and not is_emptyish(rc),
                         q_rec=bool(rec) and not is_emptyish(rec),
                         sev=kv.get('severity', ''), verdict=r.get('verdict', 'NOT_SCANNED'),
                         top_id=top['id'] if top else '', top_score=top['score'] if top else 0.0,
                         best_f=best_f, best_s=round(best_s, 2)))

    dup_pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i], rows[j]
            if a.get('q_sig') and b.get('q_sig'):
                ka, kb = parse_kv(DRAFTS / f"{a['name']}.kv"), parse_kv(DRAFTS / f"{b['name']}.kv")
                s = jaccard(ka.get('error_signature', ''), kb.get('error_signature', ''))
                if s >= 0.8:
                    dup_pairs.append((a['name'], b['name'], round(s, 2)))

    def decide(r):
        if not (r['q_sig'] and r['q_rc'] and r['q_rec']):
            return 'REJECT', 'empty_core_fields'
        if not r['md']:
            return 'REJECT', 'no_md_pair'
        if r['verdict'] == 'merge-into' or r['top_score'] >= 0.7:
            return 'REJECT', f"dup_formal_{r['top_id']}_{r['top_score']}"
        if r['best_s'] >= 0.8:
            return 'REJECT', f"dup_formal_selfcheck_{r['best_f']}_{r['best_s']}"
        if r['verdict'] == 'merge-into' or 0.5 <= r['top_score'] < 0.7:
            return 'REVIEW', f"similar_{r['top_id']}_{r['top_score']}"   # 人工裁定(批次1教训: 误判存在)
        return 'ACCEPT', ''

    for r in rows:
        if r.get('decision') == 'DEFER':
            continue
        r['decision'], r['reason'] = decide(r)
    score = lambda r: (r.get('q_sig', 0) + r.get('q_rc', 0) + r.get('q_rec', 0),
                       len(parse_kv(DRAFTS / f"{r['name']}.kv").get('error_signature', '')), 0)
    dup_names = set()
    for a, b, _s in dup_pairs:
        ra = next(x for x in rows if x['name'] == a)
        rb = next(x for x in rows if x['name'] == b)
        dup_names.add(b if score(ra) >= score(rb) else a)
    for r in rows:
        if r['name'] in dup_names and r['decision'] == 'ACCEPT':
            r['decision'], r['reason'] = 'REJECT', 'dup_in_batch'

    out = Path(batch_file).with_name(Path(batch_file).stem + '-decisions.tsv')
    with out.open('w', encoding='utf-8') as fp:
        fp.write('name\tdecision\treason\tverdict\ttop_sim\tsim_score\tselfcheck\tmd\tq_sig\tq_rc\tq_rec\n')
        for r in rows:
            fp.write('\t'.join([r['name'], r['decision'], r['reason'], r['verdict'],
                                r['top_id'], str(r['top_score']), r['best_f'], str(r['md']),
                                str(r['q_sig']), str(r['q_rc']), str(r['q_rec'])]) + '\n')
    c = collections.Counter(r['decision'] for r in rows)
    print(f'决策: {dict(c)} | REVIEW 待人工: '
          f'{[r["name"] for r in rows if r["decision"]=="REVIEW"][:5]}')
    print(f'输出: {out}')


# ─────────────────────────── promote ───────────────────────────

def cmd_promote(decisions):
    ohc = REPO / 'scripts' / 'ohc-run.py'
    log = STATE_DIR / 'promote.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    with log.open('a', encoding='utf-8') as fp:      # 追加模式: 多次调用不丢映射
        fp.write(f'\n# promote run {__import__("datetime").datetime.now().isoformat()}\n')
        for line in Path(decisions).read_text(encoding='utf-8').splitlines()[1:]:
            p = line.split('\t')
            if p[1] != 'ACCEPT':
                continue
            r = subprocess.run([sys.executable, str(ohc), 'graph', 'promote', p[0],
                                '--project-dir', str(REPO)], capture_output=True, text=True, timeout=600)
            fp.write(f"=== {p[0]} (exit={r.returncode}) ===\n{r.stdout}{r.stderr}\n")
            if r.returncode == 0:
                ok += 1
            else:
                fail += 1
    print(f'promote: 成功 {ok} | 失败 {fail}（失败含被合并检测吸收的草稿, 见日志）| {log}')


# ─────────────────────────── fix ───────────────────────────

TEMPLATE_FIELDS = {
    'id', 'trigger_tool', 'phase', 'error_signature', 'severity', 'category',
    'match_keywords', 'title', 'root_cause', 'affected_scope', 'verification_cmd',
    'rec_priority', 'rec_approach', 'rec_description', 'rec_command',
    'rec_auto_fix', 'rec_impl',
    'fallback_priority', 'fallback_approach', 'fallback_description',
    'fallback_command', 'fallback_auto_fix', 'fallback_impl',
    'fallback_2_priority', 'fallback_2_approach', 'fallback_2_description',
    'fallback_2_command', 'fallback_2_auto_fix', 'fallback_2_impl',
    'fallback2_priority', 'fallback2_approach', 'fallback2_description',
    'fallback2_command', 'fallback2_auto_fix', 'fallback2_impl',
    'forbid_1_pattern', 'forbid_1_reason', 'forbid_1_consequence',
    'forbid_2_pattern', 'forbid_2_reason', 'forbid_2_consequence',
    'principles', 'causes', 'caused_by', 'similar_to', 'conflicts_with',
    'prerequisite_of', 'doc_file', 'last_updated', 'source_event',
    'resolved_in', 'resolved_note', 'draft', 'contributor_id',
    'authors', 'source_pr', 'source_commit',
    'metrics_success_count', 'metrics_fail_count', 'metrics_confidence',
    'metrics_last_used', 'prescan_pattern', 'prescan_globs', 'prescan_severity',
}
FORBID_RE = re.compile(r'^forbid_\d+_(pattern|reason|consequence)$')
RENAME = {'keywords': 'match_keywords', 'approach': 'rec_approach',
          'verification': 'verification_cmd'}
PRINCIPLE_MAP = {
    'no-platform-macros-in-patches': 'P005', 'minimal-patch': 'P005',
    'posix-correct-minimal-patch': 'P005', 'upstreamable-patch': 'P005',
    'generated-files-are-read-only': 'P003', 'patch-generated-files': 'P003',
    'static-lib-first': 'P012', 'static-library-priority': 'P012',
    'hmdfs-symlink': 'P016', 'hmdfs-hardlink': 'P020', 'rpath-coverage': 'P009',
    'no-build-host-override': 'P001', 'llvm-toolchain': 'P010',
}
REL = {'similar_to', 'caused_by', 'prerequisite_of', 'causes', 'conflicts_with'}


def _new_entries_from_git():
    out = g('status', '--short', 'knowledge/graph/')
    ids = set()
    for l in out.splitlines():
        mm = re.search(r'(E\d+)\.kv', l)
        if mm and l.startswith(('??', 'A ')):
            ids.add(mm.group(1))
    return sorted(ids, key=lambda x: int(x[1:]))


def _trig_phase(cat, sig):
    c = (cat + ' ' + sig).lower()
    if 'cmake' in c: return 'cmake', 'build'
    if 'configure' in c or 'autotools' in c or 'config.guess' in c: return 'configure', 'configuration'
    if 'meson' in c: return 'meson', 'build'
    if 'conan' in c or 'pkg-config' in c or 'package' in c: return 'conan', 'packaging'
    if 'install' in c: return 'make', 'install'
    if 'test' in c: return 'ctest', 'test'
    return 'make', 'build'


def _fix_one(path):
    lines = Path(path).read_text(encoding='utf-8', errors='replace').splitlines(keepends=True)
    kv = {}
    for l in lines:
        mm = FIELD_RE.match(l)
        if mm:
            kv[mm.group(1)] = mm.group(2).strip()
    eid = kv.get('id', Path(path).stem)
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        mm = FIELD_RE.match(l)
        if not mm:
            out.append(l); i += 1; continue
        key, val = mm.group(1), mm.group(2).strip()
        j = i + 1
        if val in ('|', '>', '|-', '>-') or (val and j < len(lines) and not FIELD_RE.match(lines[j])):
            while j < len(lines) and (lines[j].strip() == '' or
                                      (not FIELD_RE.match(lines[j]) and lines[j][:1] in (' ', '\t'))):
                j += 1
        if key == 'severity':
            v0 = val.strip('"').split()[0] if val else ''
            out.append('severity:               %s\n' % (v0 if v0 in ('1', '2', '3') else SEV_MAP.get(v0.upper(), '2')))
            i = j; continue
        if key == 'rec_auto_fix' and val.lower() not in ('true', 'false'):
            out.append('rec_auto_fix:          false\n'); i = j; continue
        if key == 'principles' and val:
            mapped = []
            for w in (x.strip() for x in re.split(r'[,;|]', val) if x.strip()):
                hit = PRINCIPLE_MAP.get(w.lower())
                if hit and hit not in mapped:
                    mapped.append(hit)
                elif re.fullmatch(r'P\d{3}', w.upper()) and w.upper() not in mapped:
                    mapped.append(w.upper())
            out.append('principles:             ' + ', '.join(mapped) + '\n' if mapped else 'principles:               \n')
            i = j; continue
        if key in REL and val:
            i = j; continue          # 清空 relations（含多行块）
        is_std = key.lower() in TEMPLATE_FIELDS or FORBID_RE.match(key.lower())
        if not is_std:
            if key.lower() in RENAME and RENAME[key.lower()] not in kv:
                out.append(RENAME[key.lower()] + ':' + l[mm.end():].rstrip('\n') + '\n')
                out.extend(lines[i + 1:j])
            i = j; continue
        out.append(l); out.extend(lines[i + 1:j])
        i = j
    have = set()
    for l in out:
        mm = FIELD_RE.match(l)
        if mm:
            have.add(mm.group(1))
    trig, phase = _trig_phase(kv.get('category', ''), kv.get('error_signature', ''))
    rec = kv.get('rec_approach', '')
    add = []
    if 'doc_file' not in have: add.append(f'doc_file:               doc/{eid}.md')
    if 'trigger_tool' not in have: add.append(f'trigger_tool:           {trig}')
    if 'phase' not in have: add.append(f'phase:                  {phase}')
    if 'category' not in have: add.append('category:               ' + ('build-system, ohos' if trig in ('make', 'configure', 'cmake', 'meson') else 'ohos, packaging'))
    if 'match_keywords' not in have:
        kws = [w for w in re.split(r'[|\\\[\](){}.*+?^$\s,;:="]+', kv.get('error_signature', '')) if len(w) > 3][:6]
        add.append('match_keywords:         ' + (', '.join(kws) if kws else 'ohos, ' + trig))
    if 'affected_scope' not in have: add.append('affected_scope:         ' + (kv.get('title', 'general')[:60] or 'general'))
    if 'verification_cmd' not in have: add.append('verification_cmd:       # 以 source_pr CI 门禁为准（PR %s）' % kv.get('source_pr', 'n/a'))
    if 'rec_description' not in have:
        first = re.split(r'[。;；.\n]', rec)[0][:100] if rec else ''
        add.append('rec_description:        %s' % (first or '见 rec_approach'))
    if 'rec_priority' not in have: add.append('rec_priority:           1')
    if 'rec_auto_fix' not in have: add.append('rec_auto_fix:          false')
    if 'rec_impl' not in have: add.append('rec_impl:               manual')
    if add:
        if out and not out[-1].endswith('\n'):
            out[-1] += '\n'
        out.extend(a + '\n' for a in add)
    Path(path).write_text(''.join(out), encoding='utf-8')


def cmd_fix(entries_file=None):
    ids = ([l.strip() for l in Path(entries_file).read_text().splitlines() if l.strip()]
           if entries_file else _new_entries_from_git())
    n = 0
    for eid in ids:
        p = GRAPH / f'{eid}.kv'
        if p.exists():
            _fix_one(p)
            n += 1
    # index severity 数字化
    idx = GRAPH / 'index.tsv'
    rows, fixed = [], 0
    for l in idx.read_text(encoding='utf-8').splitlines(keepends=True):
        cols = l.split('\t')
        if len(cols) > 1 and cols[0].startswith('E') and cols[1].strip() in SEV_MAP:
            cols[1] = SEV_MAP[cols[1].strip()]
            fixed += 1
            rows.append('\t'.join(cols))
            if not rows[-1].endswith('\n'):
                rows[-1] += '\n'
        else:
            rows.append(l)
    idx.write_text(''.join(rows), encoding='utf-8')
    print(f'fix: {n} 条目已修复 | index severity 修正 {fixed} 行')
    print('后续: python3 scripts/ohc-run.py graph validate --fix --project-dir . 直至 0 error')


# ─────────────────────────── report ───────────────────────────

MR_URL = 'https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/'


def cmd_report(decisions, batch_no, date, out_path):
    m = json.loads(PR_MAP_PATH.read_text(encoding='utf-8')) if PR_MAP_PATH.exists() else {}

    # 从 promote 日志提取 草稿→E编号 映射（含被合并吸收的）
    pmap = {}
    log = STATE_DIR / 'promote.log'
    if log.exists():
        for mm in re.finditer(r'🎉 (\S+) → (E\d+) 提升完成', log.read_text(encoding='utf-8', errors='replace')):
            pmap[mm.group(1)] = mm.group(2)
        for mm in re.finditer(r'已移除合并草稿: (\S+)', log.read_text(encoding='utf-8', errors='replace')):
            pmap.setdefault(mm.group(1), '（并入相邻条目）')

    def pr_cell(name):
        v = m.get(name) or {}
        title = v.get('title', '').replace('|', '\\|')
        pr = v.get('pr', '')
        if pr:
            return f'[{pr} {title}]({MR_URL}{pr[1:]})'
        if title:
            act = v.get('last_activity', '')
            return f'{title}（PR 未合入 main{", 分支活跃 " + act if act else ""}）'
        return '—（无来源 PR 记录）'

    dec = [l.split('\t') for l in Path(decisions).read_text(encoding='utf-8').splitlines()[1:]]
    acc = [p for p in dec if p[1] == 'ACCEPT']
    rej = [p for p in dec if p[1] == 'REJECT']
    rev = [p for p in dec if p[1] == 'REVIEW']
    L = []
    L.append(f'# 草稿知识入库（{len(acc)} 条接纳 / {len(rej)} 条拒绝 / {len(rev)} 条待复核）—— 主编批次 {batch_no}')
    L.append('')
    L.append(f'> 审核日期：{date} ｜ 审核人：主编（OpenDesk editor 会话） ｜ 工具：scripts/kb_editor.py')
    L.append('> 原始 PR 编号及标题由草稿 git 添加记录反查自动填充；正式 PR 编号/邮箱由管理员补填。')
    L.append('')
    L.append(f'## 接纳清单（{len(acc)} 条）')
    L.append('')
    L.append('| 草稿原名称 | 接纳后编号 | 正式 PR 编号 | 原始 PR 编号及标题 | 作者 | 邮箱 | 状态 |')
    L.append('|-----------|-----------|-------------|-------------|------|------|------|')
    for p in acc:
        v = m.get(p[0]) or {}
        eid = pmap.get(p[0], '')
        mark = '✅(merged)' if eid == '（并入相邻条目）' else '✅'
        L.append(f"| {p[0]} | {eid} |  | {pr_cell(p[0])} | {v.get('author','')} | {v.get('email','')} | {mark} |")
    L.append('')
    if rej:
        L.append('')
        L.append(f'## 拒绝清单（{len(rej)} 条）')
        L.append('')
        L.append('| 草稿原名称 | 原始 PR 编号及标题 | 拒绝原因 |')
        L.append('|-----------|-------------|---------|')
        REASON_CN = {'empty_core_fields': '空壳草稿：核心三字段缺失或占位',
                     'no_md_pair': '无配套 .md 文档'}
        for p in rej:
            reason = REASON_CN.get(p[2], p[2])
            L.append(f'| {p[0]} | {pr_cell(p[0])} | {reason} |')
    df = [p for p in dec if p[1] == 'DEFER']
    if df:
        L.append('')
        L.append(f'## 暂缓清单（{len(df)} 条，来源 PR 未合入 main）')
        L.append('')
        L.append('| 草稿原名称 | 所在 feature 分支 | 分支最后活动 |')
        L.append('|-----------|-----------------|-------------|')
        for p in df:
            v = m.get(p[0]) or {}
            L.append(f"| {p[0]} | {v.get('branch','')} | {v.get('last_activity','')} |")
    if rev:
        L.append('')
        L.append(f'## 待复核清单（{len(rev)} 条，人工裁定）')
        L.append('')
        for p in rev:
            L.append(f'- {p[0]}：{p[2]}')
    L.append('')
    L.append('## 审查方法')
    L.append('')
    L.append('- 四维审核（事实/质量/有效性/重复性），流程见 knowledge/operations/editor-review-workflow.md')
    L.append('- 工具链：kb_editor.py pr-map → batch → audit → promote → fix → report → publish')
    L.append('')
    out = Path(out_path).expanduser()
    out.write_text('\n'.join(L) + '\n', encoding='utf-8')
    print(f'报告: {out}')


# ─────────────────────────── publish ───────────────────────────

def cmd_publish(branch, do_push, batch_no='N'):
    g('checkout', '-b', branch) if branch not in g('branch', '--list', branch) else None
    g('add', 'knowledge/')
    st = g('status', '--short', 'knowledge/')
    if not st:
        print('knowledge/ 无变更, 跳过提交')
        return
    msg = (f'knowledge: editor batch {batch_no} - promote/reject drafts (kb_editor.py)\n\n'
           f'- 工具: scripts/kb_editor.py (pr-map/batch/audit/promote/fix/report/publish)\n'
           f'- 流程: knowledge/operations/editor-review-workflow.md')
    r = subprocess.run([GIT, 'commit', '-m', msg], capture_output=True, text=True, cwd=str(REPO))
    print(r.stdout.strip() or r.stderr.strip())
    if do_push:
        r = subprocess.run([GIT, 'push', '-u', 'origin', branch], capture_output=True, text=True, cwd=str(REPO))
        print((r.stdout + r.stderr).strip()[-300:])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p0 = sub.add_parser('pr-info'); p0.add_argument('numbers', nargs='+'); p0.add_argument('--json', action='store_true'); p0.add_argument('--fix-map', action='store_true')
    p1 = sub.add_parser('pr-map'); p1.add_argument('--refresh', action='store_true'); p1.add_argument('--limit', type=int, default=0); p1.add_argument('--batch-file')
    p2 = sub.add_parser('batch'); p2.add_argument('--size', type=int, default=100); p2.add_argument('--start-offset', type=int, default=0)
    p3 = sub.add_parser('audit'); p3.add_argument('--batch-file', required=True)
    p4 = sub.add_parser('promote'); p4.add_argument('--decisions', required=True)
    p5 = sub.add_parser('fix'); p5.add_argument('--entries')
    p6 = sub.add_parser('report'); p6.add_argument('--decisions', required=True); p6.add_argument('--batch', required=True); p6.add_argument('--date', required=True); p6.add_argument('--out', required=True)
    p7 = sub.add_parser('publish'); p7.add_argument('--branch', required=True); p7.add_argument('--push', action='store_true'); p7.add_argument('--batch', default='N')
    a = ap.parse_args()
    {'pr-info': lambda: cmd_pr_info(a.numbers, a.json, a.fix_map),
     'pr-map': lambda: cmd_pr_map(a.refresh, a.limit, a.batch_file),
     'batch': lambda: cmd_batch(a.size, a.start_offset),
     'audit': lambda: cmd_audit(a.batch_file),
     'promote': lambda: cmd_promote(a.decisions),
     'fix': lambda: cmd_fix(a.entries),
     'report': lambda: cmd_report(a.decisions, a.batch, a.date, a.out),
     'publish': lambda: cmd_publish(a.branch, a.push, a.batch)}[a.cmd]()


if __name__ == '__main__':
    main()
