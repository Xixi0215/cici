import re, json, html
from pathlib import Path

MD = Path(r"D:/cici的作品集网站/视频提示词/01_慵懒周末_视频生成提示词.md")
OUT = Path(r"D:/cici的作品集网站/视频提示词/投喂卡-慵懒周末-60s.html")
IDX = Path(r"D:/cici的作品集网站/视频提示词/00_索引与使用说明.md")

raw = MD.read_text(encoding="utf-8")
lines = raw.splitlines()

def find(prefix, start=0):
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    return -1

i_m2 = find("## 模块二")
i_m3 = find("## 模块三")
i_tail = find("## 尾部画面纪律")
i_neg = find("## 全局负面块")

global_block = "\n".join(lines[i_m2 + 2:i_m3]).strip()
tail_block = "\n".join(lines[i_tail + 2:i_neg]).strip()
neg_block = "\n".join(lines[i_neg + 2:]).strip()
def clean(x):
    return x.replace("**", "")
global_block, tail_block, neg_block = clean(global_block), clean(tail_block), clean(neg_block)

heads = [(i, l) for i, l in enumerate(lines) if l.startswith("**第 ")]
slices = []
for k, (i, l) in enumerate(heads):
    end = heads[k + 1][0] if k + 1 < len(heads) else i_tail
    title = l.strip().strip("*")
    body = "\n".join(lines[i + 1:end]).strip()
    pre = []
    j = i - 1
    while j > i_m3 and lines[j].strip():
        pre.insert(0, lines[j].strip())
        j -= 1
    trans = " ".join(x for x in pre if x.startswith("转场"))
    if k > 0:
        slices[k - 1]["body"] = "\n".join(
            ln for ln in slices[k - 1]["body"].splitlines() if not ln.startswith("转场")).strip()
    m = re.match(r"第\s*(\d+)\s*阶段：([\d.]+)-([\d.]+)\s*秒【段(\d+)·(.+?)·(\d+)\s*秒档（生成后裁至\s*([\d.]+)\s*秒）｜(.+?)】", title)
    n_stage, t0, t1, seg, scene, band, cut, theme = m.groups()
    shots = len(re.findall(r"镜头\s*\d+（", body))
    slices.append({"stage": int(n_stage), "t0": float(t0), "t1": float(t1), "seg": seg,
                   "scene": scene, "band": int(band), "cut": float(cut),
                   "theme": theme, "body": clean(body), "trans": clean(trans), "shots": shots})

def mmss(t):
    m_ = int(t) // 60
    s_ = t - m_ * 60
    return f"{m_:02d}:{s_:04.1f}"

cards_html, payloads = [], {}
for s in slices:
    payload = global_block + "\n\n" + (s["trans"] + "\n\n" if s["trans"] else "") + s["body"]
    payloads[str(s["stage"])] = payload
    trans_html = ('<p class="trans">⚠ ' + html.escape(s["trans"]) + '</p>') if s["trans"] else ""
    cards_html.append(
        '<section class="card">'
        '<div class="chead"><div class="left">'
        f'<span class="stg">切片 {s["stage"]}</span>'
        f'<span class="tc">{mmss(s["t0"])} – {mmss(s["t1"])}</span>'
        f'<span class="sm">{s["t1"]-s["t0"]:g} 秒 · {s["shots"]} 镜 · {s["band"]} 秒档 → 裁 {s["cut"]:g} 秒</span>'
        '</div>'
        f'<button class="cp" data-k="{s["stage"]}">复制（全局＋本段）</button></div>'
        f'<h3>{html.escape(s["theme"])}</h3>'
        f'<p class="meta2">段{s["seg"]} · {html.escape(s["scene"])}</p>'
        f'{trans_html}'
        f'<pre>{html.escape(s["body"])}</pre>'
        '</section>')
cards_html = "\n".join(cards_html)

rows = "".join(
    f"<tr><td class='t'>{s['stage']}</td><td class='t'>{s['t0']:g}–{s['t1']:g}s</td><td>段{s['seg']}</td>"
    f"<td>{html.escape(s['scene'])}</td><td>{s['shots']}</td><td>{s['band']}s → {s['cut']:g}s</td>"
    f"<td>{html.escape(s['theme'])}</td></tr>" for s in slices)

payloads["global"] = global_block
payloads["tail"] = tail_block + "\n\n" + neg_block
js_payloads = json.dumps(payloads, ensure_ascii=False)

TPL = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>投喂卡 · 慵懒周末 60″（8 切片）</title>
<style>
  :root{--paper:#f7f5f1;--card:#fffdf9;--ink:#1d1b19;--ink2:#4a4642;--ink3:#8a847c;
        --line:#e2ddd3;--green:#2d5b4d;--green-l:#e7ede7;--clay:#a9622f;--clay-l:#f5e9dd}
  *{box-sizing:border-box}
  body{margin:0;background:var(--paper);color:var(--ink);
    font-family:"PingFang SC","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;font-size:15px;line-height:1.8}
  .wrap{max-width:980px;margin:0 auto;padding:52px 24px 90px}
  .eyebrow{font-size:11px;letter-spacing:.32em;color:var(--green);font-weight:600;margin-bottom:12px}
  h1{font-family:"Songti SC","Noto Serif SC",serif;font-size:32px;margin:0 0 8px;line-height:1.35}
  h1 small{display:block;font-size:16px;color:var(--ink2);font-weight:400;margin-top:8px}
  .meta{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0 0}
  .chip{font-size:12px;padding:5px 11px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink2)}
  .chip b{color:var(--ink)}
  .how{margin:28px 0 0;background:var(--green-l);border-left:3px solid var(--green);padding:18px 22px;border-radius:2px;font-size:13.5px;color:var(--ink2)}
  .how ol{margin:6px 0 0;padding-left:20px}
  .how li{margin-bottom:6px}
  .how b{color:var(--green)}
  .gcard{margin:30px 0 0;border:1px solid var(--green);border-radius:3px;background:#fff;overflow:hidden}
  .gcard .chead{background:var(--green-l);border-bottom:1px solid var(--line)}
  .card{margin:22px 0 0;border:1px solid var(--line);border-radius:3px;background:var(--card);overflow:hidden}
  .chead{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 16px;background:#f2efe8;border-bottom:1px solid var(--line)}
  .left{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}
  .stg{font-family:Georgia,serif;font-size:11px;letter-spacing:.16em;color:var(--green);font-weight:700}
  .tc{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:var(--clay)}
  .sm{font-size:11.5px;color:var(--ink3)}
  .cp{border:1px solid var(--green);background:#fff;color:var(--green);font-size:12px;padding:5px 12px;border-radius:999px;cursor:pointer;white-space:nowrap;font-family:inherit}
  .cp:hover{background:var(--green);color:#fff}
  .cp.done{background:var(--green);color:#fff;border-color:var(--green)}
  .card h3{margin:14px 16px 2px;font-family:"Songti SC","Noto Serif SC",serif;font-size:16.5px}
  .meta2{margin:0 16px 10px;font-size:11.5px;color:var(--ink3);letter-spacing:.04em}
  .trans{margin:0 16px 10px;font-size:12px;color:var(--clay);background:var(--clay-l);padding:8px 10px;border-radius:2px;line-height:1.7}
  pre{margin:0;padding:14px 16px 18px;white-space:pre-wrap;word-break:break-word;
      font-family:ui-monospace,Menlo,Consolas,"PingFang SC",monospace;font-size:12.4px;line-height:1.85;color:var(--ink2);
      border-top:1px dashed var(--line)}
  .gcard pre{border-top:none}
  .tail{margin:26px 0 0}
  h2{font-family:"Songti SC","Noto Serif SC",serif;font-size:20px;margin:52px 0 6px}
  h2 .num{font-family:Georgia,serif;color:var(--green);font-size:12px;letter-spacing:.16em;display:block;margin-bottom:6px}
  table{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}
  th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
  th{font-size:11.5px;color:var(--ink3);letter-spacing:.06em;border-bottom:1px solid var(--ink3)}
  td.t{font-family:ui-monospace,monospace;font-size:12px;color:var(--clay);white-space:nowrap}
  .ok{display:inline-block;border:1px solid var(--green);color:var(--green);border-radius:999px;padding:2px 10px;font-size:12px}
  footer{margin-top:56px;padding-top:16px;border-top:1px solid var(--line);font-size:12px;color:var(--ink3);line-height:1.9}
  #toast{position:fixed;left:50%;bottom:34px;transform:translate(-50%,20px);opacity:0;transition:.25s;
    background:var(--green);color:#fff;font-size:13px;padding:9px 18px;border-radius:999px;pointer-events:none}
  #toast.on{opacity:1;transform:translate(-50%,0)}
  @media(max-width:700px){.wrap{padding:32px 14px 60px}h1{font-size:25px}pre{font-size:11.6px}.chead{flex-direction:column;align-items:flex-start}}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">视频生成提示词 · 投喂卡</div>
  <h1>LAZY SUNDAY MORNING「慵懒周末」
    <small>EP01｜60 秒 / 22 镜 / 8 个生成单元 · Seedance 2.5 中文提示词</small></h1>
  <div class="meta">
    <span class="chip">总长 <b>60.0 s</b></span>
    <span class="chip">画幅 <b>9:16 竖构图</b></span>
    <span class="chip">切片 <b>8 个</b></span>
    <span class="chip">镜头 <b>22 个</b></span>
    <span class="chip">自检 <b>PASS 21 / WARN 0 / FAIL 0</b></span>
  </div>

  <div class="how">
    <b>怎么用（三段式）</b>
    <ol>
      <li>先复制下方<b>「模块二 全局设定」</b>，粘进对话框——它锁人物、锁光、锁色、锁物理逻辑。</li>
      <li>再点任意切片的<b>「复制（全局＋本段）」</b>，得到「全局设定＋本段分镜」的合并文本，一次性粘进去。</li>
      <li>每次生成一个 5–10 秒切片，按标题上的「裁至 X 秒」剪，八次拼起来就是 60 秒。</li>
    </ol>
  </div>

  <section class="gcard">
    <div class="chead">
      <div class="left"><span class="stg">GLOBAL</span><span class="sm">模块二 全局设定（每次都带上）</span></div>
      <button class="cp" data-k="global">复制全局设定</button>
    </div>
    <pre>__GLOBAL__</pre>
  </section>

  <h2><span class="num">SLICES 01—08</span>八个生成切片</h2>
  __CARDS__

  <h2><span class="num">TAIL</span>尾部画面纪律 ＋ 全局负面块</h2>
  <section class="card tail">
    <div class="chead">
      <div class="left"><span class="stg">TAIL</span><span class="sm">整段附在每次投喂的末尾</span></div>
      <button class="cp" data-k="tail">复制纪律＋负面</button>
    </div>
    <pre>__TAIL__</pre>
  </section>

  <h2><span class="num">LEDGER</span>账本</h2>
  <table>
    <tr><th>切片</th><th>成片时间</th><th>段</th><th>场景</th><th>镜数</th><th>生成档 → 裁切</th><th>主题</th></tr>
    __ROWS__
  </table>
  <p style="margin-top:16px"><span class="ok">lint 通过：PASS 21 ｜ WARN 0 ｜ FAIL 0</span></p>

  <footer>
    配套文件：<code>01_慵懒周末_视频生成提示词.md</code>（纯文本全文，可整段复制）、<code>00_索引与使用说明.md</code>（账本与纪律）。<br>
    生成方式：每个切片按 10 秒或 5 秒档生成，再裁到标注秒数；画面内不要出现任何文字，中文独白与手写主张卡一律后期叠加。<br>
    注意：切片 5 的镜 2、切片 7 的镜 1 是喷雾／水流镜头，必须逆光才能看见雾与水花。
  </footer>
</div>
<div id="toast">已复制</div>
<script>
const P = __PAYLOADS__;
const toast = () => { const t = document.getElementById('toast'); t.classList.add('on'); setTimeout(() => t.classList.remove('on'), 1400); };
function copyText(text, btn) {
  const done = () => { btn.classList.add('done'); const old = btn.textContent; btn.textContent = '已复制 ✓'; toast();
    setTimeout(() => { btn.classList.remove('done'); btn.textContent = old; }, 1400); };
  const fallback = () => {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.top = '-1000px';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { alert('复制失败，请手动选择文本复制'); }
    document.body.removeChild(ta);
  };
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done).catch(fallback); }
  else { fallback(); }
}
document.querySelectorAll('.cp').forEach(b => b.addEventListener('click', () => copyText(P[b.dataset.k] || '', b)));
</script>
</body>
</html>'''

htmlout = (TPL.replace("__GLOBAL__", html.escape(global_block))
              .replace("__CARDS__", cards_html)
              .replace("__TAIL__", html.escape(tail_block + "\n\n" + neg_block))
              .replace("__ROWS__", rows)
              .replace("__PAYLOADS__", js_payloads))
OUT.write_text(htmlout, encoding="utf-8")

idx = ["# 00 索引与使用说明｜EP01《慵懒周末》", "",
       "## 一、账本", "",
       "| 切片 | 成片时间 | 段 | 场景 | 镜数 | 生成档 → 裁切 | 主题 |",
       "|---|---|---|---|---|---|---|"]
for s in slices:
    idx.append(f"| {s['stage']} | {s['t0']:g}–{s['t1']:g}s | 段{s['seg']} | {s['scene']} | {s['shots']} | "
               f"{s['band']}s 档 → {s['cut']:g}s | {s['theme']} |")
idx += ["", f"合计：{len(slices)} 个生成单元 / 22 镜 / 60.0 秒。", "",
        "## 二、投喂方法", "",
        "1. 打开 `投喂卡-慵懒周末-60s.html`，先复制「模块二 全局设定」，粘进对话框作为第一段。",
        "2. 点任意切片的「复制（全局＋本段）」，得到「全局设定 + 本段分镜」的合并文本，直接投喂。",
        "3. 每次生成对应一个 5–10 秒切片，生成后按标注的「裁至 X 秒」剪。八次生成拼起来就是 60 秒成片。", "",
        "## 三、成片纪律", "",
        "- 全片统一 9:16 竖构图、全自然光、低饱和；只有 S4 阳台段落回暖，是全片唯一暖调。",
        "- 中文独白与四张手写主张卡一律后期叠加，生成画面里不要任何文字与字幕。",
        "- 喷雾镜头必须逆光（切片 5 镜 2、切片 7 镜 1），否则雾不可见。",
        "- 音乐与音效后期做；生成时只取画面，不要背景音乐。", "",
        "## 四、自检结果", "",
        "`lint_video_prompt.py --duration 60 --density B`：", "",
        "PASS 21 项 ｜ WARN 0 项 ｜ FAIL 0 项 —— 通过，FAIL 已清零。", "",
        "## 五、上游文件", "",
        "- `../分镜脚本/分镜-REPLICA慵懒周末-60s.md`（人读版分镜）",
        "- `../分镜脚本/分镜-REPLICA慵懒周末-60s_九列版.md`（机器装配版）",
        "- `../分镜脚本/editorial.json`（创作层：主题与情感）"]
IDX.write_text("\n".join(idx), encoding="utf-8")

print("cards:", len(slices), "| html KB:", len(htmlout) // 1024)
