# 数据准备模块
import logging
from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from pathlib import Path
import uuid
import hashlib


logger = logging.getLogger(__name__)


class DataPreparation:
    """数据准备模块 - 负责数据加载、清洗和预处理"""

    def __init__(self, data_path: str):
        self.data_path = data_path
        self.documents: List[Document] = []  # 父文档（完整食谱）
        self.chunks: List[Document] = []  # 子文档（按标题分割的小块）
        self.parent_child_map: Dict[str, str] = {}  # 子块ID -> 父文档ID的映射

    def load_document(self) -> List[Document]:
        """
        加载文档数据

        Returns:
            加载的文档列表
        """
        logger.info(f"正在从 {self.data_path} 加载文档...")
        documents = []
        data_path_obj = Path(self.data_path)

        for md_file in data_path_obj.rglob("*.md"):
            try:
                # 读取文件内容，保持Markdown格式
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 为每个父文档分配确定性的唯一ID（基于数据根目录的相对路径）
                try:
                    data_root = Path(self.data_path).resolve()
                    relative_path = (
                        Path(md_file).resolve().relative_to(data_root).as_posix()
                    )
                except Exception:
                    relative_path = Path(md_file).as_posix()
                parent_id = hashlib.md5(relative_path.encode("utf-8")).hexdigest()
                # 创建Document对象
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(md_file),
                        "parent_id": parent_id,
                        "doc_type": "parent",  # 标记为父文档
                    },
                )
                documents.append(doc)

            except Exception as e:
                logger.warning(f"读取文件 {md_file} 失败: {e}")
