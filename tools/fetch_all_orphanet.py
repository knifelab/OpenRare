import os
import json
import time
import requests

# 1. 强制使用以当前文件所在目录为基准的绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "diseases")
INDEX_FILE = os.path.join(BASE_DIR, "data", "index.json")
CACHE_FILE = os.path.join(BASE_DIR, "tools", "orphadata_en.json")

# 确保目录必定存在
os.makedirs(DATA_DIR, exist_ok=True)

class OrphanetFullPipeline:
    def __init__(self):
        self.index_data = []

    def get_master_disease_list(self):
        print(f"📁 缓存文件读取路径: {CACHE_FILE}")
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"📦 成功读取本地缓存，共 {len(data)} 条记录")
                    return data
            except Exception as e:
                print(f"⚠️ 读取缓存失败: {e}")
        return []

    def fetch_clinical_trials(self, disease_name):
        pipelines = []
        ct_url = f"https://clinicaltrials.gov/api/v2/studies?query.cond={disease_name}&pageSize=2"
        try:
            res = requests.get(ct_url, timeout=3)
            if res.status_code == 200:
                studies = res.json().get("studies", [])
                for study in studies:
                    protocol = study.get("protocolSection", {})
                    design = protocol.get("designModule", {})
                    phases = design.get("phases", ["Phase N/A"])
                    interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
                    drug_name = interventions[0].get("name") if interventions else "未透露新药"
                    
                    pipelines.append({
                        "drug_or_therapy": drug_name,
                        "target_or_mechanism": (protocol.get("descriptionModule", {}).get("briefSummary", "")[:60] + "...") if protocol.get("descriptionModule", {}).get("briefSummary") else "暂无简介",
                        "phase": phases[0].replace("PHASE", "Phase ") if phases else "Phase N/A",
                        "status": protocol.get("statusModule", {}).get("overallStatus", "Recruiting"),
                        "clinical_trials_id": protocol.get("identificationModule", {}).get("nctId", ""),
                        "last_updated": time.strftime("%Y-%m-%d")
                    })
        except Exception:
            pass
        return pipelines

    def run_batch_process(self, max_limit=500):
        raw_diseases = self.get_master_disease_list()
        if not raw_diseases:
            print("❌ 未找到数据，请先运行 python tools/build_local_dataset.py")
            return

        print(f"🎯 目标写入目录: {DATA_DIR}")
        print(f"📊 开始处理，最大上限: {max_limit} 种罕见病...\n")

        count = 0
        for item in raw_diseases:
            if count >= max_limit:
                break

            name_en = item.get("Name") or item.get("name_en") or ""
            orpha = item.get("OrphaCode") or item.get("orpha_code") or ""
            if not name_en:
                continue

            orpha_code = f"ORPHA{orpha}" if not str(orpha).startswith("ORPHA") else str(orpha)
            disease_id = f"OR-{count+1:05d}"
            filename = f"{disease_id}.json"
            filepath = os.path.join(DATA_DIR, filename)

            # 增量处理：如已存在则跳过 API 请求
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    disease_obj = json.load(f)
            else:
                pipelines = self.fetch_clinical_trials(name_en)
                disease_obj = {
                    "id": disease_id,
                    "name_cn": item.get("Name_CN", name_en),
                    "name_en": name_en,
                    "aliases": [],
                    "icd_11": item.get("ICD11", item.get("icd_11", "")),
                    "orpha_code": orpha_code,
                    "overview": f"{name_en} 是收录于 Orphanet 数据库的罕见病词条 (编码: {orpha_code})。",
                    "pipelines": pipelines
                }
                
                # 强制实时落盘 (os.flush)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(disease_obj, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())

            self.index_data.append({
                "id": disease_obj["id"],
                "name_cn": disease_obj["name_cn"],
                "name_en": disease_obj["name_en"],
                "icd_11": disease_obj["icd_11"],
                "orpha_code": disease_obj["orpha_code"],
                "pipeline_count": len(disease_obj["pipelines"]),
                "file": filename
            })

            count += 1
            if count % 10 == 0 or count == len(raw_diseases):
                print(f"✅ 成功写入文件: {filename} (进度: {count}/{max_limit})")

        # 写入主索引 index.json
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self.index_data, f, ensure_ascii=False, indent=2)

        print(f"\n🎉 全部完成！文件已实时更新至: {DATA_DIR}")

if __name__ == "__main__":
    runner = OrphanetFullPipeline()
    runner.run_batch_process(max_limit=7000)