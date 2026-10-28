# -*- coding: utf-8 -*-
"""生成 9:16 手写主张卡（透明底），每张一个 1080x1920 画布。"""
from pathlib import Path

OUT = Path(r"D:/cici的作品集网站/叠加字卡")
OUT.mkdir(exist_ok=True)

CARDS = [
    ("01", "NOTHING TO RUSH FOR", "今天不赶时间", None),
    ("02", "CLEAN IS A FEELING", "干净是洗给自己看的", None),
    ("03", "SOFT ISN'T WEAK", "柔软不是软弱", None),
    ("04", "STAY A LITTLE LONGER", "再赖一会儿", None),
    ("05", "LAZY SUNDAY MORNING", "慵懒周末", "MAISON MARGIELA · REPLICA"),
]

def card_html(idx, en, cn, brand, color):
    brand_html = ""
    if brand:
        brand_html = (
            '<div class="rule"></div>'
            f'<div class="brand">{brand}</div>'
        )
    underline = (
        '<svg class="ul" width="1080" height="46" viewBox="0 0 1080 46">'
        '<path d="M 300 24 C 380 16, 470 30, 560 22 S 720 14, 800 26" '
        'fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" opacity="0.7"/>'
        '</svg>'
    )
    return f'''<section class="card" style="color:{color}">
  <div class="inner">
    <div class="en">{en}</div>
    {underline}
    <div class="cn">{cn}</div>
    {brand_html}
  </div>
</section>'''

def page(cards, color, fname):
    body = "\n".join(card_html(*c, color) for c in cards)
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<style>
  @font-face {{ font-family: "KaiLocal"; src: local("KaiTi"), local("楷体"); }}
  html,body{{margin:0;padding:0;background:transparent}}
  .card{{width:1080px;height:1920px;position:relative;background:transparent}}
  .inner{{position:absolute;left:0;right:0;top:790px;text-align:center}}
  .en{{font-family:"Ink Free","Segoe Print","Segoe Script",cursive;
       font-size:66px;letter-spacing:.14em;line-height:1.1;white-space:nowrap;
       text-transform:uppercase;opacity:.94}}
  .ul{{display:block;margin:-2px auto 0;color:inherit}}
  .cn{{font-family:"KaiLocal","KaiTi","楷体","STKaiti",serif;
       font-size:72px;letter-spacing:.1em;margin-top:18px;opacity:.96}}
  .rule{{width:260px;height:2px;background:currentColor;opacity:.45;margin:56px auto 0}}
  .brand{{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif;
          font-size:24px;letter-spacing:.34em;margin-top:22px;opacity:.8}}
</style></head><body>
{body}
</body></html>'''
    p = OUT / fname
    p.write_text(html, encoding="utf-8")
    return p

print(page(CARDS, "#1b1a17", "_ink.html"))
print(page(CARDS, "#f7f3ea", "_ivory.html"))
