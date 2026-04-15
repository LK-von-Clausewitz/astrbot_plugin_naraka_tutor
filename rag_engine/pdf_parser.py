import os
from astrbot.api import logger
from .utils import clean_text, split_text, table_to_markdown

try:
    import fitz  # PyMuPDF
except Exception as e:
    fitz = None
    logger.error(f"[NarakaTutor] 无法导入 PyMuPDF: {e}")


class PDFParser:
    """PDF 解析器：提取文本、识别表格、清洗、分块。"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64, parse_tables: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.parse_tables = parse_tables

    def parse_file(self, file_path: str) -> list:
        """
        解析单个 PDF 文件，返回文本块列表。
        每个元素为 dict: {"source": str, "page": int, "text": str}
        """
        if fitz is None:
            logger.error("[NarakaTutor] PyMuPDF 未安装，无法解析 PDF。")
            return []

        if not os.path.exists(file_path):
            logger.warning(f"[NarakaTutor] 文件不存在: {file_path}")
            return []

        chunks = []
        filename = os.path.basename(file_path)
        try:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)

                if self.parse_tables and hasattr(page, "find_tables"):
                    tables = page.find_tables()
                    if tables and tables.tables:
                        raw_text = self._extract_page_with_tables(page, tables)
                    else:
                        raw_text = page.get_text()
                else:
                    raw_text = page.get_text()

                cleaned = clean_text(raw_text)
                if not cleaned:
                    continue
                page_chunks = split_text(cleaned, self.chunk_size, self.chunk_overlap)
                for idx, chunk in enumerate(page_chunks):
                    chunks.append({
                        "source": filename,
                        "page": page_num + 1,
                        "chunk_index": idx,
                        "text": chunk,
                    })
            doc.close()
            logger.info(f"[NarakaTutor] 解析完成: {filename}，共 {len(chunks)} 个文本块。")
        except Exception as e:
            logger.error(f"[NarakaTutor] 解析 PDF 失败 [{filename}]: {e}")
        return chunks

    def _extract_page_with_tables(self, page, tables):
        """
        提取页面文本，将表格区域替换为 Markdown 表格，
        避免纯文本提取导致列数据错乱。
        """
        if fitz is None:
            return page.get_text()

        text_dict = page.get_text("dict")
        table_bboxes = [fitz.Rect(tab.bbox) for tab in tables.tables]
        table_markdowns = []

        for tab in tables.tables:
            md = table_to_markdown(tab)
            if md:
                # 用 y0 坐标排序插回文本流
                table_markdowns.append((tab.bbox[1], f"[表格]\n{md}\n[/表格]"))

        non_table_parts = []
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            block_rect = fitz.Rect(block["bbox"])
            block_area = block_rect.get_area()

            # 判断该文本块是否主要落在某个表格区域内（重叠面积 > 50%）
            in_table = False
            for tbox in table_bboxes:
                inter_area = block_rect.intersect(tbox).get_area()
                if block_area > 0 and (inter_area / block_area) > 0.5:
                    in_table = True
                    break
            if in_table:
                continue

            block_lines = []
            for line in block["lines"]:
                line_text = "".join(span["text"] for span in line["spans"]).strip()
                if line_text:
                    block_lines.append(line_text)
            if block_lines:
                non_table_parts.append((block["bbox"][1], "\n".join(block_lines)))

        all_parts = non_table_parts + table_markdowns
        all_parts.sort(key=lambda x: x[0])
        return "\n\n".join([part[1] for part in all_parts])

    def parse_directory(self, directory: str) -> list:
        """解析目录下所有 PDF 文件。"""
        all_chunks = []
        if not os.path.isdir(directory):
            logger.warning(f"[NarakaTutor] 目录不存在: {directory}")
            return all_chunks

        for filename in sorted(os.listdir(directory)):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(directory, filename)
                all_chunks.extend(self.parse_file(file_path))
        return all_chunks
