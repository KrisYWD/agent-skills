#!/usr/bin/env python3
"""把技术前瞻报告的 Markdown 源构建成 A4 印刷版 HTML。

tech-outlook skill 的资源。版面依据全部经实测，不按规范文档推断——
每条参数的理由见 references/typeset.md，改之前先读。

用法：python3 build_report.py <报告.md>
      不给参数时取同目录下唯一的 .md 文件。

页脚文字取自 front matter 的 author 与 title。

版面依据（全部经实测，不按规范文档推断）：

  * 只有一种页面尺寸——A4 纵向。混排横竖页会让 PDF 逐页宽度跳变。
  * 正文列 142mm＝38.3 全角字/行（中文单栏舒适区 35—40 字）。166mm 的整幅版心
    是 43.6 字/行，已经超出舒适区，所以列宽不跟着页面走。
  * 版心与正文列等宽、左右边距对称（各 34mm）。早先为边注栏预留 40mm，
    结果左 13mm、右 55mm，版面严重偏心；而全文实际只有一条注释，不值这个预算。
  * 术语解释用**行内夹注**，不用脚注也不用边注：Chrome 没有 GCPM 脚注引擎
    （CSS.supports('float','footnote') === false），能写出来的"脚注"只是章末尾注，
    而正文的 [1]–[16] 已经是一套尾注了。夹注紧跟术语，位置最近，且不占版面预算。
    注文超过约 30 字就不该用夹注——那说明它是正文，不是注。
  * 标题字号改等比数列（公比 1.25）。原来 h4 只比正文大 6.5%，那不是层级，是字号误差。

已删除的三行"自我安慰"CSS（实测无效）：
    text-justify: inter-ideograph   Chrome 不支持（只支持 inter-character）
    text-autospace: normal          这就是默认值，写了等于没写
    text-spacing-trim: trim-start   依赖字体的 chws 特性表，Source Han Serif SC 没有

"""

from __future__ import annotations

import html as html_lib
import pathlib
import re
import sys
from urllib.parse import unquote

import mistune

HERE = pathlib.Path(__file__).resolve().parent
def resolve_src() -> pathlib.Path:
    """报告路径来自命令行；省略时取同目录下唯一的 .md。"""
    if len(sys.argv) > 1:
        return pathlib.Path(sys.argv[1]).resolve()
    candidates = sorted(HERE.glob("*.md"))
    if len(candidates) != 1:
        raise SystemExit(
            f"同目录下有 {len(candidates)} 个 .md，无法自动选择。"
            f"用法：python3 {pathlib.Path(__file__).name} <报告.md>"
        )
    return candidates[0]

STYLE = """
    :root {
      --ink: #17364b;
      --blue: #1d5a7a;
      --teal: #2d7772;
      --red: #9c4b43;
      --gold: #9a6a2d;
      --paper: #fffdf8;
      --wash: #eef3f4;
      --line: #cbd6da;
    }
    * { box-sizing: border-box; }
    html { background: #e8edef; }
    body {
      max-width: 782px;                /* 608px 正文 ≈ 38 全角字/行，与印刷版同行长 */
      margin: 32px auto;
      padding: 56px 87px;
      background: var(--paper);
      color: var(--ink);
      font-family: "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", STSong, SimSun, serif;
      font-size: 16px;
      line-height: 1.75;
      box-shadow: 0 16px 48px rgba(23, 54, 75, .13);
    }
    .p, li, td, th, figcaption, .blockquote { line-break: strict; }
    .p { margin: .9em 0; color: #243f50; text-align: justify; text-wrap: pretty; }

    /* ── 标题：等比数列，公比 1.25 ── */
    h1 {
      margin: 0 0 20px;
      padding: 0 0 16px;
      border-bottom: 4px solid var(--blue);
      color: var(--ink);
      font-family: "PingFang SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
      font-size: 39px;
      line-height: 1.22;
      text-wrap: balance;
    }
    .h2 {
      margin: 2.2em 0 .9em;
      padding: .5em .7em;
      border-left: 7px solid var(--blue);
      background: var(--wash);
      color: var(--ink);
      font-family: "PingFang SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
      font-size: 25px;
      line-height: 1.32;
      text-wrap: balance;
    }
    .h3 {
      margin: 1.5em 0 .5em;
      padding: .25em 0 .25em .7em;
      border-left: 4px solid var(--teal);
      color: var(--ink);
      font-family: "PingFang SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
      font-size: 20px;
      line-height: 1.45;
      text-wrap: balance;
    }
    /* h4 不用字号分级——撑不起一个字号台阶的层级，换一根轴：排入式 */
    .h4 {
      display: inline;
      margin: 0;
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      font-weight: 700;
      font-size: 1em;
      color: var(--blue);
    }
    .h4::after { content: "　"; }

    .byline {
      margin: 16px 0;
      padding: 12px 16px;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      color: #4e6674;
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 13px;
      line-height: 1.7;
    }
    .evidence-legend {
      margin: 16px 0 24px;
      padding: 14px 16px;
      border-left: 4px solid var(--gold);
      background: #f4f0e6;
      color: #4e6674;
      font-size: 13px;
      line-height: 1.8;
    }

    /* ── 证据标签：颜色之外再加边框样式 + 前导符号两条非色彩通道，
         因为三类标签的明度差最小只有 3，黑白打印会糊成同一个灰 ── */
    .tag {
      display: inline-block;
      margin: 0 .18em .12em 0;
      padding: .05em .4em;
      border: 1px solid currentColor;
      border-radius: 3px;
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: .78em;
      font-weight: 700;
      line-height: 1.55;
      white-space: nowrap;
      vertical-align: .08em;
    }
    .tag::before { margin-right: .26em; font-size: .9em; }
    .tag-fact { color: var(--blue); background: #edf4f7; border-style: solid; }
    .tag-fact::before { content: "\\25CF"; }
    .tag-judgment { color: var(--teal); background: #edf6f3; border-style: dashed; }
    .tag-judgment::before { content: "\\25C6"; }
    .tag-test { color: var(--red); background: #f9eeec; border-style: double; border-width: 3px; }
    .tag-test::before { content: "\\25A0"; }

    /* ── 行内夹注：紧跟术语，浅一档、小一档，不打断阅读 ── */
    .gloss {
      color: #6c7d86;
      font-size: .88em;
    }

    .blockquote {
      margin: 1.1em 0;
      padding: 1em 1.2em;
      border-left: 5px solid var(--blue);
      background: #edf3f5;
      color: var(--ink);
      font-size: 1.05em;
    }
    .blockquote .p { margin: 0; font-weight: 700; }
    a { color: #275f83; text-decoration: underline; text-decoration-thickness: .06em; text-underline-offset: .12em; }
    sup { color: var(--blue); font-family: "PingFang SC", sans-serif; font-weight: 700; }
    .codespan {
      padding: .04em .3em;
      border: 1px solid #dbe3e7;
      border-radius: 2px;
      background: #eef2f4;
      color: var(--ink);
      font-family: "SF Mono", Menlo, Consolas, monospace;
      font-size: 88%;
      overflow-wrap: anywhere;
    }
    figure { margin: 1.4em 0; text-align: center; }
    figure img { display: block; width: 100%; height: auto; margin: 0 auto; }
    figure.cover img { border-radius: 2px; }
    figcaption { margin-top: .5em; font-size: 12px; line-height: 1.55; color: #4e6674; text-align: left; }

    /* ── 三线表。表格的线是用来分组的，不是用来画格子的 ── */
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1em 0;
      border-top: 1px solid var(--ink);
      border-bottom: 1px solid var(--ink);
      font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 13px;
      line-height: 1.45;
      font-variant-numeric: tabular-nums;   /* 满页都是百分比和量纲，数字必须成列 */
    }
    th, td { border: 0; padding: .38em .55em; vertical-align: top; text-align: left; }
    thead th { border-bottom: 1px solid var(--ink); color: var(--ink); font-weight: 700; }
    td { color: #294553; }
    ol, ul { margin: .9em 0 1.1em; padding-left: 1.6em; }
    li { margin: .35em 0; color: #294553; }
    hr { margin: 2.2em 0; border: 0; border-top: 1px solid var(--line); }

    @page {
      size: A4 portrait;
      margin: 16mm 34mm 17mm 34mm;   /* 内容盒 142 × 264mm，与正文列等宽，版心居中 */
      @bottom-left  { content: "__FOOTER__";
                      font-family: "PingFang SC", sans-serif; font-size: 7.5pt; color: #6b7b83; }
      @bottom-right { content: counter(page) " / " counter(pages);
                      font-family: "PingFang SC", sans-serif; font-size: 7.5pt; color: #6b7b83; }
    }

    @media print {
      html, body { background: #fff; }
      body {
        width: 142mm;        /* 38.3 全角字/行——中文单栏舒适区 35—40 字 */
        max-width: none;
        margin: 0;
        padding: 0;
        box-shadow: none;
        font-size: 10.5pt;
        line-height: 1.62;
        orphans: 2;
        widows: 2;
      }
      .p { margin: .5em 0; }
      h1 { font-size: 25.6pt; margin-top: 3mm; }
      /* 标题间距沿用屏幕值（h2 2.2em ≈ 8mm）在纸面上过松：h2 自带填色块，
         本身就是强分隔，不需要再靠空白强调。收紧后全文省下约七行，
         正好消掉末页那两行的孤儿页。 */
      .h2 { font-size: 16.4pt; margin: 1.6em 0 .7em; break-after: avoid-page; break-inside: avoid; }
      .h3 { font-size: 13.1pt; margin: 1.25em 0 .45em; break-after: avoid-page; }
      .h4 { font-size: 10.5pt; }
      .byline, .evidence-legend { font-size: 8.4pt; break-inside: avoid; }
      .evidence-legend { padding: 3mm 4mm; }
      table, figcaption { font-size: 8.4pt; }
      table { line-height: 1.35; break-inside: auto; }
      th, td { padding: .34em .5em; }
      thead { display: table-header-group; break-inside: avoid; }
      tr { break-inside: avoid; }
      .gloss { font-size: .86em; }
      figure { margin: 4mm 0; break-inside: avoid; }
      .blockquote { break-inside: avoid; font-size: 1em; }
      a { color: inherit; text-decoration: none; }
      .tag { font-size: .76em; }
      .codespan { background: transparent; border-color: #b9c6cc; }
      hr { margin: 5mm 0; }
    }
"""

# `TIL[^til]` / `**机械过滤下界**[^xiajie]` → 术语加点线下划线 + 紧随其后的边注块
ANCHOR = re.compile(r"(?:\*\*(?P<b>[^*]+)\*\*|(?P<t>[A-Za-z0-9]+|[一-鿿]{2,8}))\[\^(?P<k>\w+)\]")
FOOTDEF = re.compile(r"^\[\^(\w+)\]:[ \t]*(.+?)$", re.M)


class ReportRenderer(mistune.HTMLRenderer):
    """输出带语义类名的干净标记；正文不带任何行内样式。"""

    def paragraph(self, text: str) -> str:
        m = re.fullmatch(r'\s*<img src="([^"]*)" alt="([^"]*)"\s*/?>\s*', text)
        if m:
            src, alt = m.group(1), m.group(2)
            name = unquote(src).rsplit("/", 1)[-1]
            cls = "cover" if name.startswith("封面-") else ("plate" if name.endswith(".svg") else "chart")
            # alt 文字即图注：`![图 1｜说明](x.png)` → figure + figcaption。
            # 图内只放标题和数据，来源、口径、告诫放图注，避免图片里塞小字。
            cap = f"<figcaption>{alt}</figcaption>" if alt.strip() else ""
            return f'<figure class="{cls}"><img src="{src}" alt="{alt}">{cap}</figure>\n'
        return f'<p class="p">{text}</p>\n'

    def heading(self, text: str, level: int, **attrs) -> str:
        if level == 1:
            return f"<h1>{text}</h1>\n"
        return f'<h{level} class="h{level}">{text}</h{level}>\n'

    def block_quote(self, text: str) -> str:
        return f'<blockquote class="blockquote">{text}</blockquote>\n'

    def codespan(self, text: str) -> str:
        return f'<code class="codespan">{html_lib.escape(text)}</code>'

    def block_html(self, html: str) -> str:
        return html + "\n"

    def thematic_break(self) -> str:
        return "<hr>\n"


def inline_sidenotes(md_text: str) -> tuple[str, int]:
    """把 [^key] 脚注语法就地改写成边注块，并移除定义行。"""
    defs = {k: v.strip() for k, v in FOOTDEF.findall(md_text)}
    md_text = FOOTDEF.sub("", md_text)

    used = 0

    def repl(m: re.Match) -> str:
        nonlocal used
        key = m.group("k")
        body = defs.get(key)
        term = m.group("b") or m.group("t")
        if not body:
            return term
        used += 1
        # 全文只有一条注释，却要在每一页留出 40mm 注栏——不划算。
        # 改成紧跟术语的行内夹注：位置更近，且不占版面预算。
        hm = re.match(r"\*\*(.+?)\*\*\s*[＝=]\s*(.*)", body, re.S)
        rest = (hm.group(2) if hm else body).strip()
        rest = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", rest).rstrip("。")
        return f'{term}<span class="gloss">（{rest}）</span>'

    return ANCHOR.sub(repl, md_text), used


def build() -> None:
    src = resolve_src()
    out = src.with_suffix(".html")
    raw = src.read_text(encoding="utf-8")

    meta = {}
    if raw.startswith("---"):
        _, front, raw = raw.split("---", 2)
        for line in front.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()

    raw, n_notes = inline_sidenotes(raw)

    md = mistune.create_markdown(
        renderer=ReportRenderer(escape=False),
        plugins=["table", "strikethrough"],
    )
    body = md(raw.strip())

    title = meta.get("title", src.stem)
    # 页脚＝性质 + 标题，取自 front matter，避免改了标题忘了改页脚
    footer = "｜".join(x for x in (meta.get("author", ""), title) if x)
    style = STYLE.replace("__FOOTER__", html_lib.escape(footer))
    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_lib.escape(title)}</title>
  <meta name="author" content="{html_lib.escape(meta.get('author', ''))}">
  <meta name="description" content="{html_lib.escape(meta.get('description', ''))}">
  <style id="editorial-print-system">{style}</style>
</head>
<body>
{body}</body>
</html>
"""
    out.write_text(doc, encoding="utf-8")

    check_maturity(body)

    print(
        f"已生成 {out.name}：{len(doc):,} 字符｜"
        f"{doc.count('<figure')} 张图｜{doc.count('class=\"tag ')} 个证据标签｜{n_notes} 条夹注"
    )


# 每条「路线 N：…」必须自带成熟度标签，否则读者无法区分在售商品与论文样片。
ROUTE = re.compile(r"路线[一二三四五六七八九十]+：(.{0,40}?)</strong>(.{0,400}?)(?=<|$)", re.S)
MATURITY = ("【已在售】", "【仅专利论文】", "【关键参数未公开】")
# 上一版的「判断｜依据｜推翻条件」三槽格式已废除；留一条断言防止回潮。
RETIRED = ("推翻条件｜", '【判断】</span>')


def check_maturity(body: str) -> None:
    """在研路线必须标成熟度；同时拦截已废除的判断块格式。"""
    problems = [f"  正文出现已废除的写法「{token}」" for token in RETIRED if token in body]

    routes = re.findall(r"路线[一二三四五六七八九十]+：[^<]{0,60}", body)
    tagged = sum(body.count(f'>{m}<') for m in MATURITY)
    # 扉页图例里三个标签各出现一次，是说明用例，不计入正文
    tagged -= len(MATURITY)
    if routes and tagged < len(routes):
        problems.append(f"  {len(routes)} 条路线只有 {tagged} 个成熟度标签，缺 {len(routes) - tagged} 个")

    if problems:
        raise SystemExit("正文不合规，构建中止：\n" + "\n".join(problems))
    print(f"  在研路线 {len(routes)} 条，成熟度标签 {tagged} 个 ✓")


if __name__ == "__main__":
    build()
