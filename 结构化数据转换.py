import os
import pandas as pd
import requests
from time import sleep
API_KEY = "Si7y7u8msNhdwfGwvPKbX7ACopImeQiA"
API_URL = "https://api.mistral.ai/v1/chat/completions"
def read_excel_data(file_path):
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"读取Excel文件失败: {str(e)}")
        exit(1)
def generate_case_prompt(case_data):
    return f"""请将以下结构化洪水数据转换为自然语言案例描述，要求：
    1. 使用正式报告文体
    2. 包含完整时间线
    3. 突出关键数据
    4. 保持段落连贯
    5. 中文输出
    数据：
    - 事件编号：{case_data.get('DisNo.', '')}
    - 灾害分类编码：{case_data.get('Classification Key', '')}
    - 灾害具体类型：{case_data.get('Disaster Subtype', '')}
    - 起始年份：{case_data.get('Start Year', '')}
    - 起始月份：{case_data.get('Start Month', '')}
    - 起始日：{case_data.get('Start Day', '')}
    - 受灾国家：{case_data.get('Country', '')}
    - 发生地点：{case_data.get('Location', '')}
    - 死亡人数：{case_data.get('Total Deaths', '')}
    - 灾害成因：{case_data.get('Origin', '')}
    - 受灾人口：{case_data.get('Total Affected', '')}人
    - 直接经济损失(单位：万美元)：{case_data.get('Total Damage, Adjusted (000 US$)', '')}万美元
"""
def call_mistral_api(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-medium-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3  # 降低随机性
    }
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {str(e)}")
        return None
def save_to_txt(case_descriptions, output_file):
    with open(output_file, 'w', encoding='utf-8') as f:
        for i, desc in enumerate(case_descriptions, 1):
            f.write(f"案例 {i}:\n{desc}\n\n{'=' * 50}\n\n")
def main():
    input_file = "data/flood_cases.xlsx"
    output_file = "flood_cases_report.txt"
    cases = read_excel_data(input_file)
    print(f"成功读取 {len(cases)} 条案例数据")
    results = []
    for idx, case in enumerate(cases, 1):
        print(f"正在处理第 {idx}/{len(cases)} 条案例...")
        prompt = generate_case_prompt(case)
        response = call_mistral_api(prompt)
        if response:
            results.append(response)
            sleep(1)
        else:
            results.append(f"【生成失败】案例 {idx} 生成失败")
    save_to_txt(results, output_file)
    print(f"处理完成，结果已保存至 {output_file}")
if __name__ == "__main__":
    main()