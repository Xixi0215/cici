#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""storyboard-to-video-prompts ── 把「落地分镜脚本」装配成可直接投喂的视频生成提示词。

输入：
  1) 分镜脚本 markdown：`**E01-01 · 场景 · 14.8s · 5 切**` + 九列表格
     （镜号｜时长｜景别｜运镜｜画面内容｜人物表演｜声音分层｜生图提示词｜运动提示词）
  2) 创作层 JSON（人工撰写，唯一的创作输入）：
     {"E01-01": {"themes": ["主题A","主题B"], "emotions": ["物理锚点（情感：……）", ...]}, ...}

输出：每集一个 md（自包含，可整段复制），并打印每集的切片账本。

用法：
  python sb_to_video_prompts.py --sb <分镜.md> --editorial <创作层.json> --outdir <输出目录> \
      [--density B] [--durations 59.1,43.2,...]
装配完必须跑：
  python ../video-prompt-generator/scripts/lint_video_prompt.py <输出.md> --duration <该集秒数> --density B
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ============================================================ 可替换资产表
# 景别 → 机位技术槽（同时承担量化密度：米／mm／度／厘米 四个量纲）
LENS = {
    "大远景": "机位距主体 12 米／焦段 18mm／俯角 6 度／景深 4 米",
    "远景":   "机位距主体 8 米／焦段 24mm／俯角 6 度／景深 3 米",
    "全景":   "机位距主体 5 米／焦段 35mm／俯角 5 度／景深 1.6 米",
    "中景":   "机位距主体 2.5 米／焦段 50mm／俯角 4 度／景深 60 厘米",
    "近景":   "机位距主体 1.4 米／焦段 70mm／俯角 3 度／景深 25 厘米",
    "特写":   "机位距主体 0.8 米／焦段 85mm／俯角 2 度／景深 12 厘米",
    "大特写": "机位距主体 0.4 米／焦段 100mm／俯角 0 度／景深 5 厘米",
}
LENS_DEFAULT = LENS["中景"]

# 场景关键词 → (环境声, 动作音效, 光影, 色调)   ← 按题材改写，务必带 dB / Hz / 度 / 厘米 / %
SCENES = [
    (("浴室", "水汽"), ("浴室水声，底噪 46dB", "水柱撞击瓷砖 2.4kHz／52dB",
                    "单窗侧顶光、入射角约 60 度，水汽让光柱可见、边缘衰减过渡约 20 厘米，光比约 2:1，湿瓷砖反射率 18%",
                    "冷青白调，高光压到 88IRE，暗部偏青 6%")),
    (("阳台", "屋顶"), ("远处城市低频 41dB、鸟鸣 3.2kHz", "瓷杯与木台轻碰 1.8kHz／38dB",
                    "晨光低角度 12 度斜入、穿过铁艺栏杆投出条状影、影宽约 8 厘米，光比约 3:1，木质反射率 12%",
                    "暖白调，肤色保留 15% 暖偏移，高光不溢出")),
    (("床", "枕", "棉布"), ("室内安静，底噪 31dB", "床单摩擦 1.2kHz／40dB",
                        "窗纱漫射天光、入射角约 45 度，床单褶皱的明暗过渡带约 10 厘米，光比约 2.5:1，棉布反射率 12%",
                        "中性白，饱和度峰值 40%，暗部偏青 5%")),
    (("卧", "晨"), ("室内极静，底噪 28dB、远处鸟鸣", "手机震动 180Hz／44dB",
                  "窗纱逆光、入射角约 30 度，光柱内可见尘粒、边缘衰减约 30 厘米，光比约 4:1，墙面反射率 20%",
                  "暖白偏青，高光压到 85IRE")),
]
SCENE_DEFAULT = ("室内安静，底噪 33dB", "布料摩擦 1.6kHz／39dB",
                 "侧窗漫射天光、入射角约 50 度，光比约 3:1，暗部反射率 8%",
                 "低饱和电影调，暗部偏青")

# 人物七维（≥5 维；lint 用 "[年龄" 这类中括号前缀识别）——下面两条是可直接替换的示例
CHARS = {
    "她": ("[年龄／种族] 约 28 岁东亚女性，素颜。\n"
           "[肤色／皮肤质感] 冷白偏暖，锁骨与颈侧透一点血色，保留真实的微细毛孔与肌肤纹理，皮肤反射率约 9%。\n"
           "[面部细节特征] 下颌线圆润，眉毛自然未修，唇色偏浅、没有明显妆感。\n"
           "[眼神／灵魂] 眼睛先放松、再聚焦，安静里有钝感，不讨好镜头。\n"
           "[发型／发色] 深棕黑及肩发，未做造型，发尾自然外翘，额前有几根碎发。\n"
           "[服装／服装质感] 白色棉质睡裙与 oversize 白衬衫，布料哑光、含棉量高，褶皱自然不熨烫。\n"
           "[体型／情绪／气质] 身量中等，肩颈松，气质安静、不甜。"),
}

MINOR = "[次要人物] 按集内实际出场角色补写（管家／丫鬟／门房／内侍／宾客／百姓等），只锁服装与身份，不逐个写脸。"

# 物理逻辑：全片通用的力学纪律（正面写法）
PHYS = ("发力有支点、受力有反作用，接触有明确落点、位移带惯性；物体按真实重量、摩擦与材质响应。"
        "布料、发丝与水面比身体晚半拍跟随，位移越快滞后越明显，约滞后 0.05—0.15 秒。"
        "人物与道具共用同一个重力方向，落地有缓冲、受击有回弹。"
        "烟雾、灰尘与火星自接触点生成，沿受力方向扩散、由密到疏消散。")

NEG = ("无卡通渲染，无动漫风格，无水彩与油画笔触感，无塑料质感材质，无光滑橡胶质感皮肤，"
       "无重复贴图纹理，无镜头光晕滤镜效果，无人工合成辉光，无暗角人为添加，无颗粒感过度，"
       "无Rec.2020色域溢出，无HDR映射导致的局部过曝死白，无黑色阶损失导致的死黑，"
       "无过度虚化导致的微缩模型感，无运动模糊糊掉五官，无面部比例崩坏与换脸，"
       "无多余手指与多肢，无瓶身比例失真与标签变形，无喷雾呈点状水柱，无水花贴图感，"
       "无影棚平光感，无光源方向混乱，无跳色与色调跳变，无高光溢出死白，无暗部抬灰发雾")

# 光影：全片统一的光位纪律（正面写法）
LIGHT = ("主光为单一主导光源，方向贯穿全片不换边；光比按场景定档，暗部保留细节、反射率压到 6% 以下。"
         "体积光只在有介质（尘、雾、水汽）处出现，光柱边缘有真实衰减、由亮到暗过渡约 30 厘米。"
         "影子方向与光位严格对应，影长随高度变化、边缘硬度随光源面积变化。"
         "光影随时间推移的方向与色温变化连续，不跳变。")

# 色调：全片统一的色彩纪律（正面写法）
GRADE = ("整体低饱和电影调，饱和度峰值不超过 60%；高光滚降不溢出、暗部保留 5% 以上细节、不做纯黑。"
         "肤色是唯一的暖色锚点，单独保护、偏移不超过 15%；除肤色外统一降饱和。"
         "同一集内色调不跳变，只在场景切换处允许一次受控偏移。")

STYLE = ("香水与生活方式广告质感，9:16 竖构图，全自然光为主，浅景深，"
         "布料与皮肤质感真实，8K 细节分辨率")

SUBJ = ["少女", "男子", "妇人", "老妇", "管事", "管家", "丫鬟", "侍女", "仆妇", "内侍", "狱卒",
        "官兵", "宾客", "百姓", "门房", "众人", "下人", "一只手", "两只手", "手", "他", "她"]
BG = ["身后", "背景", "虚化", "天光", "日光", "烛光", "画面边缘", "远处", "前景", "光柱", "光斑"]

# 分镜表里「人物表演」写得过水时的识别词：命中则退回用「画面内容」里的动作短语
PERF_THIN = ("情绪随台词推进", "维持原有姿态", "神情不变", "无特别", "同前", "同上", "不变")

EP_RE = re.compile(r"^###\s*EP(\d+)《(.+?)》\s*·\s*(\d+)\s*镜\s*/\s*([\d.]+)s")
SEG_RE = re.compile(r"^\*\*E(\d+)-(\d+)\s*·\s*(.+?)\s*·\s*([\d.]+)s\s*·\s*(\d+)\s*切\*\*")


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("**", "").strip())


def core_of(img):
    s = clean(img).replace("，16:9", "").strip("；; ")
    return s.split("；", 1)[1] if "；" in s else s


def field(sound, key):
    m = re.search(key + r"[：:]\s*([^／|]*)", sound)
    return clean(m.group(1)) if m else ""


def parse_sb(path):
    eps, cur_ep, cur_seg = [], None, None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        m = EP_RE.match(raw)
        if m:
            cur_ep = {"ep": int(m.group(1)), "title": m.group(2), "shots": int(m.group(3)),
                      "dur": float(m.group(4)), "segs": []}
            eps.append(cur_ep)
            cur_seg = None
            continue
        m = SEG_RE.match(raw)
        if m and cur_ep:
            cur_seg = {"ep": int(m.group(1)), "idx": int(m.group(2)), "scene": m.group(3),
                       "dur": float(m.group(4)), "cuts": int(m.group(5)), "shots": []}
            cur_ep["segs"].append(cur_seg)
            continue
        if cur_seg and raw.startswith("|"):
            c = [clean(x) for x in raw.strip().strip("|").split("|")]
            if len(c) < 9 or not re.fullmatch(r"\d+", c[0] or ""):
                continue
            cur_seg["shots"].append({
                "no": int(c[0]), "dur": float(re.sub(r"[^\d.]", "", c[1]) or 0),
                "size": c[2], "move": c[3], "perf": c[5], "sound": c[6],
                "img": c[7], "motion": c[8], "core": core_of(c[7]),
                "line": field(c[6], "台词"),
            })
    return eps


def clip(s, n):
    s = s.strip("，。；; ")
    return s if len(s) <= n else s[:n] + "…"


def clip_soft(s, n):
    s = s.strip("，。；; ")
    if len(s) <= n:
        return s
    head = s[:n]
    for sep in ("；", "，", "、"):
        i = head.rfind(sep)
        if i > n * 0.5:
            return head[:i]
    return head + "…"


def clean_perf(p):
    parts = [x.strip() for x in p.split("；") if x.strip() and "情绪" not in x]
    parts = [re.sub(r"^(姿态|眼神|微表情|手部|群体|面部|身体|表演)[：:]", "", x) for x in parts]
    return "，".join(parts)


def action_phrase(core):
    s = core
    if "：" in s.split("，")[0]:
        s = s.split("：", 1)[1]
    s = s.split("；")[0]
    parts = [p.strip() for p in s.split("，") if p.strip()]
    start = next((i for i, p in enumerate(parts) if any(w in p for w in SUBJ)), None)
    if start is None:
        return clip(parts[0] if parts else s, 34)
    kept, n = [], 0
    for p in parts[start:]:
        if n >= 1 and any(w in p for w in BG):
            break
        kept.append(p)
        n += 1
        if n >= 3:
            break
    return clip("，".join(kept), 46)


def scene_tech(scene):
    for keys, val in SCENES:
        if any(k in scene for k in keys):
            return val
    return SCENE_DEFAULT


def pack(ep):
    """相邻同场景段合成「场景连续段」，段内贪心装箱 ≤10 秒，再消掉单镜切片。"""
    segs = ep["segs"]
    runs, i = [], 0
    while i < len(segs):
        run, j = [segs[i]], i + 1
        while j < len(segs) and segs[j]["scene"] == segs[i]["scene"]:
            run.append(segs[j])
            j += 1
        runs.append(run)
        i = j
    slices = []
    for run in runs:
        pairs = [(s, sh) for s in run for sh in s["shots"]]
        cur = []
        for s, sh in pairs:
            if cur and sum(x[1]["dur"] for x in cur) + sh["dur"] > 10.0 + 1e-6:
                slices.append(cur)
                cur = []
            cur.append((s, sh))
        if cur:
            slices.append(cur)
    for i in range(1, len(slices)):
        while len(slices[i]) < 2 and len(slices[i - 1]) > 2:
            moved = slices[i - 1][-1]
            if sum(x[1]["dur"] for x in slices[i]) + moved[1]["dur"] > 10.0 + 1e-6:
                break
            slices[i].insert(0, slices[i - 1].pop())
    return slices


def fmt_shot(idx, t0, loc0, seg, sh):
    size = sh["size"] if sh["size"] in LENS else "中景"
    tech = LENS.get(sh["size"], LENS_DEFAULT)
    core = sh["core"]
    for lab in (size + "：", size + ":", sh["size"] + "："):
        if core.startswith(lab):
            core = core[len(lab):]
            break
    core = core.replace("，切入，", "，").replace("切入，", "").replace("，，", "，")
    line = (f"镜头 {idx}（{round(t0, 1):g}-{round(t0 + sh['dur'], 1):g} 秒／片内 "
            f"{round(loc0, 1):g}-{round(loc0 + sh['dur'], 1):g} 秒 · 段{seg['idx']:02d} 镜{sh['no']:02d}）："
            f"{size}·{sh['move']}｜{tech}。画面：{core}。")
    if sh["motion"].strip("。；; "):
        line += f"运动：{sh['motion'].strip('。；; ')}。"
    if sh["line"] and sh["line"] != "无":
        line += f"台词：{sh['line']}。"
    return line


def build_episode(ep, editorial):
    scenes_seen, names = [], set()
    for seg in ep["segs"]:
        if seg["scene"] not in scenes_seen:
            scenes_seen.append(seg["scene"])
        blob = " ".join(sh["core"] + sh["perf"] + sh["line"] for sh in seg["shots"])
        names |= {n for n in CHARS if n in blob}
    slices = pack(ep)
    o = [f"# EP{ep['ep']:02d}《{ep['title']}》· 中文视频生成提示词", "",
         "> 生成方式：Seedance 2.5（5s / 10s 档），成片秒数生成后裁切；提示词全部中文，可整段复制投喂。",
         "> 结构：一集 = 若干「生成切片」（一次生成，5—10 秒），每切片内含 2—4 个「剪辑镜头」（1.5—3.5 秒）。",
         "> 投喂：每生成一次 = 「模块二 全局设定（含人物造型）」＋「模块三 中该阶段的整段文本」，两段拼在一起粘贴。",
         "", "## 总述名称", "",
         f"EP{ep['ep']:02d}《{ep['title']}》｜{ep['dur']} 秒｜{ep['shots']} 镜 · {len(slices)} 个生成单元", "",
         "## 模块一｜多模态参考层（可选，未挂参考图则整段删除）", "",
         "基于上传的参考图，@图1 逐字锁定香瓶的 [瓶身比例／标签排版／喷头结构] 与标签文字排版，"
         "@图2 逐字锁定场景的 [光位／色调] 与道具位置。", "",
         "## 模块二｜全局设定", "",
         f"**基础环境与质感**：本集场景：{'、'.join(scenes_seen)}。强调极致的真实物理质感。", "",
         f"**视觉风格**：真人实景质感，{STYLE}。", "",
         f"**光影**：{LIGHT}", "",
         f"**色调**：{GRADE}", "",
         "**镜头语言**：9:16 竖构图；机位以固定、极慢横移与缓推为主，切片内 2—4 个剪辑镜头、单镜 1.5—3.5 秒；"
         "轻微手持呼吸感，不做快速剪辑；画面内只保留一位主角，不出现群众与多余人物。", "",
         "**人物造型**（锁定，全文逐字复用）：", ""]
    for n, body in CHARS.items():
        if n in names:
            o += [f"〔{n}〕{body}", ""]
    if not (names & set(CHARS)):
        print("  ！本集未匹配到 CHARS 里的角色名：已按 CHARS 全量输出，"
              "请把 CHARS 的键改成剧本中的角色名（否则人物一致性无从锁定）")
        for n, body in CHARS.items():
            o += [f"〔{n}〕{body}", ""]
    if names - set(CHARS):
        o += [MINOR, ""]
    o += [f"**物理逻辑**：{PHYS}", "",
          "**表演核心**：呼吸先于动作、指尖先于表情；情绪只走眼神、呼吸与指节；"
          "手部特写只出现一只手或两只手；不出现表演性的笑与看镜头。", "",
          "## 模块三｜时间戳剧本分镜", ""]

    last_scene = None
    for si, sl in enumerate(slices, 1):
        total = round(sum(x[1]["dur"] for x in sl), 1)
        g0 = round(sum(sum(x[1]["dur"] for x in s) for s in slices[:si - 1]), 1)
        g1 = round(g0 + total, 1)
        seg = sl[0][0]
        key = f"E{seg['ep']:02d}-{seg['idx']:02d}"
        k = sum(1 for x in slices[:si - 1] if x[0][0] is seg)
        themes = editorial.get(key, {}).get("themes", [""])
        theme = themes[min(k, len(themes) - 1)]
        scene = seg["scene"]
        if last_scene is not None and scene != last_scene:
            a, b = slices[si - 2][-1][1], sl[0][1]
            o += [f"转场：在换场处使用“场景硬切”转场。镜头 A 收在「{clip(action_phrase(a['core']), 20)}」，"
                  f"随后自然过渡到镜头 B：「{clip(action_phrase(b['core']), 20)}」。"
                  f"切换处留足呼吸时间，让画面 A 完整走完再入画面 B，两镜的光线走向与动作朝向连续。"
                  f"要求必须自然切换场景。", ""]
        band = "5 秒档" if total <= 5.0 else "10 秒档"
        o += [f"**第 {si} 阶段：{g0:g}-{g1:g} 秒【段{seg['idx']:02d}·{scene}·{band}"
              f"（生成后裁至 {total:g} 秒）｜{theme}】**", ""]

        acts, emos, anchors, t, loc, pos = [], [], [], g0, 0.0, {}
        for s, sh in sl:
            pos.setdefault(f"E{s['ep']:02d}-{s['idx']:02d}", [sh["no"], len(s["shots"]), s["shots"][0]["no"]])
            o += [fmt_shot(len(anchors) + 1, t, loc, s, sh), ""]
            anchors.append(1)
            perf = sh["perf"]
            acts.append(f"镜{len(anchors):02d} " + (action_phrase(sh["core"])
                        if (any(k in perf for k in PERF_THIN) or len(perf) < 8)
                        else clip_soft(clean_perf(perf), 52)))
            t += sh["dur"]
            loc += sh["dur"]
        for kid, (start_no, n_shots, first_no) in pos.items():
            e = (editorial.get(kid, {}).get("emotions") or [""])
            if e and e[0]:
                rel = (start_no - first_no) / max(n_shots - 1, 1)
                pick = e[max(0, min(len(e) - 1, int(round(rel * (len(e) - 1)))))]
                if pick not in emos:
                    emos.append(pick)
        o += [f"动作/表情：{'；'.join(acts)}。", "",
              "机位纪律：单镜内只走一条运镜；≥3 人同框时只让主体进入动作，其余人物停在原位、保留微弱的呼吸起伏。", "",
              "情感解析：" + "；".join(emos[:3]) + "。", ""]
        amb, sfx_s, light, grade = scene_tech(scene)
        gold = []
        for _s, _sh in sl:
            for _c in re.split(r"[；;]", _sh.get("sound", "")):
                _c = _c.strip()
                if _c.startswith("音效"):
                    _c = re.sub(r"^音效[：:]", "", _c).strip()
                    if _c and _c not in gold:
                        gold.append(_c)
        sfx = "；".join(gold) if gold else sfx_s
        o += [f"声音：{amb}；{sfx}；全片无对白、无人声，环境声与动作音之间的声压差约 6dB。不要背景音乐。", "",
              f"光影：{light}；主光斜入→主体边缘形成约 1 厘米宽的过渡阴影；"
              f"色温 4800K，光斑随人物移动的横移速度约 0.2 米/秒。", "",
              f"色调：{grade}；人体肤色单独保护，与背景色温差不超过 300K。", "",
              "技术锚点：手部特写时指节握力约 1.5 公斤；棉布表面反射率约 12%、哑光；"
              "玻璃瓶身折射率约 1.5，边缘高光宽约 0.3mm。", "",
              "力学链：支点发力→关节传导→末端接触→反作用回传躯干，四段在同一镜内可见；"
              "接触点即粒子生成点。", ""]
        last_scene = scene

    o += ["## 尾部画面纪律", "",
          "不要字幕，不要手写字卡，不要水印，不要画面内出现任何文字（中文独白与手写主张卡一律后期叠加）；"
          "不要背景音乐。", "",
          "## 全局负面块", "", NEG + "。", ""]
    return "\n".join(o), len(slices)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sb", required=True)
    ap.add_argument("--editorial", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--template", default="{ep:02d}_{title}_视频生成提示词.md")
    a = ap.parse_args()
    editorial = json.loads(Path(a.editorial).read_text(encoding="utf-8"))
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    for ep in parse_sb(a.sb):
        md, n = build_episode(ep, editorial)
        p = out / a.template.format(ep=ep["ep"], title=ep["title"])
        p.write_text(md, encoding="utf-8")
        print(f"EP{ep['ep']:02d}《{ep['title']}》{ep['dur']}s / {ep['shots']}镜 → {n} 个生成单元" 
              f"  ｜lint: --duration {ep['dur']} --density B")


if __name__ == "__main__":
    main()
