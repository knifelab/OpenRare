import os
import json
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISEASES_DIR = os.path.join(BASE_DIR, 'data', 'diseases')

# 模拟研发管线阶段与药物
PHASES = ["Phase I", "Phase II", "Phase III", "Preclinical"]
DRUG_TYPES = ["AAV Gene Therapy", "mRNA Vaccine", "Small Molecule", "Monoclonal Antibody", "ASO"]

def inject_mock_pipelines():
    if not os.path.exists(DISEASES_DIR):
        print("错误: 找不到疾病目录")
        return

    files = [f for f in os.listdir(DISEASES_DIR) if f.endswith('.json')]
    
    for idx, file_name in enumerate(files):
        file_path = os.path.join(DISEASES_DIR, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 前 50 种疾病赋予随机管线数据，便于测试 Top 10 和统计看板
        if idx < 50:
            pipeline_count = random.randint(1, 8)
            pipelines = []
            for p_idx in range(pipeline_count):
                pipelines.append({
                    "id": f"NCT{random.randint(10000000, 99999999)}",
                    "title": f"Study of {data.get('name_en', 'Treatment')} Pipeline {p_idx + 1}",
                    "phase": random.choice(PHASES),
                    "type": random.choice(DRUG_TYPES),
                    "sponsor": "Global Pharma Corp"
                })
            data["pipelines"] = pipelines
        else:
            data["pipelines"] = []

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print("已成功为疾病数据补全管线信息！")

if __name__ == '__main__':
    inject_mock_pipelines()