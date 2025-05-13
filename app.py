import os
import json
import faiss
import numpy as np
import traceback
import logging
import time
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

API_KEY = "sk-SacBxsdMwkWAJNTE6dF2F9682c8941EaBf5c7541D2Ff414b"
API_BASE = "https://maas-api.cn-huabei-1.xf-yun.com/v1"
LORA_ID = "1908101547974098944"
INDEX_PATH = "flood_index.bin"
METADATA_PATH = "flood_metadata.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 

def build_vector_db(document_path):
    try:
        logger.info(f"开始构建向量数据库，使用文档: {document_path}")
        
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
        logger.info(f"文档分割完成，共 {len(texts)} 个片段")

        model = SentenceTransformer(EMBEDDING_MODEL)
        embeddings = model.encode(texts, convert_to_numpy=True)
        logger.info("文本编码完成")

        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        faiss.normalize_L2(embeddings)
        index.add(embeddings)

        faiss.write_index(index, INDEX_PATH)
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump({"texts": texts}, f, ensure_ascii=False)
        logger.info("向量数据库构建完成")
        
    except Exception as e:
        logger.error(f"构建向量数据库时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        raise

class FloodRAG:
    def __init__(self):
        try:
            logger.info("初始化 FloodRAG")
            self.index = faiss.read_index(INDEX_PATH)
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                self.texts = json.load(f)["texts"]
            self.embedder = SentenceTransformer(EMBEDDING_MODEL)
            
            self.client = OpenAI(
                api_key=API_KEY,
                base_url=API_BASE,
                timeout=30.0
            )
            logger.info("FloodRAG 初始化完成")
            
        except Exception as e:
            logger.error(f"初始化 FloodRAG 时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            raise

        self.base_prompt = """你是一个洪涝灾害应急响应专家，请基于以下参考资料回答问题：

参考资料：
{context}

问题：{question}

请提供专业、准确的建议，并在回答末尾标注使用的参考资料编号。
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def _call_api(self, messages):
        try:
            logger.debug("发送请求到 API")
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
            logger.debug("收到 API 响应")
            return response
        except Exception as e:
            logger.error(f"API 调用失败: {str(e)}")
            raise

    def _retrieve_context(self, query, top_k=3):
        try:
            logger.debug(f"检索相关上下文，查询: {query}")
            query_embed = self.embedder.encode([query])
            faiss.normalize_L2(query_embed)
            scores, indices = self.index.search(query_embed, top_k)
            
            results = [
                {
                    "text": self.texts[idx],
                    "score": float(score),
                    "index": idx
                }
                for score, idx in zip(scores[0], indices[0])
            ]
            logger.debug(f"找到 {len(results)} 个相关片段")
            return results
            
        except Exception as e:
            logger.error(f"检索上下文时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _format_context(self, context_results):
        try:
            logger.debug("格式化上下文")
            formatted = "\n\n".join([
                f"[参考资料{i + 1}] {res['text']}"
                for i, res in enumerate(context_results)
            ])
            logger.debug("上下文格式化完成")
            return formatted
        except Exception as e:
            logger.error(f"格式化上下文时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def query(self, question, top_k=3):
        try:
            logger.info(f"处理用户问题: {question}")
            
            context_results = self._retrieve_context(question, top_k)
            formatted_context = self._format_context(context_results)
            
            messages = [
                {"role": "user", "content": self.base_prompt.format(
                    context=formatted_context,
                    question=question
                )}
            ]
            
            try:
                response = self._call_api(messages)
                
                if response and hasattr(response.choices[0], 'message'):
                    logger.info("成功生成回答")
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
                    logger.error("API 返回异常响应")
                    return {
                        "answer": "API 返回结果异常，请稍后重试",
                        "contexts": context_results,
                        "status": "error"
                    }

            except Exception as api_error:
                logger.error(f"API 调用失败: {str(api_error)}")
                return {
                    "answer": "抱歉，服务暂时不可用，请稍后重试",
                    "contexts": [],
                    "status": "error"
                }

        except Exception as e:
            logger.error(f"查询处理时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                "answer": f"查询发生错误，请稍后重试",
                "contexts": [],
                "status": "error"
            }

rag = FloodRAG()

@app.route('/query', methods=['POST'])
def query():
    try:
        logger.info("收到新的查询请求")
        if not request.is_json:
            logger.error("请求Content-Type不是application/json")
            return jsonify({
                "answer": "请求格式错误，需要JSON格式",
                "contexts": [],
                "status": "error"
            }), 400
            
        data = request.get_json()
        if 'question' not in data:
            logger.error("请求中缺少question字段")
            return jsonify({
                "answer": "请求中缺少问题内容",
                "contexts": [],
                "status": "error"
            }), 400
            
        question = data['question']
        logger.info(f"处理问题: {question}")
        
        result = rag.query(question)
        logger.info(f"返回结果: {result}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "answer": f"服务器发生错误: {str(e)}",
            "contexts": [],
            "status": "error"
        }), 500

if __name__ == "__main__":
    try:
        if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
            logger.info("正在构建向量数据库...")
            build_vector_db("应急预案 1.txt")
            logger.info("向量数据库构建完成")

        logger.info("启动Flask服务器...")
        app.run(host='0.0.0.0', port=5000, debug=True)
        
    except Exception as e:
        logger.error(f"程序启动时发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        raise
