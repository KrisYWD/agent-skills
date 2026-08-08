# agent-skills

个人的 Claude Code skill 仓库。布局遵循 [skills.sh](https://www.skills.sh/docs) 约定（`skills/<name>/SKILL.md`），因此也能被 `npx skills add` 发现。

---

## 🤖 给 agent：装机流程

**用户把这个仓库交给你，就是要你帮他装 skill。按下面走：**

1. **读下面的「可用 skill」表**
2. **问用户要装哪些**（列出名字和一句话说明让他挑，可以多选或全装）
3. **只装他选的**，跳过其余
4. **装完跑验收**，把结果告诉他

不要自作主张全装，也不要跳过第 2 步——有些 skill 有额外依赖，用户可能不想装。

### 安装（对每个选中的 skill）

```bash
mkdir -p ~/.claude/skills
cp -R skills/<name> ~/.claude/skills/
```

⚠️ **目标已存在同名目录时，`cp -R` 会合并而不是替换**，可能留下旧版残留文件。先备份再删：

```bash
[ -d ~/.claude/skills/<name> ] && mv ~/.claude/skills/<name> ~/.claude/skills/<name>.bak
```

### 装完验收

```bash
ls ~/.claude/skills/<name>/SKILL.md && head -1 ~/.claude/skills/<name>/SKILL.md
```

首行是 `---` 且文件存在即安装成功。再按各 skill 的依赖表装依赖、跑各自的验收命令。

---

## 可用 skill

| 名字 | 一句话 | 触发 | 额外依赖 |
|---|---|---|---|
| **tech-scout** | 从零侦察一个工业/制造技术方向：先教会你，再多轮并行检索，产出可决策的调研 | `/tech-scout` | 无（纯标准库） |
| **tech-outlook** | 把调研语料写成产业前瞻报告，麦肯锡式结构、工序为主干，出 A4 印刷版 HTML | `/tech-outlook` | `mistune` · Chrome |

两个都是**用户触发**（`disable-model-invocation: true`）：只有人手打名字才能调用，不会被自动触发，在 context 里常驻成本为零。

**两者配合使用**：`tech-scout` 负责阶段一（教会用户）和阶段二（多轮侦察），`tech-outlook` 负责阶段三（写报告）。只装前者也能用，报告阶段换别的方式写就是了。

---

### tech-scout

把一个工业/制造技术方向从零查到能做决策。**调用时可以什么都不指定**——摸清用户要什么是它的第一项工作。

三个阶段，各自独立 session，靠一个文件夹交接：

```
① 学习   /tech-scout          先教会用户，同时摸清需求。不派 subagent
              ↓ 它吐出交接提示词
② 探索   /tech-scout <目录>   grill ⇄ 派队 ⇄ 阶段报告，循环
              ↓ 它吐出交接提示词
③ 报告   /tech-outlook <语料> 输入必须是原始语料，不是阶段报告
```

**依赖**：无。`assets/sources.py`（引用账本）只用 Python 标准库。

**验收**：

```bash
python3 ~/.claude/skills/tech-scout/assets/sources.py --help | head -3
```

**用法详见** `skills/tech-scout/README.md`（装好后在 `~/.claude/skills/tech-scout/README.md`）。

---

### tech-outlook

把一堆调研语料写成给**行业内技术负责人**看的前瞻报告：某项技术的门槛正在往哪儿移，每道工序上有哪些路线在推进，各自卡在哪、什么条件下会成。

体裁锁死，行业不限——口罩、电池、半导体、制药都能用。**市场报告、财务分析、竞品分析用不了它。**

**依赖**：

| | 用途 | 装法 | 缺了会怎样 |
|---|---|---|---|
| `mistune` | 构建 HTML | `pip3 install mistune` | 出不了报告 |
| Google Chrome | headless 出 PDF 自检排版 | `brew install --cask google-chrome` | 跳过排版自检 |

`pip3` 报 `externally-managed-environment` 时用 `pip3 install --user mistune`。

**验收**：

```bash
python3 -c "import mistune; print('mistune', mistune.__version__)"
```

---

## 备选装法：npx skills

本仓库符合 skills.sh 的目录约定，理论上可以：

```bash
npx skills add KrisYWD/agent-skills
```

⚠️ **首次用要先验证它是否连 `references/` 和 `assets/` 一起复制**——这两个 skill 缺了子目录就是废的。验证：

```bash
ls ~/.claude/skills/tech-scout/references/ ~/.claude/skills/tech-scout/assets/
```

`references/` 下应有 4 个 md、`assets/` 下应有 `sources.py`。**少了就退回上面的 `cp -R` 装法。**

---

## 多机同步

clone 一次，symlink 进去，之后 `git pull` 即生效：

```bash
git clone https://github.com/KrisYWD/agent-skills.git ~/code/agent-skills
mkdir -p ~/.claude/skills
ln -s ~/code/agent-skills/skills/tech-scout   ~/.claude/skills/tech-scout
ln -s ~/code/agent-skills/skills/tech-outlook ~/.claude/skills/tech-outlook
```

⚠️ symlink 方式下改 skill 就是改仓库工作区，记得 commit。

---

## 排障

| 症状 | 原因 | 处理 |
|---|---|---|
| `/tech-scout` 不被识别 | 目录没放对，或 `SKILL.md` 缺 frontmatter | 确认 `~/.claude/skills/tech-scout/SKILL.md` 存在且首行是 `---` |
| 报错 `No module named 'mistune'` | 依赖没装 | `pip3 install --user mistune` |
| PDF 自检找不到 Chrome | Chrome 装在别处或用的是 Edge/Chromium | 改 `tech-outlook/references/typeset.md` 里的 `CHROME=` 路径 |
| 引用校验报 `账本里没有 S<n>` | subagent 编造了引用 id | **这是脚本在正常工作**，打回该路重做 |
| skill 目录里只有 SKILL.md，没有 references/ | 用 `npx skills add` 装的，子目录没跟过来 | 改用 `cp -R` 或 symlink |

---

## 加新 skill 到这个仓库

放进 `skills/<name>/`，`SKILL.md` 的 frontmatter 至少要有 `name` 和 `description`。然后在上面的「可用 skill」表里加一行——**那张表是 agent 装机时唯一会读的目录**，不加就等于没有。
