import os
import json
import time
import requests
from typing import List, Optional
from pydantic import BaseModel, Field

# 1. 定义 OpenRare 标准数据结构（确保风格 100% 一致）
class Pipeline(BaseModel):
    drug_or_therapy: str = Field(..., description="药物或疗法名称")
    target_or_mechanism: str = Field(..., description="靶点或作用机制")
    phase: str = Field(..., description="临床阶段 (Phase 1/2/3/Approved)")
    status: str = Field("Recruiting", description="招募状态/审批状态")
    clinical_trials_id: str = Field("", description="NCT编号")
    last_updated: str = Field("", description="更新日期")

class RareDisease(BaseModel):
    id: str = Field(..., description="OpenRare唯一编号，如 OR-00003")
    name_cn: str = Field(..., description="中文名称")
    name_en: str = Field(..., description="英文名称")
    aliases: List[str] = Field(default_factory=list, description="疾病别名")
    icd_11: str = Field("", description="ICD-11编码")
    orpha_code: str = Field("", description="Orphanet编码")
    overview: str = Field("", description="疾病简介")
    pipelines: List[Pipeline] = Field(default_factory=list, description="研发管线列表")

# 2. 批量生成与去重工具类
class DiseasePipelineFetcher:
    def __init__(self, data_dir="../data/diseases"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.existing_orpha_codes = set()
        self.existing_ids = set()
        self.current_max_id = 0
        self._scan_existing_files()

    def _scan_existing_files(self):
        """扫描现有文件夹，提取已有的 ID 和 ORPHA Code 避免重复"""
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            if "orpha_code" in data and data["orpha_code"]:
                                self.existing_orpha_codes.add(data["orpha_code"])
                            if "id" in data and data["id"].startswith("OR-"):
                                try:
                                    num = int(data["id"].split("-")[1])
                                    self.existing_ids.add(num)
                                    if num > self.current_max_id:
                                        self.current_max_id = num
                                except ValueError:
                                    pass
                except Exception as e:
                    print(f"⚠️ 读取 {filename} 失败: {e}")
        print(f"✅ 已扫描已有疾病 JSON，最高 ID 序号: OR-{self.current_max_id:05d}，现存 ORPHA 编码数: {len(self.existing_orpha_codes)}")

    def generate_next_id((self) -> str:
        """自动递增生成标准化 ID (如 OR-00003)"""
        self.current_max_id += 1
        return f"OR-{self.current_max_id:05d}"

    def fetch_clinical_trials(self, disease_name_en: str) -> List[Pipeline]:
        """从 ClinicalTrials.gov API 自动拉取该罕见病的临床管线数据"""
        pipelines = []
        url = f"https://clinicaltrials.gov/api/v2/studies?query.cond={disease_name_en}&pageSize=5"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                studies = res.json().get("studies", [])
                for study in studies:
                    protocol = study.get("protocolSection", {})
                    design = protocol.get("designModule", {})
                    phases = design.get("phases", ["Phase N/A"])
                    phase_str = phases[0] if phases else "Phase N/A"
                    
                    interventions = protocol.get("armsInterventionsModule", {}).get("interventions", [])
                    drug_name = interventions[0].get("name") if interventions else "未透露新药"
                    
                    nct_id = protocol.get("identificationModule", {}).get("nctId", "")
                    brief_summary = protocol.get("descriptionModule", {}).get("briefSummary", "暂无描述")
                    
                    pipelines.append(Pipeline(
                        drug_or_therapy=drug_name,
                        target_or_mechanism=brief_summary[:80] + "..." if len(brief_summary) > 80 else brief_summary,
                        phase=phase_str.replace("PHASE", "Phase "),
                        status=protocol.get("statusModule", {}).get("overallStatus", "Recruiting"),
                        clinical_trials_id=nct_id,
                        last_updated=time.strftime("%Y-%m-%d")
                    ))
        except Exception as e:
            print(f"⚠️ 抓取 {disease_name_en} 临床试验失败: {e}")
        return pipelines

    def add_disease_batch(self, disease_list: List[dict]):
        """批量处理疾病清单，生成符合规范的 JSON 文件"""
        for item in disease_list:
            orpha = item.get("orpha_code", "")
            
            # 去重校验：如果 Orphanet 编码已存在，直接跳过
            if orpha and orpha in self.existing_orpha_codes:
                print(f"⏩ 疾病已存在，跳过: {item['name_cn']} ({orpha})")
                continue

            print(f"🔍 正在抓取并处理: {item['name_cn']} ({item['name_en']})...")
            
            # 自动拉取 ClinicalTrials 管线
            pipelines = self.fetch_clinical_trials(item['name_en'])

            # 组装为标准模型
            disease_data = RareDisease(
                id=self.generate_next_id(),
                name_cn=item['name_cn'],
                name_en=item['name_en'],
                aliases=item.get('aliases', []),
                icd_11=item.get('icd_11', ''),
                orpha_code=orpha,
                overview=item.get('overview', ''),
                pipelines=pipelines
            )

            # 生成文件名（小写下划线命名，如 duchenne.json）
            filename = f"{item['name_en'].lower().replace(' ', '_').replace('-', '_')}.json"
            filepath = os.path.join(self.data_dir, filename)

            # 写入 JSON
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(disease_data.dict(), f, ensure_ascii=False, indent=2)

            if orpha:
                self.existing_orpha_codes.add(orpha)
            
            print(f"✨ 成功生成: {filename} (含 {len(pipelines)} 条管线)")
            time.sleep(1) # 友好请求间隔

# 3. 测试批量导入候选罕见病（后续可扩展为直接读取 Excel/CSV 或爬取 Orphanet 全量清单）
if __name__ == "__main__":
    fetcher = DiseasePipelineFetcher(data_dir="../data/diseases")

    # 准备批量导入的目标罕见病清单
    targets = [
        {
            "name_cn": "杜氏肌营养不良症",
            "name_en": "Duchenne Muscular Dystrophy",
            "aliases": ["DMD"],
            "icd_11": "8B60.0",
            "orpha_code": "ORPHA98896",
            "overview": "一种伴性隐性遗传的肌肉变性疾病，主要影响男性，因抗肌萎缩蛋白（Dystrophin）基因突变所致。"
        },
        {
            "name_cn": "亨廷顿舞蹈病",
            "name_en": "Huntington Disease",
            "aliases": ["HD", "亨廷顿病"],
            "icd_11": "8A01.0",
            "orpha_code": "ORPHA399",
            "overview": "一种常染色体显性遗传的神经退行性疾病，由 HTT 基因中 CAG 重复序列异常扩增引起。"
        },
        {
            "name_cn": "法布雷病",
            "name_en": "Fabry Disease",
            "aliases": ["Fabry病"],
            "icd_11": "5C56.1",
            "orpha_code": "ORPHA324",
            "overview": "一种 X 链锁隐性遗传的鞘糖脂代谢障碍病，由于 α-半乳糖苷酶 A (GLA) 活性缺陷导致。"
        }
    ]

    fetcher.add_disease_batch(targets)