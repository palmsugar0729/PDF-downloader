"""
标题解析模块

从页面中的标题文本提取元信息：
- 序号（8位数字）
- 知识点
- 年份（2位）
- 出处（大学名、考试名等）

标题格式：{8位序号}{知识点}{2位年份}{出处}
示例：19112202データの分析19近畿大
示例：14010202数と式13センター追試

正则：^(\\d{8})(.+?)(\\d{2})(.+)$
"""

import re
import logging

logger = logging.getLogger(__name__)

# 标题解析正则（兼容以"大"结尾的大学名，以及"センター試験"等考试名）
TITLE_PATTERN = re.compile(r"^(\d{8})(.+?)(\d{2})(.+)$")

# 年份补全阈值：≤ THRESHOLD → 20xx，> THRESHOLD → 19xx
YEAR_THRESHOLD = 26


def parse_title(title_text: str) -> dict | None:
    """
    解析标题文本，提取元信息。

    Args:
            title_text: 页面中的标题文本，如 '19112202データの分析19近畿大' 或 '14010202数と式13センター追試'

    Returns:
        dict: {'serial': '19112202', 'code': '112202', 'knowledge_point': 'データの分析',
               'year_2digit': '19', 'year_full': '2019', 'source': '近畿大'}
        None: 解析失败
    """
    title_text = title_text.strip()
    match = TITLE_PATTERN.match(title_text)

    if not match:
        logger.warning("标题解析失败: %s", title_text)
        return None

    serial, knowledge_point, year_2digit, source = match.groups()

    year_full = _complete_year(year_2digit)
    # 识别码 = 8位序号去掉前2位年份后的剩余6位
    code = serial[2:]

    return {
        "serial": serial,
        "code": code,
        "knowledge_point": knowledge_point,
        "year_2digit": year_2digit,
        "year_full": year_full,
        "source": source,
    }


def _complete_year(year_2digit: str) -> str:
    """
    将 2 位年份补全为 4 位。

    规则：≤ 26 → 20xx，> 26 → 19xx

    Args:
        year_2digit: 2 位年份字符串，如 '19'

    Returns:
        4 位年份字符串，如 '2019'
    """
    year_int = int(year_2digit)
    if year_int <= YEAR_THRESHOLD:
        return f"20{year_2digit}"
    else:
        return f"19{year_2digit}"


def generate_filename(parsed: dict) -> dict[str, str]:
    """
    根据解析结果生成问题 PDF 和答案 PDF 的文件名。

    命名格式：{补全年份}{出处}_{知识点}_{识别码}_问题.pdf / _答案.pdf
    示例：
      - 2019近畿大_データの分析_112202_问题.pdf
      - 2019近畿大_データの分析_112202_答案.pdf
      - 2013センター追試_数と式_010202_问题.pdf

    Args:
        parsed: parse_title() 的返回结果

    Returns:
        dict: {'question': '2019近畿大_データの分析_112202_问题.pdf',
               'answer': '2019近畿大_データの分析_112202_答案.pdf'}
    """
    base = (
        f"{parsed['year_full']}{parsed['source']}"
        f"_{parsed['knowledge_point']}"
        f"_{parsed['code']}"
    )

    return {
        "question": f"{base}_问题.pdf",
        "answer": f"{base}_答案.pdf",
    }


def generate_save_path(output_dir: str, parsed: dict) -> dict[str, str]:
    """
    生成完整的保存路径。

    路径格式：{output_dir}/{出处}/{文件名}

    Args:
        output_dir: 用户指定的输出根目录
        parsed: parse_title() 的返回结果

    Returns:
        dict: {'question': '/path/to/output_dir/近畿大/2019近畿大_データの分析_112202_问题.pdf',
               'answer': '/path/to/output_dir/近畿大/2019近畿大_データの分析_112202_答案.pdf'}
    """
    import os

    filenames = generate_filename(parsed)
    source_dir = os.path.join(output_dir, parsed["source"])

    return {
        "question": os.path.join(source_dir, filenames["question"]),
        "answer": os.path.join(source_dir, filenames["answer"]),
    }
