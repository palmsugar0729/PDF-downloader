# PDF Downloader

自动爬取指定网页中的数学题目 PDF（问题 + 答案），智能命名并分类保存。

## 适用场景

从类似 [mikiotaniguchi.com](https://mikiotaniguchi.com/main/sm/smmain.htm) 的数学题库站点下载 PDF，按"年份 + 出处 + 知识点 + 识别码"的格式自动命名，并按出处分文件夹。

## 技术栈

- Python 3
- Selenium + Chrome

## 快速开始

```bash
# 1. 安装依赖
cd codes
pip install -r requirements.txt

# 2. 运行（确保 Chrome 已安装）
# 方式一：交互模式（直接运行，按提示输入 URL 和保存路径）
python main.py

# 方式二：参数模式（适合脚本调用）
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" -o ./downloads
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" -o ./downloads --delay-min 2 --delay-max 5
python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" --no-headless  # 显示浏览器窗口
```

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
│   ├── main.py         # CLI 入口
│   ├── downloader.py   # Selenium 爬取 + PDF 下载
│   ├── parser.py       # 标题解析 + 命名生成
│   └── requirements.txt
├── docs/               # 产品文档 & 需求 & 开发日志
├── assets/             # 设计素材 & 截图
│   ├── bug/            # 测试 bug 截图
│   ├── design/
│   └── reference/      # 参考图、灵感收集
├── notes/              # 学习笔记
├── AGENTS.md           # AI 开发指南
└── README.md           # 本文件
```

## 许可

个人工具，自用为主。
