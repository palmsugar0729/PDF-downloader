"""
页面解析 + PDF 下载模块

使用 Selenium + Chrome 渲染目标页面（document.write() 动态生成），
提取 PDF 链接和标题文本，按规则下载并命名保存。

核心逻辑：
1. 加载页面，等待 JS 渲染完成
2. 查找所有 <div align="right"> 容器
3. 在每个容器中匹配问题 PDF（.pdf）和答案 PDF（s.pdf）
4. 仅当两者同时存在时才下载
5. 解析标题文本 → 生成规范文件名 → 保存到对应目录
"""

import os
import re
import time
import random
import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from parser import parse_title, generate_save_path

logger = logging.getLogger(__name__)

# 合理且友好的 User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# PDF 链接匹配模式
QUESTION_PDF_PATTERN = re.compile(r"^(\d{8})\.pdf$", re.IGNORECASE)
ANSWER_PDF_PATTERN = re.compile(r"^(\d{8})s\.pdf$", re.IGNORECASE)

# 标题文本匹配模式（在 div 的全文文本中搜索）
# 兼容大学名（近畿大）和考试名（センター試験、センター追試等）
TITLE_SEARCH_PATTERN = re.compile(r"(\d{8}.+?\d{2}[^\d]{2,})")


class PDFDownloader:
    """PDF 自动下载器"""

    def __init__(
        self,
        output_dir: str = "./downloads",
        delay_min: float = 1.0,
        delay_max: float = 3.0,
        headless: bool = True,
    ):
        """
        Args:
            output_dir: PDF 输出根目录
            delay_min: 请求最小间隔（秒）
            delay_max: 请求最大间隔（秒）
            headless: 是否使用无头模式运行 Chrome
        """
        self.output_dir = os.path.abspath(output_dir)
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.headless = headless
        self.driver = None
        self.session = None

        # 下载统计
        self.stats = {
            "total_groups": 0,
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
        }

    def _setup_driver(self):
        """初始化 Chrome WebDriver"""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument(f"user-agent={USER_AGENT}")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        # 禁用自动下载弹窗
        prefs = {
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
        }
        options.add_experimental_option("prefs", prefs)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("Chrome WebDriver 初始化完成")

    def _setup_session(self):
        """初始化 HTTP 会话（用于下载 PDF）"""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def _check_robots_txt(self, url: str) -> bool:
        """
        检查目标站点的 robots.txt，确认是否允许爬取。

        Args:
            url: 目标页面完整 URL

        Returns:
            True 表示允许，False 表示禁止
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)

        try:
            rp.read()
            allowed = rp.can_fetch(USER_AGENT, url)
            if allowed:
                logger.info("robots.txt 检查通过，允许爬取: %s", url)
            else:
                logger.warning("robots.txt 禁止爬取此 URL: %s", url)
            return allowed
        except Exception as e:
            logger.warning("无法获取 robots.txt (%s)，默认允许爬取", e)
            return True

    def _random_delay(self):
        """随机延迟 1~3 秒（或用户指定的范围）"""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug("等待 %.1f 秒...", delay)
        time.sleep(delay)

    def _resolve_url(self, base_url: str, href: str) -> str:
        """将相对 URL 解析为绝对 URL"""
        return urljoin(base_url, href)

    def _extract_pdf_groups(self, page_url: str) -> list[dict]:
        """
        从已加载的页面中提取 PDF 分组。

        每个分组包含：标题文本、问题 PDF URL、答案 PDF URL。
        仅返回同时有问题 PDF 和答案 PDF 的有效分组。

        Returns:
            list[dict]: [{'title': '...', 'question_url': '...', 'answer_url': '...'}, ...]
        """
        # 同时匹配小写 right 和大写 RIGHT
        divs = self.driver.find_elements(By.CSS_SELECTOR, 'div[align="right"]')
        if not divs:
            divs = self.driver.find_elements(By.CSS_SELECTOR, 'div[align="RIGHT"]')
        logger.info("找到 %d 个 <div align='right/RIGHT'> 容器", len(divs))

        groups = []
        for idx, div in enumerate(divs, 1):
            # 获取 div 内所有可见文本
            full_text = div.text.strip()

            # 在文本中搜索标题模式
            title_match = TITLE_SEARCH_PATTERN.search(full_text)
            if not title_match:
                logger.info("[div %d/%d] 未找到标题，文本: %s", idx, len(divs), full_text[:80])
                continue

            title_text = title_match.group(1)

            # 查找所有 <a> 链接
            links = div.find_elements(By.TAG_NAME, "a")
            logger.info("[div %d/%d] 标题: %s | 找到 %d 个 <a> 链接", idx, len(divs), title_text, len(links))

            question_url = None
            answer_url = None

            for a_idx, link in enumerate(links, 1):
                href = link.get_attribute("href")
                if not href:
                    logger.info("  [a %d] href 为空，跳过", a_idx)
                    continue

                # 提取文件名
                href_path = urlparse(href).path
                filename = os.path.basename(href_path)

                # 获取链接的各种属性（用于调试）
                link_text = link.text.strip()
                inner_html = link.get_attribute("innerHTML") or ""

                # 策略1: 通过链接文本或子元素标记区分
                # 同时兼容大小写（<p2>/<P2>）和 HTML 实体
                is_question = bool(
                    "問題" in link_text
                    or "<p2>" in inner_html
                    or "<p2 " in inner_html
                    or "<P2>" in inner_html
                    or "<P2 " in inner_html
                )
                is_answer = bool(
                    "解答" in link_text
                    or "<p3>" in inner_html
                    or "<p3 " in inner_html
                    or "<P3>" in inner_html
                    or "<P3 " in inner_html
                )

                # 策略2: 通过文件名模式区分（兜底 fallback）
                if not is_question and not is_answer:
                    if QUESTION_PDF_PATTERN.match(filename):
                        is_question = True
                    elif ANSWER_PDF_PATTERN.match(filename):
                        is_answer = True

                # 记录每个链接的诊断信息
                logger.info(
                    "  [a %d] href=%s | filename=%s | text=%s | is_question=%s | is_answer=%s | innerHTML=%s",
                    a_idx,
                    href,
                    filename,
                    repr(link_text),
                    is_question,
                    is_answer,
                    repr(inner_html[:60]),
                )

                if is_question:
                    question_url = self._resolve_url(page_url, href)
                elif is_answer:
                    answer_url = self._resolve_url(page_url, href)

            # 仅当同时有问题和答案 PDF 时才记录
            if question_url and answer_url:
                groups.append({
                    "title": title_text,
                    "question_url": question_url,
                    "answer_url": answer_url,
                })
                logger.info(
                    "  → 有效分组: %s | Q=%s | A=%s",
                    title_text,
                    os.path.basename(question_url),
                    os.path.basename(answer_url),
                )
            else:
                logger.info(
                    "  → 跳过: 问题=%s, 答案=%s",
                    "有" if question_url else "无",
                    "有" if answer_url else "无",
                )
                self.stats["skipped"] += 1

        self.stats["total_groups"] = len(groups)
        logger.info("提取到 %d 个有效 PDF 分组", len(groups))
        return groups

    def _download_file(self, url: str, dest_path: str) -> bool:
        """
        下载单个文件到指定路径。

        Args:
            url: 文件 URL
            dest_path: 本地保存路径

        Returns:
            True 表示成功，False 表示失败
        """
        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # 如果文件已存在，跳过
            if os.path.exists(dest_path):
                logger.info("文件已存在，跳过: %s", os.path.basename(dest_path))
                return True

            logger.info("下载中: %s → %s", os.path.basename(url), dest_path)

            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # 检查 Content-Type，确保是 PDF
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                logger.warning("响应可能不是 PDF (Content-Type: %s): %s", content_type, url)

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(dest_path)
            logger.info("下载完成: %s (%d bytes)", os.path.basename(dest_path), file_size)
            return True

        except requests.RequestException as e:
            logger.error("下载失败: %s: %s", url, e)
            return False
        except OSError as e:
            logger.error("文件保存失败: %s: %s", dest_path, e)
            return False

    def run(self, url: str) -> dict:
        """
        执行完整的下载流程。

        Args:
            url: 目标页面 URL

        Returns:
            dict: 下载统计
        """
        logger.info("=" * 60)
        logger.info("PDF 自动下载器启动")
        logger.info("目标页面: %s", url)
        logger.info("输出目录: %s", self.output_dir)
        logger.info("=" * 60)

        # 1. 检查 robots.txt
        if not self._check_robots_txt(url):
            logger.error("robots.txt 禁止爬取，终止运行")
            return self.stats

        try:
            # 2. 初始化驱动和会话
            self._setup_driver()
            self._setup_session()

            # 3. 加载页面
            logger.info("正在加载页面...")
            self.driver.get(url)

            # 等待页面渲染完成（document.write() 动态内容）
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[align="right"]'))
                )
            except Exception:
                logger.warning("等待页面元素超时，尝试继续解析...")

            # 额外等待确保 document.write() 完成
            time.sleep(2)
            logger.info("页面加载完成，标题: %s", self.driver.title)

            # 4. 提取 PDF 分组
            groups = self._extract_pdf_groups(url)

            if not groups:
                logger.warning("未找到任何有效的 PDF 分组")
                return self.stats

            # 5. 逐个处理分组
            for i, group in enumerate(groups, 1):
                logger.info("--- [%d/%d] 处理: %s ---", i, len(groups), group["title"])

                # 解析标题
                parsed = parse_title(group["title"])
                if not parsed:
                    logger.warning("标题解析失败，跳过: %s", group["title"])
                    self.stats["skipped"] += 1
                    continue

                # 生成保存路径
                paths = generate_save_path(self.output_dir, parsed)
                logger.info(
                    "  出处: %s | 年份: %s | 知识点: %s",
                    parsed["source"],
                    parsed["year_full"],
                    parsed["knowledge_point"],
                )

                # 下载问题 PDF
                q_ok = self._download_file(group["question_url"], paths["question"])
                if q_ok:
                    self.stats["downloaded"] += 1
                else:
                    self.stats["failed"] += 1

                # 随机延迟
                self._random_delay()

                # 下载答案 PDF
                a_ok = self._download_file(group["answer_url"], paths["answer"])
                if a_ok:
                    self.stats["downloaded"] += 1
                else:
                    self.stats["failed"] += 1

                # 组间随机延迟
                if i < len(groups):
                    self._random_delay()

        except Exception as e:
            logger.exception("运行出错: %s", e)

        finally:
            # 6. 清理资源
            self.cleanup()

        # 7. 输出总结
        logger.info("=" * 60)
        logger.info("下载完成!")
        logger.info("  有效分组: %d 组", self.stats["total_groups"])
        logger.info("  成功下载: %d 个文件", self.stats["downloaded"])
        logger.info("  跳过:     %d 个", self.stats["skipped"])
        logger.info("  失败:     %d 个", self.stats["failed"])
        logger.info("  输出目录: %s", self.output_dir)
        logger.info("=" * 60)

        return self.stats

    def cleanup(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver 已关闭")
            except Exception:
                pass

        if self.session:
            try:
                self.session.close()
            except Exception:
                pass
