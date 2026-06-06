# PDF Downloader

自动爬取指定网页中的数学题目 PDF（问题 + 答案），智能命名并分类保存。

## 适用场景

从类似 [mikiotaniguchi.com](https://mikiotaniguchi.com/main/sm/smmain.htm) 的数学题库站点下载 PDF，按"年份 + 出处 + 知识点 + 识别码"的格式自动命名，并按出处分文件夹。

## 技术栈

- Python 3
- Selenium + Chrome

## 快速开始

### 方式一：双击运行（推荐 Windows 用户）

直接双击根目录的 **`run.bat`**，按提示输入即可。

### 方式二：命令行运行

```bash
# 1. 安装依赖
cd codes
pip install -r requirements.txt

# 2. 运行（确保 Chrome 已安装）
# 交互模式（直接运行，按提示输入 URL 和保存路径）
python main.py

# 参数模式（适合脚本调用）
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" -o ./downloads
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" -o ./downloads --delay-min 2 --delay-max 5
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" --no-headless  # 显示浏览器窗口
```

### 交互流程

1. 提示输入目标网页 URL（有默认值，直接回车即可）
2. 提示输入 PDF 保存目录（有默认值）
3. 开始下载，显示实时日志
4. 下载完成后询问：`是否继续下载其他页面？(y/n)`
5. 回答 `y` → 重新开始；回答 `n` → 退出程序

## 命令行参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | 否 | — | 目标页面地址（不传则交互式输入） |
| `-o, --output` | 否 | `./downloads` | PDF 输出目录 |
| `--delay-min` | 否 | `1` | 请求最小间隔（秒） |
| `--delay-max` | 否 | `3` | 请求最大间隔（秒） |
| `--no-headless` | 否 | — | 显示 Chrome 浏览器窗口（调试用） |
| `-v, --verbose` | 否 | — | 显示详细日志（DEBUG 级别） |

## 命名规则

从页面标题中提取信息，生成唯一文件名：

| 标题示例 | 文件名示例 |
|----------|-----------|
| `19112202データの分析19近畿大` | `2019近畿大_データの分析_112202_问题.pdf` |
| `14010202数と式13センター追試` | `2013センター追試_数と式_010202_问题.pdf` |

- **8 位序号拆分**：前 2 位 → 年份（补全为 4 位），后 6 位 → 识别码（防重名覆盖）
- **年份补全**：`≤ 26` → `20xx`，`> 26` → `19xx`
- **保存路径**：`{输出目录}/{出处}/`

## 项目结构

```
├── codes/              # 所有源代码
│   ├── main.py         # CLI 入口（交互式 + 循环下载）
│   ├── downloader.py   # Selenium 爬取 + PDF 下载
│   ├── parser.py       # 标题解析 + 命名生成
│   └── requirements.txt
├── docs/               # 产品文档 & 需求 & 开发日志
│   ├── PRD_1.0.md      # 已封存的产品需求（第一期）
│   ├── PRD_2.0.md      # 下期产品需求（规划中）
│   ├── needs_1.0.md    # 已封存的需求文档（第一期）
│   ├── needs_2.0.md    # 下期需求文档（规划中）
│   └── 2026-06-05_开发日志.md
├── assets/             # 设计素材 & 截图
│   ├── bug/            # 测试 bug 截图
│   ├── design/
│   └── reference/      # 参考图、灵感收集
├── notes/              # 学习笔记
├── run.bat             # Windows 一键运行脚本
├── AGENTS.md           # AI 开发指南
└── README.md           # 本文件
```

## 文档索引

| 文档 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | AI/开发者指南，含技术决策和代码规则 |
| [docs/PRD_1.0.md](docs/PRD_1.0.md) | 第一期产品需求文档（已封存） |
| [docs/PRD_2.0.md](docs/PRD_2.0.md) | 第二期产品需求文档（规划中） |
| [docs/needs_1.0.md](docs/needs_1.0.md) | 第一期需求文档（已封存） |
| [docs/needs_2.0.md](docs/needs_2.0.md) | 第二期需求文档（规划中） |
| [docs/2026-06-05_开发日志.md](docs/2026-06-05_开发日志.md) | 第一期完整开发记录 |
| [docs/2026-06-06_开发日志.md](docs/2026-06-06_开发日志.md) | chromedriver 锁超时/下载卡顿修复记录 |
| [docs/踩坑记录.md](docs/踩坑记录.md) | 已知踩坑点汇总与解决方案速查 |

## 许可

个人工具，自用为主。
