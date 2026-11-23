# 第三方资产清单

本仓库除下列一项外全部为原创。列出是为了让 MIT 的覆盖范围清晰。

## Fusion Pixel 12px Monospaced

| 项 | 值 |
|---|---|
| 字体 | Fusion Pixel Font（缝合像素字体）12px Monospaced，`zh_hans` 子集 |
| 作者 | TakWolf |
| 上游仓库 | https://github.com/TakWolf/fusion-pixel-font |
| 许可证 | SIL Open Font License 1.1 |
| 许可全文（仓库内） | [`LICENSE-OFL-1.1.txt`](LICENSE-OFL-1.1.txt) |
| 许可全文（上游） | https://github.com/TakWolf/fusion-pixel-font/blob/master/LICENSE-OFL |
| 正文来源 | https://openfontlicense.org/documents/OFL.txt，下载于 2026-11-23，正文未改 |
| 存在形式 | WOFF2，base64 内嵌在 `skins/B-pixel.html`、`skins/B-paper.html` 的 `@font-face` 中 |
| 是否修改 | 否。未子集化、未改名、未改动字形数据 |
| 子集说明 | 使用的是上游已发布的 `zh_hans` 子集，属上游产物，不是本仓库的再加工 |
| 文件内署名 | 两个文件的 `@font-face` 上方均有注释：`真像素字体（Fusion Pixel 12px Monospaced zh_hans · OFL 1.1 · TakWolf）` |

### 关于 OFL 合规

OFL 1.1 允许嵌入、重分发与商业使用，要求保留版权声明与许可证、不得单独售卖字体本身、修改后的字体不得沿用 Reserved Font Name。

本仓库的做法：

- **许可正文随仓库分发**（`LICENSE-OFL-1.1.txt`），不是只给一个链接
- 版权行与 Reserved Font Name **以上游仓库为准**，本仓库不代为改写。`LICENSE-OFL-1.1.txt` 头部写明了这一点，并去掉了官方模板里形如 `Copyright (c) <dates>, <Copyright Holder>` 的未填示例行 —— 那是占位符，不是声明，留着反而会被误读成本项目的版权主张
- 字体未作任何修改，因此不涉及 Reserved Font Name 的改名要求

## 其余全部原创

- 14 套界面的 HTML / CSS / JS（`skins/*.html`）
- 14 张 `shots/*.png` 展示图（**PNG，不是 JPG**）
- `index.html` 总览页
- `tools/probe_layout.py`、`tools/shoot_shots.py`
- `README.md`、`docs/gallery.md`、`_skipped/README.md`

以上按仓库根目录 `LICENSE`（MIT）授权。

## 边界的准确说法

| 说法 | 是否成立 |
|---|---|
| 运行时无外部网络请求 | 成立。字体内嵌，图形全用 CSS 画，没有 CDN |
| 无需构建步骤 | 成立。单文件 HTML，双击即开 |
| 不含第三方代码或资产 | **不成立**。字体是第三方资产，只是不联网 |
| 交付物依赖本机 Edge | 不成立。只有截图/体检脚本依赖，与页面运行无关 |
