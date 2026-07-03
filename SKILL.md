---
name: fastp-pipeline
description: Run the fastp paired-end FASTQ QC pipeline (outer fastp run.sh + inner fastp_report_deploy report generator). Use when the user wants to (1) run QC on paired-end sequencing data, (2) generate a fastp QC HTML/PDF report from existing fastp JSONs, (3) regenerate specific QC plots, or (4) troubleshoot a failed step in the pipeline. Covers env setup, full pipeline run, single-step debug, project metadata customization, and common failure modes.
---

# fastp QC Pipeline — 使用指南

## 流水线结构

本项目由两段独立的子流水线串联：

```
外层 run.sh  ──▶  fastp QC（每个样本 JSON + HTML）
        │
        └─▶  内层 fastp_report_deploy/run_fastp_report.sh
                │
                └─▶  报告/QC_report.html + report/QC_report.pdf
```

- **外层** (`run.sh`)：在 FASTQ 上并行调 fastp，输出 `*_fastp.{json,html}`。
- **内层** (`fastp_report_deploy/`)：消费 JSON，生成可视化图表 + HTML 汇总 + PDF 报告。
- **桥接**：通过 `./run.sh -r fastp_report_deploy` 一键触发外→内；或独立 `./run_fastp_report.sh` 仅跑报告。

---

## 何时使用本 Skill

在以下场景中调用：
- 用户给了一组 paired-end FASTQ，要求做 QC。
- 用户已有 fastp JSON，要重新生成报告（HTML / PDF / 单文件 HTML）。
- 单步重跑某一类图（质量曲线 / 碱基含量曲线）而不重跑全流程。
- 流水线某一步报错，需要定位与重试。
- 切换项目元数据（项目编号、名称、作者、页眉 logo）。

---

## ⛔ 运行前必读：运行环境约定

> **核心原则：用户必须先指定程序运行环境，智能体必须先切换到该环境，再执行任何流水线命令。未指定环境前，禁止执行。**

### 为什么必须这样做

- `run.sh` 用 `command -v fastp / parallel` 检测二进制；`env_check.py` 用 `python3` 探测 Python 包。**这两个 PATH 和 site-packages 都跟当前 shell 的环境强绑定**。
- 在 base 环境 / 系统 Python / 错误虚拟环境下运行会立即失败（fastp 不在 PATH、PyPDF2 找不到），或者更糟——半成功半失败，产出难以诊断。
- 不同 conda 环境里 fastp / playwright / matplotlib 版本可能不同，会导致 PDF 中文方块、大纲页码偏移等隐性 bug。

### 执行前的强制步骤（按顺序）

1. **询问用户环境**（如果用户没主动说）：
   - 用 `AskUserQuestion` 询问，候选项：本地当前 shell / Conda 环境 / venv 虚拟环境 / 远程主机 / Docker 容器。
   - 用户必须给出**环境名 / 路径 / SSH 别名**之一。

2. **切换到指定环境**（按用户选择执行对应命令）：

   ```bash
   # 情况 A：conda 环境
   conda activate <ENV_NAME>
   # 验证：which python3 fastp parallel

   # 情况 B：venv / virtualenv
   source /path/to/venv/bin/activate
   # 验证：which python3

   # 情况 C：远程主机（SSH）
   ssh <USER>@<HOST> "cd <REMOTE_DIR> && which python3 fastp parallel"
   # 后续命令都包在 ssh 中，或用 sftp/scp 同步文件后执行

   # 情况 D：Docker 容器
   docker exec -it <CONTAINER_ID> bash -c "cd <WORKDIR> && which python3 fastp parallel"

   # 情况 E：Singularity / Apptainer
   singularity exec <IMAGE> bash -c "cd <WORKDIR> && which python3 fastp parallel"
   ```

3. **环境就绪性自检**（切换后必须跑，不通过则停止）：
   ```bash
   python3 -V                         # 必须是 Python 3.6+
   which python3 fastp parallel       # 三个都必须命中
   python3 -c "import yaml, matplotlib, numpy, pandas, jinja2, playwright, PyPDF2; print('OK')"
   playwright --version               # 提示浏览器是否就绪
   ```
   - 任何一条不通过 → 报错并提示用户安装（参考 "环境准备" 一节），**不要**继续往下跑。

4. **进入项目目录后再执行命令**：
   ```bash
   cd <PATH_TO>/fastp_pipeline_SOP    # 注意是 /run.sh 同级目录
   pwd                                 # 必须落在 fastp_pipeline_SOP
   ```

### 智能体答复模板

调用本 Skill 后，第一条回复必须是：

> 请确认运行环境：
> - 1) Conda 环境名：`______`
> - 2) venv 路径：`______`
> - 3) SSH 远程主机：`user@host`
> - 4) Docker 容器 ID/名：`______`
> - 5) 其他（请描述）

收到回答后，先切换 + 自检 → 自检通过 → 才进入"快速开始"或"单步调试"章节的命令。

### 反模式（禁止）

- ❌ 用户没说环境直接跑 `./run.sh ...` —— 高概率失败。
- ❌ 假设用户在 base 环境就够 —— 90% 的生产服务器都不是 base。
- ❌ 切换环境后不验证，直接调流水线 —— 失败时排查成本高。
- ❌ 在错误的 Python 环境里 `pip install` —— 会污染错环境，应先告知用户切到正确环境再装。
- ❌ 把"切换环境 + 自检 + 跑流水线"混在一行 shell 里 —— 出错时无法定位是哪一段失败。

---

## 🔒 安装权限约定（只提示，不动手）

> **核心原则：智能体不得执行任何安装/卸载/系统级变更命令。所有 `pip install` / `conda install` / `apt-get install` / `brew install` / `playwright install` / `sudo ...` 一律由用户自行执行。**

### 为什么必须这样做

- **权限边界**：生产服务器 / 共享集群 / 公司堡垒机的软件安装需要审批，智能体自动执行可能触发审计告警或被安全策略拦截。
- **环境不可逆性**：智能体不知道这个 venv 是否被其他项目共享；不知道 `apt install` 会不会影响线上服务；不知道是否要走代理 / 走内部镜像。
- **可复现性**：用户需要自己决定包版本、安装方式（pip / conda / uv / poetry），智能体强装会破坏环境锁定策略。
- **责任归属**：装错包 / 装坏依赖栈的责任必须由人承担，智能体不应越权。

### 智能体的正确做法：发现缺包 → 仅提示

当自检失败时，按以下模板回复用户，**不要**自己执行任何安装命令：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 环境自检未通过，缺少以下依赖：
  [系统工具]  fastp, parallel
  [Python包]  pyyaml, playwright
  [其他]      chromium 浏览器（playwright）

请在指定环境（<ENV_NAME>）中手动安装：

  # 系统工具
  conda install -c bioconda fastp parallel
  # 或：sudo apt-get install -y fastp parallel

  # Python 包
  pip install pyyaml matplotlib numpy pandas jinja2 playwright pypdf2

  # Playwright 浏览器
  playwright install chromium
  # 系统库（需 root）：sudo bash fastp_report_deploy/Help/install_playwright_deps.sh

安装完成后请回复"已安装"，我会重新运行环境自检。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 禁止的安装行为清单

| 类别 | 禁止命令 | 替代做法 |
|---|---|---|
| Python 包 | `pip install ...` / `pip3 install ...` / `python -m pip install ...` / `uv pip install ...` / `poetry add ...` / `conda install ...` | 打印提示模板，等待用户执行 |
| 系统包 | `apt-get install ...` / `yum install ...` / `dnf install ...` / `brew install ...` | 打印提示模板，等待用户执行 |
| Playwright | `playwright install chromium` / `playwright install-deps` | 打印提示模板，等待用户执行 |
| 提权命令 | `sudo ...` 任何命令 | 提示用户执行；不得自动 sudo |
| 二进制下载 | `wget ...` / `curl ...` 下载并 `chmod +x` 安装 | 提示用户下载链接与安装步骤 |
| 全局状态变更 | `pip install --user ...` / 修改 `/etc/...` / 修改 PATH | 提示用户，影响范围可能超出本项目 |

### 例外（智能体可直接执行）

仅以下场景可由智能体**只读式**执行，**不允许修改系统状态**：
- ✅ `command -v <tool>` / `which <tool>` / `<tool> --version` —— 检查存在与版本。
- ✅ `python3 -c "import xxx"` —— 检查模块可导入性。
- ✅ `pip list` / `pip show <pkg>` / `conda list <pkg>` —— 查询已安装状态。
- ✅ `ls` / `cat` / `find` / `stat` —— 文件元信息查询。
- ✅ `python3 Scripts/env_check.py` —— 运行项目自带的环境检查脚本（只读）。

任何带 `install` / `uninstall` / `remove` / `add` / `upgrade` / `update` / `--upgrade` / `-U` / `-y` 等写操作含义的 flag，**智能体一律不调用**。

### 反模式（禁止）

- ❌ 检测到缺包后自作主张 `pip install pyyaml` —— 越权。
- ❌ 在提示用户前先 `pip install` 试试看 —— 等于默认执行。
- ❌ 把"环境检查 + 自动安装 + 跑流水线"写成一行 shell —— 用户毫无控制权。
- ❌ 在错误的环境里装包（用户说要 `conda activate fastp`，智能体却在 base 里 `pip install`）—— 装错地方。
- ❌ 用 `echo y | sudo apt install` 这种"看似询问实则强装"的做法 —— 仍然越权。
- ❌ 修改 `~/.bashrc` / `~/.zshrc` / shell profile 添加 PATH —— 影响用户全局环境。
- ❌ 创建 / 删除 / 修改 conda 环境（`conda create` / `conda env remove`）—— 用户专属动作。
- ❌ 修改 `requirements.txt` / `environment.yml` 并自动同步安装 —— 包管理是用户决策。

---

## 📋 参数解释与确认约定

> **核心原则：执行 `run.sh` / 任何 Python 脚本前，必须逐个参数向用户解释含义 + 给出建议值 + 等待用户确认，未确认前禁止执行。**

### 为什么必须这样做

- `-i` 错指会把 `fastp` 跑在错误的数据集上，产出污染后续分析。
- `-o` 路径与现有目录冲突会覆盖旧报告；`-w` 过大可能撑爆服务器内存。
- `-r` 路径错指会让内层流水线在错误目录里读不到 JSON。
- Python 脚本 `--config` 错指会让模板找不到；`--with-toc` / `--with-cover` 漏传会让 PDF 缺目录封页。
- 用户经常"我大概知道参数"但记不清每个值的合法范围，**确认环节**是兜底。

### 智能体的标准动作：先解释 → 再提问 → 再执行

按下面 4 步走：

1. **列出所有参数**（无论用户给没给），逐项解释含义、默认值、合法性约束、缺省风险。
2. **对每个参数给出建议值**（基于项目目录结构、当前文件存在性、常用实践）。
3. **用 `AskUserQuestion` 一次性收集所有需要确认的值**（multiSelect 按需）。
4. **用户确认后，把命令完整打印一次**（带 echo 的最终命令），让用户能复制验证，再执行。

### `run.sh` 参数逐项解释

| 参数 | 必填 | 含义 | 默认值 | 取值约束 / 风险 |
|---|---|---|---|---|
| `-i <DIR>` | ✓ | FASTQ 原始数据目录 | — | 必须含 `*_R1*.fq.gz`；R2 按 `_R1`→`_R2` 推断；不存在时 `run.sh:90` 报错退出 |
| `-o <DIR>` |  | fastp 输出目录（保存 `*_fastp.{json,html}`） | `.` 当前目录 | 目录不存在会被 `mkdir -p` 自动创建；如已存在同名 JSON 会被覆盖 |
| `-w <INT>` |  | 每个样本 fastp 线程数 | `4` | 整数；建议 ≤ 服务器核数；过大无收益，过小拖慢 |
| `-r <DIR>` |  | 报告目录；指定后触发内层流水线 | （空） | 必须指向含 `Input/fastp_json/` 的目录；本项目通常填 `fastp_report_deploy` |

#### 标准确认提问模板

执行前对用户说：

```
即将执行以下命令（请逐项确认）：

  ./run.sh -i <INPUT_DIR>  -o <OUTPUT_DIR>  -w <THREADS>  -r <REPORT_DIR>

参数解释：
  -i  FASTQ 原始数据目录（必填）
       含义：含 *_R1*.fq.gz 的目录；R2 文件名按 _R1→_R2 推断
       当前建议值：<探测或询问得到的目录>
       风险：不存在或无 *_R1*.fq.gz 时 run.sh 会立即 exit 1

  -o  fastp 输出目录（保存 *_fastp.{json,html}）
       含义：fastp 的 JSON / HTML 报告落盘位置
       当前建议值：.  （当前目录）或 <新建的子目录>
       风险：若该目录下已有同名 JSON 会被覆盖

  -w  每样本线程数
       含义：单个样本跑 fastp 的并发线程
       当前建议值：4
       风险：过大会与其他任务抢 CPU；过小拖慢单样本

  -r  报告目录（指定后自动跑内层报告流水线）
       含义：含 Input/fastp_json/ 的目录，run.sh 会自动 cd 进去跑 run_fastp_report.sh
       当前建议值：fastp_report_deploy  （项目内自带）
       风险：路径错会读不到 JSON；不指定则只跑 QC 不出报告

是否继续？
  1) 用以上建议值直接执行
  2) 修改部分参数（请告诉我新值）
  3) 先 dry-run（只打印命令，不执行）
```

收到 "1 / 2 / 3" 后再行动。

### Python 脚本参数确认

`render_fastp_html.py`、`html_to_pdf_playwright.py` 等需要 `--config`，部分还带布尔开关。执行前同样要先解释：

| 脚本 | 参数 | 含义 | 默认 | 注意事项 |
|---|---|---|---|---|
| `render_fastp_html.py` | `--config <yaml>` | 项目配置 | （必填） | 通常填 `fastp_report_deploy/config/report.yaml` |
| `html_to_pdf_playwright.py` | `--config <yaml>` | 项目配置 | （必填） | 同上 |
| `html_to_pdf_playwright.py` | `--with-toc` | 生成目录页 | 不传则**无目录** | 报告页数 > 3 时强烈建议开 |
| `html_to_pdf_playwright.py` | `--with-cover` | 追加封页 | 不传则**无封页** | 公司项目通常开 |
| `generate_single_html.py` | （无参数） | — | — | 直接执行 |

确认模板：

```
即将执行 Python 脚本（请确认参数）：

  python  fastp_report_deploy/Scripts/render_fastp_html.py \
          --config fastp_report_deploy/config/report.yaml

参数解释：
  --config  项目元数据 / 路径 / PDF 页眉页脚的 YAML 配置
            含义：决定 HTML 报告标题、作者、页眉 logo 等
            当前建议值：fastp_report_deploy/config/report.yaml

是否继续？
  1) 用以上值执行
  2) 修改配置路径
```

### 反模式（禁止）

- ❌ 用户说"跑一下 QC"就直接 `getopts` 默认值跑 —— 默认值不一定对。
- ❌ 把 4 个参数拼成一条命令直接执行而不解释 —— 用户无法校验。
- ❌ 假定 `-i` 就是当前目录 —— `run.sh` 强制要求显式 `-i`，智能体不能脑补。
- ❌ `-r` 留空又不告诉用户"将只生成 JSON/HTML，不出 PDF 报告" —— 用户期望被违背。
- ❌ `-w` 给 `100` 让用户事后才发现 CPU 100% —— 应建议 ≤ 服务器核数。
- ❌ Python 脚本省略 `--with-toc --with-cover` 又不告知后果 —— 用户可能不知道报告少了什么。
- ❌ 跳过确认环节，直接用 `!` 前缀把命令塞回 prompt 让用户跑 —— 仍属于未确认执行。

---

## 工作目录与路径约定

---

## 工作目录与路径约定

所有命令都假设当前工作目录为 `fastp_pipeline_SOP/`（即与 `run.sh` 同级）。所有 Python 脚本通过 `SCRIPT_DIR = dirname(abspath(__file__))` + `PROJECT_ROOT = dirname(SCRIPT_DIR)` 自动解析路径，**不要**手动 `cd` 到 `fastp_report_deploy/Scripts/` 里调用脚本（除非明确指定）。

关键路径：

| 路径 | 用途 |
|---|---|
| `run.sh` | 外层入口 |
| `fastp_report_deploy/run_fastp_report.sh` | 内层编排脚本 |
| `fastp_report_deploy/config/report.yaml` | 项目元数据 / 输出路径 / PDF 页眉页脚 |
| `fastp_report_deploy/Input/fastp_json/` | fastp JSON 输入目录 |
| `fastp_report_deploy/Output/` | 各步骤中间产物 |
| `fastp_report_deploy/report/` | 最终交付（QC_report.html/pdf） |

---

## 快速开始：一键跑完整流水线

> ⚠️ **运行前必须先按 "📋 参数解释与确认约定" 逐项解释参数含义 + 给出建议值 + 等待用户确认。未确认前禁止直接执行本节命令。**

```bash
# 在 fastp_pipeline_SOP/ 目录下执行（仅示例，最终值由用户确认）
./run.sh -i <FASTQ_DIR> -o <FASTP_OUT_DIR> -w 4 -r fastp_report_deploy
```

参数：

| 参数 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `-i` | ✓ | — | FASTQ 目录；必须含 `*_R1*.fq.gz`；R2 文件名按 `_R1` → `_R2` 推断 |
| `-o` |  | `.` | fastp 输出目录（保存 `*_fastp.html` 与 `*_fastp.json`） |
| `-w` |  | `4` | 每个样本的 fastp 线程数；样本间使用 GNU `parallel` 并发 |
| `-r` |  | — | 指定后自动复制 JSON 到 `<r>/Input/fastp_json/`，然后 `cd` 进 `<r>` 跑 `run_fastp_report.sh` |

前置依赖：`fastp` 与 GNU `parallel` 必须在 PATH；Python 依赖由 `Scripts/env_check.py` 验证。

---

## 仅生成报告（已有 fastp JSON）

```bash
cp <your>/*_fastp.json fastp_report_deploy/Input/fastp_json/
cd fastp_report_deploy
./run_fastp_report.sh
```

`run_fastp_report.sh` 按顺序执行 7 步，任一失败立即 `exit 1`：

1. `env_check.py` — 验证 Python 依赖。
2. `plot_quality_curves.py` — 生成 `Output/read{1,2}_quality_curves/*_quality.png`。
3. `plot_content_curves.py` — 生成 `Output/read{1,2}_content_curves/*_content.png`。
4. `render_fastp_html.py` — JSON → DataFrame → Jinja2 → `Output/html/fastp_qc_summary.html`。
5. `html_to_pdf_playwright.py --with-toc --with-cover` — 渲染 `Output/pdf/fastp_qc_summary.pdf`（带封页/目录/页眉页脚/页码/大纲）。
6. `generate_single_html.py` — 打包单文件 `Output/html/fastp_qc_single_file.html`（base64 内嵌 CSS + 图片）。
7. 整理 → `report/QC_report.html` + `report/QC_report.pdf` + `report/rawData/`。

---

## 单步调试

> ⚠️ **运行前必须先按 "📋 参数解释与确认约定" 解释 Python 脚本的参数（特别是 `--config` / `--with-toc` / `--with-cover`）并等待用户确认。**

直接调用单个 Python 脚本，无需走全流程：

```bash
# 0. 环境检查（pyyaml/matplotlib/numpy/pandas/jinja2/playwright/PyPDF2）
python3 fastp_report_deploy/Scripts/env_check.py

# 1. 仅质量曲线
python  fastp_report_deploy/Scripts/plot_quality_curves.py

# 2. 仅碱基含量曲线
python  fastp_report_deploy/Scripts/plot_content_curves.py

# 3. 重新渲染 HTML（依赖前两步的 PNG）
python  fastp_report_deploy/Scripts/render_fastp_html.py \
    --config fastp_report_deploy/config/report.yaml

# 4. 重新生成 PDF（封页 + 目录 + 主报告）
python  fastp_report_deploy/Scripts/html_to_pdf_playwright.py \
    --config fastp_report_deploy/config/report.yaml \
    --with-toc --with-cover

# 5. 重新生成单文件 HTML（base64 内嵌）
python  fastp_report_deploy/Scripts/generate_single_html.py

# 调试：把 JSON 直接打成 DataFrame / HTML 表
python  fastp_report_deploy/Scripts/fastp_json_to_df.py
```

注意：
- 步骤 1–2 输入必须是 `fastp_report_deploy/Input/fastp_json/*.json`。
- 步骤 3–4 需 `--config` 参数；步骤 1、2、5 不需要。
- 步骤 4 的 `--with-toc` 与 `--with-cover` 是布尔开关，省略则不生成对应部分。

---

## 切换项目元数据

> ⚠️ **每个项目的 `project.*` 字段都不同，必须按当前项目独立确认，禁止复用上一次的值。** 项目编号（`ID`）会出现在 PDF 页眉右侧、项目名称（`name`）会出现在 HTML 报告 H1 标题与 PDF 大纲里，错填会被客户一眼发现。

### 为什么必须每个项目独立确认

- 当前 `report.yaml` 是**香芽蕉时空转录组**项目（`ID: KM-XS-2508-005`），作者"康美华大生信部"。
- 其他项目可能是完全不同的物种 / 部门 / 课题（比如"水稻抗病 GWAS"、"肺癌 WES"、"土壤宏基因组"），所有 `project.*` 字段都得重填。
- `pdf_header_footer.header.right_text` 里硬编码了 `项目编号: KM-XS-2508-005`，**改 `project.ID` 时必须同步改这里**，否则 PDF 页眉与项目编号对不上。
- `assets/images/logo.png` 可能是公司通用 logo（多项目共用），但项目编号 / 名称 / 描述 / 作者 / 日期是项目专属的。

### 智能体的标准动作（只读 + 提醒，**不修改文件**）

执行任何会读取 `report.yaml` 的步骤前（`render_fastp_html.py` / `html_to_pdf_playwright.py` / `run_fastp_report.sh`），智能体**只读不写**，按以下步骤提醒用户去**自己的编辑器 / 配置界面**修改：

1. **`cat fastp_report_deploy/config/report.yaml`** 读取当前值（智能体只读，不假设、不复用上次）。
2. **逐项列出当前 `project.*` 值**给用户看：
   - 项目编号 ID
   - 项目名称 name
   - 项目描述 description
   - 作者 author
   - 日期 date
   - 页眉右侧文案 `pdf_header_footer.header.right_text`（与 ID 联动）
3. **提示字段联动关系**（见下表），特别是 `project.ID` 与 `header.right_text` 的硬编码联动。
4. **询问用户是否需要修改**（用 `AskUserQuestion`）：
   - 选项 A：当前值已对，回复"已确认" → 智能体继续执行下游步骤。
   - 选项 B：需要修改 → 用户去自己的编辑器 / 配置界面改完，回复"已修改"，智能体重新 `cat` 一次复核。
5. **复核后用户明确确认"开始跑流水线"**，智能体才能往下走。

> 🚫 智能体**绝不**用 `Write` / `Edit` 工具 / `cat > report.yaml << EOF ...` / `sed -i` / `python -c "yaml.dump(...)"` 等方式**自行修改** `report.yaml`。配置文件是用户专属决策，必须由用户在外部界面修改。

### 字段联动关系（改 A 必改 B）

| 改 `project.*` 的字段 | 必须同步检查的字段 | 原因 |
|---|---|---|
| `project.ID` | `pdf_header_footer.header.right_text` | 页眉右侧文案里硬编码了项目编号 |
| `project.name` | （无需联动其他字段，但需复核 `templates/fastp_summary.html` 是否需要新项目名） | Jinja2 模板渲染时引用 `project.name` |
| `project.date` | （无联动） | 仅日期字符串 |
| `project.author` | （无联动） | 仅报告署名 |
| `project.description` | （无联动） | 仅 HTML 报告正文 |

### 编辑模板

```yaml
project:
  ID: KM-XS-2508-005                     # 项目编号（出现在 PDF 页眉右侧）
  name: 项目中文名
  description: 项目描述
  author: 部门 / 责任人
  date: 2026-01-08

input:
  fastp_json_dir: Input/fastp_json       # 相对 fastp_report_deploy/ 解析

output:
  html: Output/html/fastp_qc_summary.html
  pdf:  Output/pdf/fastp_qc_summary.pdf

pdf_header_footer:
  header:
    enabled: true
    logo: assets/images/logo.png         # 页眉左侧 logo
    right_text: "康美华大测序数据质控报告 | 项目编号: KM-XS-2508-005"
    logo_height: "25px"
  footer:
    enabled: true
    text: "康美华大基因技术有限公司 | https://www.kmhdgene.com"
    show_page_numbers: true
  margins:
    top: "25mm"
    bottom: "20mm"
    left: "10mm"
    right: "10mm"
```

### 反模式（禁止）

- ❌ **智能体自行修改 `report.yaml`** —— 包括 `Write` / `Edit` 工具、`cat > report.yaml << EOF`、`sed -i`、`python -c "yaml.dump(...)"`、`awk` 等任何写动作。配置文件是用户专属决策，必须由用户在外部编辑器 / 配置界面修改。
- ❌ 看到 `report.yaml` 已存在就跳过确认，直接跑流水线 —— 报告里会出现上一个项目的编号 / 名称。
- ❌ "项目编号改一下" —— 只改 `project.ID`，忘了 `header.right_text` 里硬编码的那一份。
- ❌ 把项目编号 / 名称写到 `templates/fastp_summary.html` 模板里去 —— 模板应只引用 `{{ project.* }}`，硬编码会污染多项目复用。
- ❌ 用户改完 YAML 后不重新 `cat` 复核就继续 —— 用户可能改错或漏改。
- ❌ 把 logo 文件（`assets/images/logo.png`）当成项目专属替换 —— logo 通常是公司级，多项目共用，**别**瞎覆盖。

---

## 环境准备（首次使用）

```yaml
project:
  ID: KM-XS-2508-005                     # 项目编号（出现在 PDF 页眉右侧）
  name: 项目中文名
  description: 项目描述
  author: 部门 / 责任人
  date: 2026-01-08

input:
  fastp_json_dir: Input/fastp_json       # 相对 fastp_report_deploy/ 解析

output:
  html: Output/html/fastp_qc_summary.html
  pdf:  Output/pdf/fastp_qc_summary.pdf

pdf_header_footer:
  header:
    enabled: true
    logo: assets/images/logo.png         # 页眉左侧 logo
    right_text: "康美华大测序数据质控报告 | 项目编号: KM-XS-2508-005"
    logo_height: "25px"
  footer:
    enabled: true
    text: "康美华大基因技术有限公司 | https://www.kmhdgene.com"
    show_page_numbers: true
  margins:
    top: "25mm"
    bottom: "20mm"
    left: "10mm"
    right: "10mm"
```

替换 logo 直接覆盖 `assets/images/logo.png`；分辨率建议 ≥ 600px 宽度。

---

## 环境准备（首次使用）

> ⚠️ **本节是给用户的安装参考。智能体不得代为执行任何安装命令——检测到缺包时只能提示用户按本节手动安装。详见 "🔒 安装权限约定"。**

```bash
# 1. 系统工具（用户执行）
conda install -c bioconda fastp parallel      # 或 apt/brew
# playwright 需要浏览器及系统依赖（root 权限）
sudo bash fastp_report_deploy/Help/install_playwright_deps.sh

# 2. Python 依赖（脚本内未自带 requirements.txt）
pip install pyyaml matplotlib numpy pandas jinja2 playwright pypdf2
playwright install chromium
```

可选：把环境检查作为 CI 门禁 —— `python3 Scripts/env_check.py` 返回非零即视为环境未就绪。

---

## 数据流与产物位置速查

```
FASTQ (*_R1/_R2.fq.gz)
    │  run.sh + GNU parallel + fastp
    ▼
*_fastp.json  ──┐
*_fastp.html    │
                │  cp → Input/fastp_json/*.json
                ▼
        plot_quality_curves.py  ──▶ Output/read{1,2}_quality_curves/*.png
        plot_content_curves.py  ──▶ Output/read{1,2}_content_curves/*.png
        render_fastp_html.py    ──▶ Output/html/fastp_qc_summary.html
        html_to_pdf_playwright  ──▶ Output/pdf/fastp_qc_summary.pdf
        generate_single_html    ──▶ Output/html/fastp_qc_single_file.html
                │
                ▼
        report/QC_report.html + report/QC_report.pdf + report/rawData/
```

---

## 常见问题与故障排查

### 1. `run.sh` 报 "No R1 files found"
- 检查输入目录是否含 `*_R1*.fq.gz`。
- 不接受 `*.fastq.gz` / `*.fq.bz2` / `.fastq`（无 gz）；如需支持其他扩展名，编辑 `run.sh:87` 的 glob。

### 2. 报告里看不到任何图表
- 检查 `fastp_report_deploy/Output/read{1,2}_quality_curves/` 与 `..._content_curves/` 是否真的有 PNG。
- 检查 `render_fastp_html.py` 渲染的图片路径前缀 `../../Output/...` —— 假设 HTML 从 `Output/html/` 被打开；如果改了输出位置必须同步改这里。

### 3. PDF 大纲页码错位
- `html_to_pdf_playwright.py` 已用 PyPDF2 重建大纲并修复偏移。**不要**单独调用 `temp_main.pdf` —— 那是中间产物，运行后会被脚本清理。
- 若 Playwright 失败回退到简单合并（仅 `PdfMerger`），大纲层级会丢失；建议直接重跑整步。

### 4. Playwright 报错 "Executable doesn't exist"
- 未安装 chromium：**请用户在指定环境中手动执行** `playwright install chromium`
- 服务器缺系统库：**请用户在指定环境中手动执行** `sudo bash fastp_report_deploy/Help/install_playwright_deps.sh`

### 5. `env_check.py` 提示缺包
- **智能体只提示，不安装**。请用户在指定环境中手动执行：
  - `pip install pyyaml matplotlib numpy pandas jinja2 playwright pypdf2`
  - 安装 playwright 后再跑 `playwright install chromium`
- 完整提示模板参见 "🔒 安装权限约定"。

### 6. 想保留清洗后的 FASTQ（不仅 HTML/JSON）
- 修改 `run.sh:113-118`：
  - 把 `-o /dev/null -O /tmp/null.fastq` 改成 `-o <out_dir>/${sample}_R1.clean.fq.gz -O <out_dir>/${sample}_R2.clean.fq.gz`。
- 注意这会显著增加磁盘占用。

### 7. 改了样本命名（如去掉 `_R1` / 改成 `.R1.fq.gz`）
- `run.sh:109` 的 `basename "$r1" | sed 's/_R1.*//'` 提取样本名。改名约定必须同步调整此处以及所有报告脚本对 JSON 的查找方式。

### 8. `Scripts/html_to_pdf.py` 与 `html_to_pdf_playwright.py` 怎么选
- 仓库内两个 PDF 脚本并存。`run_fastp_report.sh` 调用的是 **Playwright 版本**（带 TOC/cover/header/footer/outline）。
- `Scripts/html_to_pdf.py`（wkhtmltopdf 版本）**未被编排脚本调用**，仅作历史参考；如要切换需改 `run_fastp_report.sh:21` 的变量名。

### 9. 中文字体在 PDF 中显示为方块
- 安装 `Noto Sans CJK SC` 或 `Microsoft YaHei` 到系统字体目录；Playwright 渲染时 CSS 已声明 `"Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif`。
- 若服务器无 GUI 字体，可用 `fc-cache -fv` 重建缓存。

---

## 关键约定（修改代码前必读）

- **路径锚点**：所有 Python 脚本用 `SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))` + `PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)`。**新增脚本必须保持**这一约定，避免硬编码相对路径。
- **目录职责**：`Input/fastp_json/` 唯一输入；`Output/<step>/` 是各步骤中间产物；`report/` 是最终交付（仅 Step 6 写入）。
- **HTML 渲染路径**：`render_fastp_html.py` 与 `generate_single_html.py` 都假设图片在 `../../Output/...`，改路径需同步两处。
- **fastp 参数**：`-A -G -Q -L`（自动接头 / 去 polyG / 去 N 低质尾部 / 长度过滤）；输出仅 HTML/JSON，FASTQ 丢弃。
- **样本命名**：依赖 `*_R1*.fq.gz` → `_R2` 推断 R2，改名约定要同步改 `run.sh:108-109`。
- **失败即停**：`run.sh` 与 `run_fastp_report.sh` 均 `set -euo pipefail`，任一非零返回即终止。

---

## 调用本 Skill 时的回复模板

当其他智能体调用本 Skill 并希望得到执行建议时，按下面的优先级回答：

0. **先确认运行环境**（最高优先级，未完成前不要进入 1-7）：
   - 用户没说 → 用 `AskUserQuestion` 询问 conda/venv/SSH/Docker 之一；
   - 给了环境 → 先切换（`conda activate` / `source venv/bin/activate` / `ssh` / `docker exec`）；
   - 自检（`which python3 fastp parallel` + `python3 -c "import yaml,..."` + `playwright --version`）通过后再继续；
   - 不通过则报错并停，不允许跳过环境直接跑流水线。
   - **自检发现缺包时**：按 "🔒 安装权限约定" 的提示模板打印要求，**不**代为 `pip install` / `apt install` / `playwright install` / `sudo`。
1. **再确认项目元数据**（"切换项目元数据"章节）：
   - `cat fastp_report_deploy/config/report.yaml` 读取当前值（**只读，不修改**）；
   - 逐项列出 `project.ID / name / description / author / date` 与 `pdf_header_footer.header.right_text` 的当前值；
   - 提示 `project.ID` ↔ `header.right_text` 的**联动关系**（硬编码的"项目编号: KM-XS-2508-005"必须同步改）；
   - 用 `AskUserQuestion` 询问"是否需要修改"，选项 A 已对 / 选项 B 需要修改；
   - 若用户选 B → **让用户去自己的编辑器 / 配置界面改 `report.yaml`**，改完回复"已修改"；
   - 智能体**不**用 `Write` / `Edit` / `cat >` / `sed -i` 等任何方式自行写 `report.yaml`；
   - 用户回复"已修改"后智能体再次 `cat` 复核，然后才往下走。
2. **再解释并确认参数**（"📋 参数解释与确认约定"）：
   - 列出所有将用到的参数（`run.sh` 的 `-i/-o/-w/-r`；Python 脚本的 `--config/--with-toc/--with-cover` 等）；
   - 逐项解释含义、默认值、合法性约束、缺省风险；
   - 给出建议值，用 `AskUserQuestion` 一次性收集用户确认（提供"用建议值 / 修改 / dry-run"选项）；
   - 用户确认后再执行；**禁止**用户没确认就拼命令跑。
3. **明确目的**：跑完整 QC？仅跑报告？仅重跑某一步？改元数据？
4. **当前状态**：JSON 是否已经在 `Input/fastp_json/`？依赖是否安装？（如果缺依赖，回到 0 的提示模板）
5. **给出对应命令**：从上文"快速开始 / 单步调试 / 切换项目元数据"中选（参数值以 2 中的确认结果为准）。
6. **如报错**：从"常见问题"中检索并给出修复命令（修复动作若是安装，同样按提示模板，不亲自动手）。
7. **不要**：`cd` 进 `Scripts/` 执行脚本；删 `temp_main.pdf` / `temp_toc.pdf`；修改 `Output/` 内的产物名（下游依赖路径）；在未确认环境前跑任何命令；在用户未确认参数前跑任何命令；在未确认项目元数据前跑任何命令；**智能体自行修改 `report.yaml`**（包括 `Write` / `Edit` / `cat >` / `sed -i` / `python yaml.dump` 等任何写动作 —— 配置必须由用户在外部界面改）；复用上一次项目的 `project.*` 值而不重新确认；任何形式的代为安装（`pip install` / `conda install` / `apt-get install` / `brew install` / `playwright install` / `sudo` / 修改 shell profile / `pip install --user` / `conda create` / `conda env remove`）。