#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""对 14 个皮肤页做排版体检。

判据（都可执行，不靠眼睛）：
  1. 水平溢出 —— 任一元素 scrollWidth > clientWidth + 1
  2. 行间交叠 —— 两个文本 rect 垂直区间相交 > 2px 且水平区间相交 > 2px
  3. 碎片行   —— .hint 内宽度 < 18px 且只含标点的行（孤字/孤标点）
用法：python tools/probe_layout.py
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS = os.path.join(ROOT, "skins")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE = os.path.join(tempfile.gettempdir(), "edgehl")
PORT = 8137

PROBE = r"""
<script>
window.addEventListener('load', function(){
  function rects(node, out){
    if (node.nodeType === 3) {
      var t = node.textContent;
      if (!t.trim()) return;
      var r = document.createRange(); r.selectNodeContents(node);
      var list = r.getClientRects();
      for (var i = 0; i < list.length; i++) {
        var rc = list[i];
        if (rc.width < 0.5) continue;
        out.push({k:'t', s:t.trim().slice(0,10), t:rc.top, b:rc.bottom, l:rc.left, r:rc.right});
      }
    } else if (node.nodeType === 1 && node.tagName !== 'BR' && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
      var rc2 = node.getBoundingClientRect();
      if (node.textContent.trim() && rc2.width > 0.5) {
        out.push({k:'e', s:'<' + node.tagName + '>' + node.textContent.trim().slice(0,10),
                  t:rc2.top, b:rc2.bottom, l:rc2.left, r:rc2.right, tag:node.tagName});
      }
      for (var j = 0; j < node.childNodes.length; j++) rects(node.childNodes[j], out);
    }
  }

  // 1) 水平溢出：只统计会被看见的溢出（overflow:hidden/auto 的元素自己裁剪，不算）
  //    白名单：票根的 .divider 用 ::before/::after 左右各伸 13px 画半圆打孔，是设计意图
  var of = [];
  var all = document.querySelectorAll('*');
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    if (el.tagName === 'HTML' || el.tagName === 'BODY') continue;
    if (String(el.className || '').indexOf('divider') >= 0) continue;
    var ox = getComputedStyle(el).overflowX;
    if (ox === 'hidden' || ox === 'auto' || ox === 'scroll') continue;
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 4) {
      of.push(el.tagName + '.' + (el.className || '') + ' sw=' + el.scrollWidth + ' cw=' + el.clientWidth);
    }
  }

  // 2) + 3) 说明面板逐行
  var hint = document.querySelector('.hint');
  var out = [];
  var frag = 0, hintH = 0, hintW = 0, overlap = 0, lines = [];
  if (hint) {
    hintH = Math.round(hint.getBoundingClientRect().height);
    hintW = Math.round(hint.getBoundingClientRect().width);
    // 只收文本节点的 rect，不掺元素容器（否则父子必然"重叠"）
    var raw = [];
    for (var c = 0; c < hint.childNodes.length; c++) {
      collectText(hint.childNodes[c], raw);
    }
    var byLine = {};
    raw.forEach(function (o) {
      var key = Math.round(o.t);
      if (!byLine[key]) byLine[key] = {t:key, b:0, l:1e9, r:-1e9, txt:''};
      byLine[key].b = Math.max(byLine[key].b, o.b);
      byLine[key].l = Math.min(byLine[key].l, o.l);
      byLine[key].r = Math.max(byLine[key].r, o.r);
      byLine[key].txt += o.s;
    });
    var keys = Object.keys(byLine).map(Number).sort(function(a,b){return a-b;});
    keys.forEach(function (k) {
      var L = byLine[k];
      L.w = Math.round(L.r - L.l);
      lines.push(L);
      if (L.w < 18) frag++;
    });

    // 真交叠：不同行（top 相差 > 2）且水平也相交
    for (var a = 0; a < raw.length; a++) {
      for (var b2 = a + 1; b2 < raw.length; b2++) {
        var A = raw[a], B = raw[b2];
        if (Math.abs(A.t - B.t) <= 2) continue;
        var vo = Math.min(A.b, B.b) - Math.max(A.t, B.t);
        var ho = Math.min(A.r, B.r) - Math.max(A.l, B.l);
        if (vo > 2 && ho > 2) overlap++;
      }
    }
  }

  function collectText(node, out) {
    if (node.nodeType === 3) {
      var t = node.textContent;
      if (!t.trim()) return;
      var r = document.createRange(); r.selectNodeContents(node);
      var list = r.getClientRects();
      for (var i = 0; i < list.length; i++) {
        var rc = list[i];
        if (rc.width < 0.5) continue;
        out.push({s:t.trim().slice(0,10), t:rc.top, b:rc.bottom, l:rc.left, r:rc.right});
      }
    } else if (node.nodeType === 1) {
      for (var j = 0; j < node.childNodes.length; j++) collectText(node.childNodes[j], out);
    }
  }

  document.title = 'PROBE|' + JSON.stringify({
    overflow: of.slice(0, 6), frag: frag, overlap: overlap,
    hintH: hintH, hintW: hintW,
    narrow: lines.filter(function(L){return L.w < 30;}).map(function(L){return L.txt + '=' + L.w;}).slice(0,5),
    h1: (document.querySelector('.devbar h1') || {}).textContent || ''
  });
});
</script>
</body>"""


def fetch(path):
    url = "http://127.0.0.1:%d/%s" % (PORT, urllib.parse.quote(path))
    out = subprocess.run(
        [EDGE, "--headless=new", "--disable-gpu", "--virtual-time-budget=4000",
         "--user-data-dir=" + PROFILE, "--dump-dom", url],
        capture_output=True, timeout=120,
    )
    html = out.stdout.decode("utf-8", "replace")
    m = re.search(r"PROBE\|(\{.*?\})</title>", html, re.S)
    return m.group(1) if m else None


def main():
    import json
    names = sorted(f for f in os.listdir(SKINS) if f.endswith(".html"))
    print("%-16s %-8s %-6s %-6s %-7s %s" % ("skin", "hintH", "frag", "ovlp", "hintW", "overflow"))
    print("-" * 96)
    bad = 0
    for n in names:
        src = os.path.join(SKINS, n)
        html = open(src, encoding="utf-8").read()
        if "</body>" not in html:
            print("%-16s 无 </body>，跳过" % n)
            continue
        tmp = os.path.join(ROOT, "_preview", "probe_" + n)
        open(tmp, "w", encoding="utf-8").write(html.replace("</body>", PROBE, 1))
        try:
            raw = fetch("_preview/probe_" + n)
        except subprocess.TimeoutExpired:
            print("%-16s TIMEOUT" % n)
            bad += 1
            continue
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        if not raw:
            print("%-16s PROBE 未返回" % n)
            bad += 1
            continue
        d = json.loads(raw)
        flag = ""
        if d["overlap"] > 0:
            flag += " OVERLAP"
            bad += 1
        if d["frag"] > 0:
            flag += " FRAG"
            bad += 1
        if d["overflow"]:
            flag += " OVERFLOW"
            bad += 1
        print("%-16s %-8d %-6d %-6d %-7d %s%s" % (
            n, d["hintH"], d["frag"], d["overlap"], d["hintW"],
            (d["overflow"][0][:38] if d["overflow"] else "-"), flag))
    print("-" * 96)
    print("有问题的文件数：%d / %d" % (bad, len(names)))


if __name__ == "__main__":
    main()
