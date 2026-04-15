import os
from astrbot.api import logger

try:
    import chromadb
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
except Exception as e:
    chromadb = None
    DefaultEmbeddingFunction = None
    logger.error(f"[NarakaTutor] 无法导入 chromadb: {e}")


class VectorStore:
    """基于 ChromaDB 的轻量级向量存储。使用默认的 ONNX EmbeddingFunction，无需 PyTorch。"""

    def __init__(self, persist_directory: str):
        self.persist_directory = persist_directory
        self.client = None
        self.collection = None
        self.embedding_function = None
        self._init_db()

    def _init_db(self):
        if chromadb is None:
            logger.error("[NarakaTutor] chromadb 未安装，向量库初始化失败。")
            return
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.embedding_function = DefaultEmbeddingFunction()
            self.collection = self.client.get_or_create_collection(
                name="naraka_knowledge",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"[NarakaTutor] 向量库已加载: {self.persist_directory}")
        except Exception as e:
            logger.error(f"[NarakaTutor] 向量库初始化异常: {e}")

    def is_ready(self) -> bool:
        return self.collection is not None

    def add_chunks(self, chunks: list):
        """
        chunks: list of dict with keys: source, page, chunk_index, text
        """
        if not self.is_ready() or not chunks:
            return
        try:
            ids = []
            documents = []
            metadatas = []
            for chunk in chunks:
                cid = f"{chunk['source']}_p{chunk['page']}_c{chunk['chunk_index']}"
                ids.append(cid)
                documents.append(chunk["text"])
                metadatas.append({
                    "source": chunk["source"],
                    "page": chunk["page"],
                })
            # 分批添加避免单次过大
            batch_size = 128
            for i in range(0, len(ids), batch_size):
                self.collection.add(
                    ids=ids[i:i + batch_size],
                    documents=documents[i:i + batch_size],
                    metadatas=metadatas[i:i + batch_size],
                )
            logger.info(f"[NarakaTutor] 已向向量库添加 {len(chunks)} 个文本块。")
        except Exception as e:
            logger.error(f"[NarakaTutor] 添加文本块失败: {e}")

    def clear(self):
        if not self.is_ready():
            return
        try:
            self.client.delete_collection(name="naraka_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="naraka_knowledge",
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("[NarakaTutor] 向量库已清空。")
        except Exception as e:
            logger.error(f"[NarakaTutor] 清空向量库失败: {e}")

    def search(self, query: str, top_k: int = 5) -> list:
        """
        返回相关文本块列表，每个元素为 dict: {"text": str, "source": str, "page": int, "distance": float}
        """
        if not self.is_ready():
            return []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count() or 1),
                include=["documents", "metadatas", "distances"],
            )
            output = []
            docs = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            for doc, meta, dist in zip(docs, metas, distances):
                output.append({
                    "text": doc,
                    "source": meta.get("source", ""),
                    "page": meta.get("page", 0),
                    "distance": dist,
                })
            return output
        except Exception as e:
            logger.error(f"[NarakaTutor] 向量检索失败: {e}")
            return []
