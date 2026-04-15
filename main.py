import os
import re
from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.api import AstrBotConfig
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.message_components import At

from .rag_engine import PDFParser, VectorStore


@register("naraka_tutor", "YourName", "永劫无间教学 RAG 插件", "1.0.0")
class NarakaTutorPlugin(Star):
    """
    永劫无间游戏技巧教学插件。
    群聊中 @机器人 + 自然语言提问时，自动从本地 PDF 知识库检索相关材料并注入 LLM 上下文。
    """

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 路径计算
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        astrbot_root = os.path.dirname(os.path.dirname(self.plugin_dir))
        self.data_dir = os.path.join(astrbot_root, "data", "plugin_data", "astrbot_plugin_naraka_tutor")
        self.materials_dir = os.path.join(self.plugin_dir, "materials")
        self.vector_db_dir = os.path.join(self.data_dir, "vector_db")

        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.vector_db_dir, exist_ok=True)

        # 初始化组件
        self.chunk_size = int(config.get("chunk_size", 512))
        self.chunk_overlap = int(config.get("chunk_overlap", 64))
        self.top_k = int(config.get("top_k", 5))
        self.parse_tables = bool(config.get("parse_tables", True))
        self.trigger_keywords = list(config.get("trigger_keywords", []))
        self.system_prompt_template = str(config.get("system_prompt_template", ""))

        self.pdf_parser = PDFParser(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            parse_tables=self.parse_tables,
        )
        self.vector_store = VectorStore(persist_directory=self.vector_db_dir)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        """AstrBot 加载完成后自动初始化知识库。"""
        logger.info("[NarakaTutor] 插件加载中，检查知识库状态...")
        if not self.vector_store.is_ready():
            logger.error("[NarakaTutor] 向量库未就绪，请检查依赖安装。")
            return
        if self.vector_store.collection.count() == 0:
            logger.info("[NarakaTutor] 向量库为空，开始从 materials 构建知识库...")
            await self._rebuild_knowledge_base()
        else:
            logger.info(f"[NarakaTutor] 知识库已存在，共 {self.vector_store.collection.count()} 条记录。")

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """
        拦截 LLM 请求：当检测到 @机器人 且问题涉及永劫无间时，
        从向量库检索相关文本并注入 system_prompt。
        """
        if not self.vector_store.is_ready():
            return

        # 1. 判断是否 @ 了当前机器人
        is_at_me = False
        try:
            for comp in event.message_obj.message:
                if isinstance(comp, At) and str(comp.qq) == str(event.message_obj.self_id):
                    is_at_me = True
                    break
        except Exception:
            pass

        if not is_at_me:
            return

        # 2. 提取用户问题（去掉 @ 内容）
        raw_text = event.message_str or ""
        question = re.sub(r'@\d+', '', raw_text).strip()
        if not question:
            return

        # 3. 触发关键词检查
        if not self._should_trigger(question):
            return

        # 4. 向量检索
        contexts = self.vector_store.search(query=question, top_k=self.top_k)
        if not contexts:
            return

        # 5. 构建 RAG 提示并注入
        rag_text = self._build_rag_prompt(contexts, question)
        original_system_prompt = req.system_prompt or ""
        req.system_prompt = original_system_prompt + rag_text
        logger.debug(f"[NarakaTutor] 已为问题注入 {len(contexts)} 条上下文。")

    @filter.command("naraka_reload")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def naraka_reload(self, event: AstrMessageEvent):
        """管理员命令：手动重建永劫无间知识库。"""
        yield event.plain_result("[NarakaTutor] 开始重建知识库，请稍候...")
        success, msg = await self._rebuild_knowledge_base()
        if success:
            yield event.plain_result(f"[NarakaTutor] 重建完成！{msg}")
        else:
            yield event.plain_result(f"[NarakaTutor] 重建失败：{msg}")

    @filter.command("naraka_status")
    async def naraka_status(self, event: AstrMessageEvent):
        """查看知识库状态。"""
        if not self.vector_store.is_ready():
            yield event.plain_result("[NarakaTutor] 向量库未就绪，请检查 chromadb 是否正确安装。")
            return
        count = self.vector_store.collection.count()
        pdf_files = [f for f in os.listdir(self.materials_dir) if f.lower().endswith(".pdf")]
        yield event.plain_result(
            f"[NarakaTutor] 状态:\n"
            f"- PDF 文件数: {len(pdf_files)}\n"
            f"- 向量记录数: {count}\n"
            f"- 触发关键词数: {len(self.trigger_keywords)}\n"
            f"- Top-K 检索: {self.top_k}"
        )

    def _should_trigger(self, text: str) -> bool:
        """检查文本是否包含配置的触发关键词。"""
        if not self.trigger_keywords:
            return True
        text_lower = text.lower()
        for kw in self.trigger_keywords:
            if str(kw).lower() in text_lower:
                return True
        return False

    def _build_rag_prompt(self, contexts: list, question: str) -> str:
        """将检索结果格式化为 system_prompt 追加内容。"""
        context_str = "\n\n---\n\n".join(
            [f"[来源: {c['source']} 第 {c['page']} 页]\n{c['text']}" for c in contexts]
        )
        template = self.system_prompt_template
        if not template:
            template = (
                "\n\n[系统提示：用户正在询问永劫无间相关问题。"
                "请严格依据下方的教学材料进行回答，保持准确、简洁。"
                "如果材料中未包含足够信息，请明确告知用户。]\n\n"
                "相关材料：\n{context}\n\n"
                "用户问题：{question}\n"
            )
        return template.format(context=context_str, question=question)

    async def _rebuild_knowledge_base(self) -> tuple:
        """重新解析所有 PDF 并填充向量库。"""
        try:
            self.vector_store.clear()
            chunks = self.pdf_parser.parse_directory(self.materials_dir)
            if not chunks:
                return False, "未在 materials/ 目录下找到可解析的 PDF 文件。"
            self.vector_store.add_chunks(chunks)
            return True, f"共解析 {len(chunks)} 个文本块。"
        except Exception as e:
            logger.error(f"[NarakaTutor] 重建知识库异常: {e}")
            return False, str(e)
