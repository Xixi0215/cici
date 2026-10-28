import sys
from pathlib import Path

bp = Path(r"D:/cici的作品集网站/分镜脚本/build_prompts.py")
s = bp.read_text(encoding="utf-8")

def rep(old, new, must=True):
    global s
    if old not in s:
        if must:
            print("!! NOT FOUND:", old[:70].replace("\n", " "))
            sys.exit(1)
        return
    s = s.replace(old, new, 1)

# 1) 视觉风格去掉重复的「真人实景」
rep('STYLE = ("真人实景，香水与生活方式广告质感，9:16 竖构图，全自然光为主，浅景深，"\n         "布料与皮肤质感真实，8K 细节分辨率")',
    'STYLE = ("香水与生活方式广告质感，9:16 竖构图，全自然光为主，浅景深，"\n         "布料与皮肤质感真实，8K 细节分辨率")')

# 2) pos 记录段内首镜号
rep('pos.setdefault(f"E{s[\'ep\']:02d}-{s[\'idx\']:02d}", [sh["no"], len(s["shots"])])',
    'pos.setdefault(f"E{s[\'ep\']:02d}-{s[\'idx\']:02d}", [sh["no"], len(s["shots"]), s["shots"][0]["no"]])')

rep('for kid, (start_no, n_shots) in pos.items():',
    'for kid, (start_no, n_shots, first_no) in pos.items():')

rep('pick = e[min(len(e) - 1, int(round((start_no - 1) / max(n_shots, 1) * len(e))))]',
    'rel = (start_no - first_no) / max(n_shots - 1, 1)\n'
    '                pick = e[max(0, min(len(e) - 1, int(round(rel * (len(e) - 1)))))]')

# 3) 音效用本切片内各镜的音效，而不是整个场景一套
rep('        amb, sfx, light, grade = scene_tech(scene)',
    '        amb, sfx_s, light, grade = scene_tech(scene)\n'
    '        gold = []\n'
    '        for _s, _sh in sl:\n'
    '            for _c in re.split(r"[；;]", _sh.get("sound", "")):\n'
    '                _c = _c.strip()\n'
    '                if _c.startswith("音效"):\n'
    '                    _c = re.sub(r"^音效[：:]", "", _c).strip()\n'
    '                    if _c and _c not in gold:\n'
    '                        gold.append(_c)\n'
    '        sfx = "；".join(gold) if gold else sfx_s')

bp.write_text(s, encoding="utf-8")
print("patched build_prompts.py")

# 4) 分镜表：运镜列去掉与 LENS 重复的机位距离
sb = Path(r"D:/cici的作品集网站/分镜脚本/分镜-REPLICA慵懒周末-60s_九列版.md")
t = sb.read_text(encoding="utf-8")
n = 0
for frag in ["，机位距主体约 0.4 米 |", "，机位距主体约 2.5 米 |", "，机位距主体约 1.4 米 |", "，机位距主体约 2 米 |"]:
    n += t.count(frag)
    t = t.replace(frag, " |")
sb.write_text(t, encoding="utf-8")
print("cleaned 运镜 dup:", n)
