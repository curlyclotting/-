import os
import json
import faiss
import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from flask import Flask, request, jsonify
from flask_cors import CORS
 

API_KEY = "d"
API_BASE = "https://maas-api.cn-huabei-1.xf-yun.com/v1"
LORA_ID = "1908101547974098944"
INDEX_PATH = "flood_index.bin"
METADATA_PATH = "flood_metadata.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


app = Flask(__name__)
CORS(app) 

def build_vector_db(document_path):

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=50,
        length_function=len,
        is_separator_regex=False,
    )


    loader = TextLoader(document_path, encoding="utf-8")
    docs = loader.load()
    all_text = "".join([doc.page_content for doc in docs])
    split_docs = text_splitter.create_documents([all_text])

    texts = [doc.page_content for doc in split_docs]


    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(texts, convert_to_numpy=True)


    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    faiss.normalize_L2(embeddings)
    index.add(embeddings)


    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump({"texts": texts}, f, ensure_ascii=False)


class FloodRAG:
    def __init__(self):

        self.index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            self.texts = json.load(f)["texts"]
        self.embedder = SentenceTransformer(EMBEDDING_MODEL)


        self.client = OpenAI(api_key=API_KEY, base_url=API_BASE)


        self.base_prompt = """你是一个洪涝灾害应急响应专家，请基于以下参考资料回答问题：

参考资料：
{context}

问题：{question}

请提供专业、准确的建议，并在回答末尾标注使用的参考资料编号。
"""

    def _retrieve_context(self, query, top_k=3):

        query_embed = self.embedder.encode([query])
        faiss.normalize_L2(query_embed)
        scores, indices = self.index.search(query_embed, top_k)

        return [
            {
                "text": self.texts[idx],
                "score": float(score),
                "index": idx
            }
            for score, idx in zip(scores[0], indices[0])
        ]

    def _format_context(self, context_results):

        return "\n\n".join([
            f"[参考资料{i + 1}] {res['text']}"
            for i, res in enumerate(context_results)
        ])

    def query(self, question, top_k=3):

        try:

            context_results = self._retrieve_context(question, top_k)
            formatted_context = self._format_context(context_results)


            messages = [
                {"role": "user", "content": self.base_prompt.format(
                    context=formatted_context,
                    question=question
                )}
            ]


            response = self.client.chat.completions.create(
                model="xdeepseekr1qwen32b",
                messages=messages,
                stream=False,
                temperature=0.7,
                max_tokens=4096,
                extra_headers={"lora_id": LORA_ID},
                stream_options={"include_usage": True},
                extra_body={"show_ref_label": True}
            )

            if response and hasattr(response.choices[0], 'message'):
                processed_contexts = [
                {
                    "text": ctx["text"],
                    "score": ctx["score"],
                    "index": int(ctx["index"])  
                }
                for ctx in context_results
            ]
                return {
                    "answer": response.choices[0].message.content,
                    "contexts": processed_contexts,
                    "status": "success"
                }
            else:
                return {
                    "answer": "API 返回结果异常",
                    "contexts": context_results,
                    "status": "error"
                }

        except Exception as e:
            return {
                "answer": f"查询发生错误: {str(e)}",
                "contexts": [],
                "status": "error"
            }


rag = FloodRAG()


@app.route('/query', methods=['POST'])
def query():
    try:
        data = request.get_json()
        question = data['question']
        print(f"收到问题: {question}")  
        result = rag.query(question)
        print(f"返回结果: {result}")  
        return jsonify(result)
    except Exception as e:
        print(f"发生错误: {e}")  
        return jsonify({"answer": "服务器发生错误", "contexts": [], "status": "error"})

if __name__ == "__main__":

    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        print("正在构建向量数据库...")
        build_vector_db("应急预案 1.txt") 
        print("向量数据库构建完成。")

    app.run(host='0.0.0.0', port=5000, debug=True)
