"""
RAG 知识库：Chroma 持久化向量库 + 本地确定性 embedding。

为什么不用在线 embedding 模型？
- 零外网依赖：不下载 HuggingFace/ONNX 模型，clone 下来即可跑；
- 可复现：相同文本永远得到相同向量，AI 评测的召回结果稳定可断言；
- 中文友好：用字符 bigram + 词片段哈希，对中文短句有明显区分度。

生产可一行切换到 OpenAI/BGE embedding，见 docs 说明。
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import chromadb

from . import config

_client: chromadb.PersistentClient | None = None
_collection = None


def _tokenize(text: str) -> list[str]:
    """中文按字符 bigram，英文/数字按词，混合切片。"""
    text = text.lower().strip()
    tokens: list[str] = []
    # 英文单词与数字
    tokens.extend(re.findall(r"[a-z0-9_]+", text))
    # 中文字符 unigram + bigram
    han = "".join(re.findall(r"[\u4e00-\u9fff]", text))
    tokens.extend(list(han))
    tokens.extend(han[i:i + 2] for i in range(len(han) - 1))
    return tokens or [text]


def embed(text: str) -> list[float]:
    """确定性哈希向量：token -> 维度下标，带符号与权重，最后 L2 归一化。"""
    vec = [0.0] * config.EMBED_DIM
    for tok in _tokenize(text):
        h = hashlib.md5(tok.encode("utf-8")).digest()
        idx = int.from_bytes(h[:4], "big") % config.EMBED_DIM
        sign = 1.0 if h[4] % 2 == 0 else -1.0
        vec[idx] += sign * 1.0
        # 二次映射，降低碰撞影响
        idx2 = int.from_bytes(h[4:8], "big") % config.EMBED_DIM
        vec[idx2] += sign * 0.5
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def collection():
    global _client, _collection
    if _collection is None:
        Path(config.CHROMA_DIR).mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=config.CHROMA_DIR)
        _collection = _client.get_or_create_collection(
            name=config.COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def count() -> int:
    try:
        return collection().count()
    except Exception:
        return 0


def add_document(title: str, content: str) -> dict[str, Any]:
    doc_id = hashlib.md5((title + "\n" + content).encode("utf-8")).hexdigest()[:16]
    col = collection()
    # 同标题先清掉旧分块，避免文档内容更新后残留过期 chunk
    delete_document(title)
    # 长文本按段切分，模拟真实 RAG 的 chunking
    chunks = [c.strip() for c in re.split(r"\n\s*\n|(?<=。)", content) if len(c.strip()) >= 8]
    if not chunks:
        chunks = [content]
    ids, docs, metas, embs = [], [], [], []
    for i, chunk in enumerate(chunks):
        ids.append(f"{doc_id}-{i}")
        full = f"{title}\n{chunk}"
        docs.append(full)
        metas.append({"title": title, "chunk": i})
        embs.append(embed(full))
    col.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embs)
    return {"doc_id": doc_id, "chunks": len(chunks), "total_docs": col.count()}


def delete_document(title: str) -> int:
    """按标题删除该文档的全部 chunk（Chroma 按 metadata 过滤），返回删除条数。"""
    col = collection()
    try:
        got = col.get(where={"title": title}, include=[])
        ids = got.get("ids") or []
        if ids:
            col.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def doc_chunks(title: str) -> list[dict[str, Any]]:
    """列出某篇文档在向量库里的全部分块（知识库页面的「分块预览」）。"""
    col = collection()
    try:
        got = col.get(where={"title": title}, include=["documents", "metadatas"])
    except Exception:
        return []
    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    out = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        chunk = (meta or {}).get("chunk", i)
        # 存储时是「标题 + 换行 + 正文」，展示时把标题前缀去掉
        text = doc.split("\n", 1)[1] if "\n" in doc else doc
        out.append({"index": chunk, "text": text, "chars": len(text)})
    return sorted(out, key=lambda x: x["index"])


def search_detail(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    """召回测试用：比 search() 多返回 分块序号 / 命中片段长度，便于讲「召回质量」。"""
    k = top_k or config.RAG_TOP_K
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[embed(query)], n_results=min(k, col.count()))
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for doc, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        out.append({"title": meta.get("title", ""), "chunk": meta.get("chunk", 0),
                    "score": round(1.0 - float(dist), 4),
                    "text": doc.split("\n", 1)[1] if "\n" in doc else doc,
                    "chars": len(doc)})
    return out


def search(query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    k = top_k or config.RAG_TOP_K
    col = collection()
    if col.count() == 0:
        return []
    res = col.query(query_embeddings=[embed(query)], n_results=min(k, col.count()))
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for doc, meta, dist in zip(docs, metas, dists):
        out.append({
            "text": doc,
            "title": (meta or {}).get("title", ""),
            "score": round(1.0 - float(dist), 4),
        })
    return out


def format_hits(hits: list[dict[str, Any]]) -> str:
    if not hits:
        return "知识库未检索到相关内容。"
    return "\n".join(f"[{i+1}] {h['title']} (相似度{h['score']}): {h['text']}"
                     for i, h in enumerate(hits))


def load_seed_docs() -> int:
    """启动时按 knowledge/docs 重新灌入示例语料（同标题覆盖，保证与文件一致）。"""
    files = sorted(config.KNOWLEDGE_DIR.glob("*.md"))
    for p in files:
        text = p.read_text(encoding="utf-8")
        first = text.splitlines()[0].lstrip("# ").strip() if text else p.stem
        add_document(first, text)
    return len(files)
