#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给 14 套皮肤出展示图，一条命令跑完，不用手工截图。

为什么要有这个脚本：
  README 里那 14 张图是「产物」，手截的图没法复现，改了一行 CSS 之后就不知道哪张过期。
  这里把「起服务 → 逐页截图 → 裁掉页边空白 → 压体积」全过程写死，
  皮肤改了重跑一次即可，产物与源码永远对得上。

三个阶段：
  1. 截图  本地 http 起在 127.0.0.1:8137，Edge headless 用 1440x1200 视口整页截 PNG
           （走 http 不走 file://，否则内联字体和相对路径在 headless 下行为不一致）
  2. 裁切  以四角均值为背景色，取「与背景差异 > 6」的像素包围盒，四周留 24px
           （页面按 1440 宽设计，底部留着大片背景色，不裁的话图里一半是空的）
  3. 出图  存 PNG。这个内容是界面截图，有大量文字和细线，
           JPEG 在文字边缘会出振铃，而 PNG 调色板化又会让渐变背景出色带，
           所以直接 PNG 无损，单张 100~200 KB，14 张总共 2 MB 左右，可以接受。

用法：python tools/shoot_shots.py [皮肤名...]
      不带参数就全出。只出一张写 python tools/shoot_shots.py A-songti
"""
import http.server
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKINS = os.path.join(ROOT, "skins")
SHOTS = os.path.join(ROOT, "shots")
PORT = 8137
VIEW = (1440, 1200)
PAD = 24
BG_TOL = 6

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.isfile(p):
            return p
    raise SystemExit("找不到 msedge.exe，改 EDGE_CANDIDATES")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, *a):
        pass


def serve():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), Quiet)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


BUDGET_MS = 40000
# 演示是循环动画，直接截会截到「说到一半、有散字浮在半空」的中间帧。
# 所以给临时副本注入一段收尾脚本：在虚拟时间快走完时把动画推到终态、滚动容器归零。
# 定时器本身也被虚拟时间加速，所以 34 s 的 setTimeout 会在预算结束前刚好触发。
SETTLE = r"""<script>
window.addEventListener('load', function(){
  setTimeout(function(){
    try {
      document.getAnimations().forEach(function(a){ try { a.finish(); } catch(e) {} });
    } catch(e) {}
    var all = document.querySelectorAll('*');
    for (var i = 0; i < all.length; i++) {
      var el = all[i];
      if (el.scrollHeight > el.clientHeight + 2) el.scrollTop = 0;
      if (el.scrollWidth > el.clientWidth + 2) el.scrollLeft = 0;
    }
  }, %d);
});
</script></body>""" % (BUDGET_MS - 6000)


def shoot(edge, name, out_png, profile):
    src = os.path.join(SKINS, name + ".html")
    html = open(src, encoding="utf-8").read()
    if "</body>" not in html:
        raise RuntimeError("%s 里没有 </body>，无法注入收尾脚本" % name)
    tmp_name = "_shoot_" + name + ".html"
    tmp = os.path.join(SKINS, tmp_name)      # 放同目录，相对路径也不受影响
    open(tmp, "w", encoding="utf-8").write(html.replace("</body>", SETTLE, 1))
    url = "http://127.0.0.1:%d/%s" % (PORT, urllib.parse.quote("skins/" + tmp_name))
    cmd = [
        edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--virtual-time-budget=%d" % BUDGET_MS,
        "--window-size=%d,%d" % VIEW,
        "--user-data-dir=" + profile,
        "--screenshot=" + out_png,
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=180)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if not os.path.isfile(out_png) or os.path.getsize(out_png) < 20000:
        raise RuntimeError("截图失败：%s\n%s" % (name, r.stderr.decode("utf-8", "replace")[-400:]))


def trim(src, dst):
    """裁掉页边背景色，四周留 PAD。返回 (w, h)。"""
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    h, w, _ = a.shape
    k = 8
    corners = np.concatenate([
        a[:k, :k].reshape(-1, 3), a[:k, w - k:].reshape(-1, 3),
        a[h - k:, :k].reshape(-1, 3), a[h - k:, w - k:].reshape(-1, 3),
    ])
    bg = corners.mean(0)
    mask = np.abs(a - bg).max(2) > BG_TOL
    ys, xs = np.where(mask)
    if len(xs) == 0:
        im.save(dst)
        return im.size
    x0 = max(0, xs.min() - PAD)
    y0 = max(0, ys.min() - PAD)
    x1 = min(w, xs.max() + 1 + PAD)
    y1 = min(h, ys.max() + 1 + PAD)
    out = im.crop((x0, y0, x1, y1))
    out.save(dst, optimize=True)
    return out.size


def main():
    names = sys.argv[1:]
    if not names:
        names = sorted(f[:-5] for f in os.listdir(SKINS) if f.endswith(".html"))
    edge = find_edge()
    os.makedirs(SHOTS, exist_ok=True)
    profile = os.path.join(tempfile.gettempdir(), "edgeshots")
    httpd = serve()
    time.sleep(0.4)
    print("%-14s %-12s %s" % ("skin", "裁剪后", "体积"))
    print("-" * 46)
    total = 0
    try:
        for n in names:
            raw = os.path.join(tempfile.gettempdir(), "shot_%s.png" % n)
            try:
                shoot(edge, n, raw, profile)
                size = trim(raw, os.path.join(SHOTS, n + ".png"))
                kb = os.path.getsize(os.path.join(SHOTS, n + ".png")) // 1024
                total += kb
                print("%-14s %-12s %4d KB" % (n, "%dx%d" % size, kb))
            finally:
                if os.path.isfile(raw):
                    os.remove(raw)
    finally:
        httpd.shutdown()
    print("-" * 46)
    print("共 %d 张，%d KB" % (len(names), total))


if __name__ == "__main__":
    main()
