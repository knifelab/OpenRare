import os
import json
import urllib.request
import urllib.parse
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISEASES_DIR = os.path.join(BASE_DIR, 'data', 'diseases')

def fetch_clinical_trials(disease_name):
    """通过 ClinicalTrials.gov API v2 检索疾病最新的临床试验数据"""
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.cond': disease_name,
        'pageSize': 5,  # 每次获取最新 5 条
        'format': 'json'
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    headers = {'User-Agent': 'Mozilla/5.0 OpenRarePlatform/1.0'}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                studies = data.get('studies', [])
                
                pipelines = []
                for study in studies:
                    protocol = study.get('protocolSection', {})
                    
                    # 提取 NCT ID
                    nct_id = protocol.get('identificationModule', {}).get('nctId', '')
                    # 提取标题
                    title = protocol.get('identificationModule', {}).get('briefTitle', '')
                    # 提取分期 (Phase)
                    phases = protocol.get('designModule', {}).get('phases', ['N/A'])
                    phase_str = phases[0] if phases else 'N/A'
                    # 提取申办方
                    sponsor = protocol.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name', 'Unknown')
                    
                    pipelines.append({
                        "id": nct_id,
                        "title": title,
                        "phase": phase_str,
                        "sponsor": sponsor
                    })
                return pipelines
    except Exception as e:
        print(f"抓取 {disease_name} 失败: {e}")
    return []

def sync_data():
    if not os.path.exists(DISEASES_DIR):
        print("错误: 找不到疾病目录")
        return

    # 获取前 20 种疾病进行自动更新（根据接口频次控制）
    files = [f for f in os.listdir(DISEASES_DIR) if f.endswith('.json')][:20]
    
    print(f"开始同步前 {len(files)} 种罕见病的最新临床试验...")
    for file_name in files:
        file_path = os.path.join(DISEASES_DIR, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            disease_data = json.load(f)
        
        disease_name = disease_data.get('name_en')
        if disease_name:
            print(f"正在更新: {disease_name}")
            new_pipelines = fetch_clinical_trials(disease_name)
            
            # 如果成功获取到了真实数据，则更新字段
            if new_pipelines:
                disease_data['pipelines'] = new_pipelines
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(disease_data, f, ensure_ascii=False, indent=2)
            
            # 避免请求过于频繁，休眠 1 秒
            time.sleep(1)

    print("数据同步完成！")

if __name__ == '__main__':
    sync_data()