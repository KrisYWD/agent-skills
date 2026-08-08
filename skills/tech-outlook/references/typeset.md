# 排版与构建

`assets/build_report.py` 把 markdown 构建成 A4 印刷版 HTML。下面的参数全部经实测，不是从规范文档推断的——改之前先读原因。

## 用法

把脚本复制到报告 markdown 所在目录，改开头两个路径常量指向你的文件，然后：

```bash
python3 build_report.py
```

它会打印构建期断言的结果。**断言不过就中止，不要绕过去。**

## 关键参数与它们的理由

### 正文列 142mm

**38.3 个全角字/行。中文单栏的舒适区是 35—40 字。**

整幅版心 166mm 是 43.6 字/行，已经超出舒适区。所以**列宽不跟着页面走**——不要为了"填满页面"把正文拉宽，那是用可读性换视觉整齐。

### 版心与正文列等宽、左右对称

`@page { margin: 16mm 34mm 17mm 34mm }`，内容盒正好 142mm。

早先为边注栏预留 40mm，结果左边距 13mm、右边距 55mm，版面严重偏心——看起来像浪费了半页，其实是版心没摆正。

### 术语用行内夹注，不用边注栏

Chrome 没有 GCPM 脚注引擎（`CSS.supports('float','footnote') === false`），能写出来的"脚注"只是章末尾注。而边注栏要在**每一页**都预留宽度，一份报告通常只有一两条注释，不值这个预算。

夹注紧跟术语，浅一档（`#6c7d86`）小一档（`.88em`）。**注文超过约 30 字就不该用夹注**——那说明它是正文，不是注。

markdown 里仍用 `**术语**[^key]` + `[^key]: **术语**＝定义` 的写法，脚本会转成夹注。

### 标题间距

打印版 `.h2 { margin: 1.6em 0 .7em }`、`.h3 { margin: 1.25em 0 .45em }`。

屏幕版的 2.2em（≈8mm）在纸面上过松：h2 自带填色块，本身就是强分隔，不需要再靠空白强调。收紧后一份十几页的报告能省下约七行——常常正好消掉末页的孤儿页。

### 三个证据标签

`.tag-fact` / `.tag-judgment` / `.tag-test` 对应成熟度三档。**颜色之外还有边框样式和前导符号两条非色彩通道**，因为三类标签的明度差最小只有 3，黑白打印会糊成同一个灰。

### 构建期断言

脚本里的 `check_maturity()` 强制两件事：每条「路线 N：」必须带成熟度标签；正文不许出现已废弃的写法。

**把约定变成构建期约束。** 靠自觉的规范会失效——本 skill 沉淀自的那次实践里，写在规范里的"判断块 ≤150 字"最后平均 221 字，改成断言之后才真正执行。加新规则就往这个函数里加。

## PDF 自检

HTML 里看不出孤儿页和混排页尺，必须渲染成 PDF 检查。

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=/tmp/check.pdf "file://$PWD/报告.html"

python3 - <<'PY'
import re
from PIL import Image
d = open("/tmp/check.pdf", "rb").read()
boxes = re.findall(rb"/MediaBox\s*\[\s*([\d.\- ]+?)\]", d)
sizes = {tuple(round(float(x), 2) for x in b.split()) for b in boxes}
print("页数:", len(boxes), "｜尺寸集合:", sizes)
assert len(sizes) == 1, "页面尺寸不一致——混排了横竖页"
PY

# 末页是不是孤儿页
pdftoppm -png -r 68 /tmp/check.pdf /tmp/pg
python3 -c "
from PIL import Image; import numpy as np, glob
a = np.array(Image.open(sorted(glob.glob('/tmp/pg-*.png'))[-1]).convert('L'))
inked = ((a < 200).sum(axis=1) > 3).sum()
print(f'末页填充 {inked/a.shape[0]*100:.0f}%')
"
```

**三项判据**：

1. **页面尺寸集合只有一个元素**。混排横竖页会让 PDF 逐页宽度跳变，这是最容易被忽略又最刺眼的毛病。
2. **末页填充 > 25%**。低于这个数就是孤儿页——两三行独占一页。修法不是砍内容，是收紧标题间距或轻微改写让它回到上一页。
3. **图与图注不拆页**。`figure { break-inside: avoid }` 已经在 CSS 里，但要眼看确认。

想逐页看排版，把 PDF 渲染成图直接读：

```bash
pdftoppm -png -r 68 /tmp/check.pdf /tmp/pages/p
```

这一步值得做——本 skill 沉淀自的那次实践里，页脚一直印着早已改掉的旧标题，是渲染成图之后才看见的。
