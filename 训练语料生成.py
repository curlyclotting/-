import json
import openai
import faiss
import numpy as np

DEEPSEEK_API_KEY = "sk-210d04c713bf4ce5b23b496dc847f3fe"
INDEX_PATH = "geo_indexq.bin"
METADATA_PATH = "geo_metadataq.json"
OUTPUT_PATH = "training_data11.jsonl"

client = openai.OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
    timeout=30
)

index = faiss.read_index(INDEX_PATH)
with open(METADATA_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)
    all_texts = metadata["texts"]

def generate_qa_pairs(text_chunk, max_questions=2):
    format_example = r'''{
  "text": "根据《国家防汛应急预案》第5.2条规定，Ⅱ级应急响应期间需在事发后6小时内完成危险区群众转移安置，救援队伍应配备不少于3台大功率排水车（≥1000m³/h）和2组应急发电机组",
  "prompt": "请根据防汛应急预案要求说明：①黄金6h阶段群众转移的具体时间要求 ②列出该时段必须配置的排水设备技术参数 ③说明发电机组配置标准",
  "response": "①黄金6h处置要求｜必须在灾情发生后6小时内完成全部危险区群众转移｜②排水设备配置｜大功率排水车≥3台｜单机排水量≥1000m³/h｜③发电机组配置｜柴油发电机组≥2组｜单组功率≥200kW｜依据：《国家防汛物资储备定额》Ⅱ级标准"
}'''
    prompt = f"""
    作为应急管理部认证的培训师，请基于防汛知识库内容生成{max_questions}组训练QA对：
    知识库文本片段：
    {text_chunk}
    严格遵循以下规范：
    1. 问题设计：
       - 必须包含时间阶段标记①黄金6h/②12h/③24h
       - 需明确要求回答防汛流程步骤/资源配置标准/处置技术要点
       - 涉及地理范围限定在：北纬28°-32°，东经114°-122°
    2. 答案规范：
       - 流程类回答使用「阶段标记+处置动作+完成时限」结构
       - 资源配置须标注《定额标准》等级和具体参数
       - 技术方案需包含排水量(m³/h)、沙袋(个/延米)等量化指标
       - 救援力量注明武警/消防/社会救援队建制单位
    3. 格式要求：
       - 使用竖线分隔不同信息模块
       - 数值型参数采用国际标准单位
       - 每个QA对包含3-5个技术要素

    示例参考：
    {format_example}
    """
    max_retries = 3
    backoff_factor = 1.5
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1500,
                stop=["```end"]
            )

            raw_content = response.choices[0].message.content
            print("原始响应：\n", raw_content)

            json_str = raw_content.split("```json")[1].split("```")[0].strip()
            parsed = json.loads(json_str)

            required_keys = {"text", "prompt", "response"}
            if not required_keys.issubset(parsed.keys()):
                raise ValueError("缺少必要字段")

            coord_part = parsed["response"].split("；")[0]
            lat = float(coord_part.split("北纬")[1].split("°")[0])
            lng = float(coord_part.split("东经")[1].split("°")[0])
            if not (28 <= lat <= 32) or not (114 <= lng <= 122):
                raise ValueError("坐标超出限定范围")

            return [parsed]


        except Exception as e:
            print(f"API错误: {str(e)}")
            break
    return []

def generate_dataset(num_samples=2):
    dataset = []
    if not all_texts:
        raise ValueError("数据库中没有可用文本！")

    rand_indices = np.random.choice(
        len(all_texts),
        min(num_samples, len(all_texts)),
        replace=False
    )
    x=0
    for idx in rand_indices:
        print("训练到第个",end=" ")
        x+=1
        print(x)
        text = all_texts[int(idx)]
        print(f"\n处理文本 {idx}: {text[:50]}...")

        qas = generate_qa_pairs(text)
        if qas:
            dataset.append({
                "text": text,
                "prompt": qas[0]["prompt"],
                "response": qas[0]["response"],
                "metadata": {
                    "source_index": int(idx),
                    "validation": {
                        "has_coordinates": "北纬" in qas[0]["response"],
                        "has_stages": all(t in qas[0]["response"]
                                       for t in ["6小时", "12小时", "24小时"])
                    }
                }
            })
    return dataset

def save_dataset(dataset):
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    try:
        dataset = generate_dataset(num_samples=2)
        if dataset:
            save_dataset(dataset)
            print(f"\n生成完成！保存至 {OUTPUT_PATH}，共 {len(dataset)} 条数据")
            print("\n示例数据：")
            print(json.dumps(dataset[0], indent=2, ensure_ascii=False))
        else:
            print("错误：未生成任何有效数据")
    except Exception as e:
        print(f"程序运行异常: {str(e)}")