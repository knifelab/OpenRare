import os
import json

# 目录路径定义
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DISEASES_DIR = os.path.join(DATA_DIR, 'diseases')
INDEX_FILE = os.path.join(DATA_DIR, 'index.json')

def rebuild_index():
    index_data = []
    
    if not os.path.exists(DISEASES_DIR):
        print(f"错误: 找不到疾病目录 {DISEASES_DIR}")
        return

    # 遍历 diseases 目录下的所有子 JSON 文件
    files = [f for f in os.listdir(DISEASES_DIR) if f.endswith('.json')]
    print(f"正在读取 {len(files)} 个疾病详细文件...")

    for file_name in files:
        file_path = os.path.join(DISEASES_DIR, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                detail = json.load(f)
                
                # 兼容不同数据结构的 pipelines 读取逻辑
                pipelines = detail.get('pipelines', [])
                if isinstance(pipelines, list):
                    real_count = len(pipelines)
                elif isinstance(pipelines, int):
                    real_count = pipelines
                else:
                    real_count = 0

                # 提取索引信息
                item = {
                    "id": detail.get("id", ""),
                    "name_cn": detail.get("name_cn", ""),
                    "name_en": detail.get("name_en", ""),
                    "icd_11": detail.get("icd_11", ""),
                    "orpha_code": detail.get("orpha_code", ""),
                    "pipeline_count": real_count,  # 动态获取真实的管线数量
                    "file": file_name
                }
                index_data.append(item)
        except Exception as e:
            print(f"解析文件 {file_name} 失败: {e}")

    # 按 ID 排序保证列表稳定性
    index_data.sort(key=lambda x: x.get("id", ""))

    # 写入 index.json
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print(f"成功更新 {INDEX_FILE}，共处理 {len(index_data)} 条记录！")

if __name__ == '__main__':
    rebuild_index()