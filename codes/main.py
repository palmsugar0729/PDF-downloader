"""
CLI 入口 — PDF 自动下载工具

用法：
    # 交互模式（直接运行，按提示输入）
    python main.py

    # 参数模式（一次性传入，适合脚本调用）
    python main.py "https://target.com/page.htm" -o ./downloads
    python main.py "https://target.com/page.htm" -o ./downloads --delay-min 2 --delay-max 5
    python main.py "https://target.com/page.htm" --no-headless  # 显示浏览器窗口
"""

import argparse
import logging
import sys
import os

from downloader import PDFDownloader


# 默认目标页面（方便调试时直接回车）
DEFAULT_URL = "https://mikiotaniguchi.com/main/sm/smmain.htm"
# 默认输出目录
DEFAULT_OUTPUT = "./downloads"


def setup_logging(verbose: bool = False):
    """配置日志"""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)

    # 降低第三方库日志级别
    for name in ("selenium", "urllib3", "webdriver_manager"):
        logging.getLogger(name).setLevel(logging.WARNING)


def prompt_url(default: str = DEFAULT_URL) -> str:
    """交互式提示用户输入目标页面 URL"""
    print()
    print("=" * 60)
    print("  PDF 自动下载工具")
    print("=" * 60)
    print()
    print("请输入目标网页地址（直接回车使用默认值）：")
    print(f"  默认: {default}")
    user_input = input("> ").strip()
    url = user_input if user_input else default
    print(f"  已选择: {url}")
    return url


def prompt_output_dir(default: str = DEFAULT_OUTPUT) -> str:
    """交互式提示用户输入输出目录"""
    print()
    print("请输入 PDF 保存目录（直接回车使用默认值）：")
    print(f"  默认: {default}")
    user_input = input("> ").strip()
    output_dir = user_input if user_input else default
    print(f"  已选择: {output_dir}")
    return output_dir


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="PDF 自动下载工具 — 从指定网页下载数学题目的 PDF（问题+答案）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
交互模式（推荐）:
  python main.py

参数模式（脚本/调试配置）:
  python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm"
  python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" -o ./my_downloads
  python main.py "https://mikiotaniguchi.com/main/sm/smmain.htm" --delay-min 2 --delay-max 5
        """,
    )

    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="目标页面地址（不传则进入交互模式）",
    )
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"PDF 输出目录 (默认: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--delay-min",
        type=float,
        default=1.0,
        help="请求最小间隔/秒 (默认: 1.0)",
    )
    parser.add_argument(
        "--delay-max",
        type=float,
        default=3.0,
        help="请求最大间隔/秒 (默认: 3.0)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="显示 Chrome 浏览器窗口（调试用）",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志（DEBUG 级别）",
    )

    return parser.parse_args()


def run_single(args) -> dict:
    """
    执行单次下载流程。

    Args:
        args: argparse 解析结果

    Returns:
        dict: 下载统计
    """
    logger = logging.getLogger(__name__)

    # 如果命令行没有传 url，进入交互模式
    url = args.url if args.url else prompt_url(default=DEFAULT_URL)

    # 如果用户通过 -o 显式指定了路径（且不是默认值），就用参数；
    # 否则也进入交互式确认
    if args.output != DEFAULT_OUTPUT:
        output_dir = args.output
    else:
        output_dir = prompt_output_dir(default=DEFAULT_OUTPUT)

    output_dir = os.path.abspath(output_dir)
    logger.info("输出目录: %s", output_dir)

    # 创建下载器并运行
    downloader = PDFDownloader(
        output_dir=output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        headless=not args.no_headless,
    )

    try:
        stats = downloader.run(url)

        # 根据结果输出总结提示
        if stats["failed"] > 0:
            logger.warning("本次下载有 %d 个文件失败", stats["failed"])
        elif stats["downloaded"] == 0 and stats["total_groups"] == 0:
            logger.warning("未找到任何可下载的 PDF")

        return stats

    except KeyboardInterrupt:
        logger.info("用户中断，正在清理...")
        downloader.cleanup()
        raise
    except Exception as e:
        logger.exception("未预期的错误: %s", e)
        downloader.cleanup()
        raise


def prompt_continue() -> bool:
    """询问用户是否继续下载"""
    print()
    print("=" * 60)
    while True:
        choice = input("是否继续下载其他页面？(y/n): ").strip().lower()
        if choice in ("y", "yes", "是"):
            return True
        elif choice in ("n", "no", "否"):
            return False
        else:
            print("请输入 y 或 n")


def main():
    """主入口 — 支持循环下载"""
    args = parse_args()
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    first_run = True

    while True:
        try:
            # 非首次运行时，重置 args 以触发交互式输入
            if not first_run:
                args.url = None
                args.output = DEFAULT_OUTPUT

            stats = run_single(args)
            first_run = False

        except KeyboardInterrupt:
            logger.info("程序被用户中断")
            sys.exit(130)
        except SystemExit:
            # run_single 中不会调用 sys.exit，但保留处理
            raise
        except Exception:
            # 出错后询问是否继续，而不是直接退出
            first_run = False

        # 询问是否继续
        if not prompt_continue():
            print()
            print("感谢使用，再见！")
            print("=" * 60)
            break


if __name__ == "__main__":
    main()
