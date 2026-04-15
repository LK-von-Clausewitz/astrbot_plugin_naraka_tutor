import re


def clean_text(text: str) -> str:
    """清洗从 PDF 提取的原始文本。"""
    # 替换多种空白字符为普通空格
    text = text.replace('\xa0', ' ').replace('\u3000', ' ')
    # 删除多余换行，保留段落结构
    text = re.sub(r'\n+', '\n', text)
    # 删除行首行尾空格
    lines = [line.strip() for line in text.split('\n')]
    # 过滤空行但保留段落间隔
    cleaned_lines = []
    for line in lines:
        if line:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)


def table_to_markdown(table) -> str:
    """
    将 PyMuPDF 提取的表格对象转换为 Markdown 表格字符串。
    不依赖 pandas/tabulate，纯原生实现。
    """
    try:
        cells = table.extract()
    except Exception:
        return ""
    if not cells:
        return ""

    # 统一列数
    max_cols = max(len(row) for row in cells)
    normalized = []
    for row in cells:
        if len(row) < max_cols:
            row = list(row) + [""] * (max_cols - len(row))
        normalized.append(row)

    lines = []
    for i, row in enumerate(normalized):
        # 清洗单元格内容：去换行、去首尾空格
        cleaned_cells = [str(cell).replace('\n', ' ').replace('\r', ' ').strip() for cell in row]
        lines.append("| " + " | ".join(cleaned_cells) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * max_cols) + " |")

    return "\n".join(lines)


def split_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list:
    """按字符数对文本进行滑动窗口分块。"""
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)
        if end >= text_len:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks
