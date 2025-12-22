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

                # 增强文档元数据
                for doc in documents:
                    self._enhance_metadata(doc)

                self.documents = documents
                return documents

            except Exception as e:
                logger.warning(f"读取文件 {md_file} 失败: {e}")

    def _enhance_metadata(self, doc: Document):
        """增强文档元数据"""
        file_path = Path(doc.metadata.get("source", ""))
        path_parts = file_path.parts

        # 提取菜品分类
        category_mapping = {
            'meat_dish': '荤菜', 'vegetable_dish': '素菜', 'soup': '汤品',
            'dessert': '甜品', 'breakfast': '早餐', 'staple': '主食',
            'aquatic': '水产', 'condiment': '调料', 'drink': '饮品'
        }

        # 从文件路径推断分类
        doc.metadata["category"] = "其他"
        for key, value in category_mapping.items():
            if key in file_path.parts:
                doc.metadata["category"] = value
                break

        # 提取菜品名称
        doc.metadata["dish_name"] = file_path.stem

        # 分析难度等级
        content = doc.page_content
        if '★★★★★' in content:
            doc.metadata['difficulty'] = '非常困难'
        elif '★★★★' in content:
            doc.metadata['difficulty'] = '困难'
        elif '★★★' in content:
            doc.metadata['difficulty'] = '中等'
        elif '★★' in content:
            doc.metadata['difficulty'] = '简单'
        elif '★' in content:
            doc.metadata['difficulty'] = '非常简单'
        else:
            doc.metadata['difficulty'] = '未知'

    def chunk_document(self) -> List[Document]:
        """
        Markdown 结构感知分块

        Returns:
            分块后的文档列表
        """
        logger.info("正在进行Markdown结构感知分块...")

        if not self.documents:
            raise ValueError("请先加载文档")

        # 使用Markdown标题分割器
        chunks = self._markdown_header_split()

        # 为每个chunk添加基础元数据
        for i, chunk in enumerate(chunks):
            if 'chunk_id' not in chunk.metadata:
                # 如果没有chunk_id（比如分割失败的情况），则生成一个
                chunk.metadata['chunk_id'] = str(uuid.uuid4())
            chunk.metadata['batch_index'] = i  # 在当前批次中的索引
            chunk.metadata['chunk_size'] = len(chunk.page_content)

        self.chunks = chunks
        logger.info(f"Markdown分块完成，共生成 {len(chunks)} 个chunk")
        return chunks

    def _markdown_header_split(self)-> List[Document]:
        """
        使用Markdown标题分割器进行结构化分割

        Returns:
            按标题结构分割的文档列表
        """
        # 定义要分割的标题层级
        headers_to_split_on = [
            ("#", "主标题"),      # 菜品名称
            ("##", "二级标题"),   # 必备原料、计算、操作等
            ("###", "三级标题")   # 简易版本、复杂版本等
        ]
        # 创建Markdown分割器
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False # 保留标题，便于理解上下文
        )