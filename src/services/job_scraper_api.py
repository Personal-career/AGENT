import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
import mysql.connector
import requests
import xml.etree.ElementTree as ET
import re
from typing import List, Dict
import config

# --------------------------------------------------------------------------
# FastAPI 앱 생성
# --------------------------------------------------------------------------
app = FastAPI(
    title="Worknet Job Scraper API",
    description="관심 기업의 채용 공고를 수집하여 데이터베이스에 저장하는 API입니다.",
    version="1.0"
)

# --------------------------------------------------------------------------
# 설정 및 기존 로직 
# --------------------------------------------------------------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'dldudwns01~',
    'database': 'mysql'
}

# _normalize, build_interest_set, is_interest_company 함수 (기존과 동일)
def _normalize(s: str) -> str:
    if not s: return ""
    s = re.sub(r"\(주\)", "", s)
    s = re.sub(r"[\s·•\-_/]", "", s)
    s = re.sub(r"[^\w가-힣]", "", s)
    return s.lower()

def build_interest_set(companies, aliases):
    norm_set = set()
    for c in companies: norm_set.add(_normalize(c))
    for a in aliases:
        if a: norm_set.add(_normalize(a))
    return norm_set

def is_interest_company(company_name: str, interest_norm_set) -> bool:
    n = _normalize(company_name)
    if not n: return False
    if n in interest_norm_set: return True
    for target in interest_norm_set:
        if target in n or n in target: return True
    return False

# --------------------------------------------------------------------------
# 데이터베이스 및 API 호출 함수 (기존 로직 약간 수정)
# --------------------------------------------------------------------------

def fetch_companies_from_db() -> (List[str], List[str]):
    print("\n🔍 DB에서 관심 기업 불러오기")
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT name, alias FROM companies")
        rows = cursor.fetchall()
        companies = [row[0] for row in rows if row[0]]
        aliases = [row[1] for row in rows if len(row) > 1 and row[1]]
        print(f"✅ DB 기업명 {len(companies)}개, 별칭 {len([a for a in aliases if a])}개 불러옴")
        return companies, aliases
    except mysql.connector.Error as err:
        print(f"❌ DB 오류: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

def fetch_and_filter_jobs(companies, aliases) -> List[Dict]:
    # (기존 fetch_and_filter_jobs 함수 내용과 동일)
    if not companies: return []
    url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"
    all_raw_jobs = []
    interest_norm_set = build_interest_set(companies, aliases)
    print("\n📦 '채용정보' API 수집 시작\n")
    for page in range(1, 4):
        params = {"authKey": config.WORKNET_API_KEY, "callTp": "L", "returnType": "XML", "startPage": str(page), "display": "100"}
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            for job_item in root.findall(".//dhsOpenEmpInfo"):
                company_name = job_item.findtext("empBusiNm") or ""
                if not is_interest_company(company_name, interest_norm_set): continue
                print(f"🎯 매칭된 기업: {company_name}")
                job_data = {
                    "company_name": company_name, "job_title": job_item.findtext("empWantedTitle"),
                    "employment_type": job_item.findtext("empWantedTypeNm"), "start_date": job_item.findtext("empWantedStdt"),
                    "end_date": job_item.findtext("empWantedEndt"), "company_type": job_item.findtext("coClcdNm"),
                    "company_logo": job_item.findtext("regLogImgNm"), "apply_link": job_item.findtext("empWantedHomepgDetail"),
                    "job_id": job_item.findtext("wantedAuthNo")
                }
                all_raw_jobs.append(job_data)
        except Exception as e:
            print(f"❌ API 오류 (페이지 {page}): {e}")
            continue
    print(f"\n📊 관심기업 공고 수집 결과: {len(all_raw_jobs)}건")
    return all_raw_jobs


def upsert_jobs_to_db(data: List[Dict]):
    # (기존 upsert_jobs_to_db 함수 내용과 거의 동일, 에러 핸들링 추가)
    if not data:
        print("💡 수집된 공고가 없어 DB에 저장하지 않습니다.")
        return
    conn = None
    try:
        # 이 함수 내에서 기존 job_id를 가져오는 로직을 포함
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT job_id FROM jobs")
        existing_job_ids = {row[0] for row in cursor.fetchall()}
        
        new_jobs = [job for job in data if job['job_id'] not in existing_job_ids]
        if not new_jobs:
            print("💡 새로운 공고가 없습니다.")
            return

        job_tuples = [(job.get('company_name'), job.get('job_title'), job.get('employment_type'), job.get('start_date'),
                       job.get('end_date'), job.get('company_type'), job.get('company_logo'), job.get('apply_link'),
                       job.get('job_id')) for job in new_jobs]
        
        query = """
            INSERT INTO jobs (company_name, job_title, employment_type, start_date, end_date, company_type, company_logo, apply_link, job_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE company_name=VALUES(company_name), job_title=VALUES(job_title), employment_type=VALUES(employment_type), start_date=VALUES(start_date), end_date=VALUES(end_date), company_type=VALUES(company_type), company_logo=VALUES(company_logo), apply_link=VALUES(apply_link);
        """
        cursor.executemany(query, job_tuples)
        conn.commit()
        print(f"✅ 총 {cursor.rowcount}개 신규 공고가 DB에 성공적으로 저장되었습니다.")
    except mysql.connector.Error as err:
        print(f"❌ DB 저장 오류: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()


def create_jobs_table_if_not_exists():
    # (기존 create_jobs_table 함수와 동일)
    conn = None
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        create_table_query = """
            CREATE TABLE IF NOT EXISTS jobs (id INT AUTO_INCREMENT PRIMARY KEY, company_name VARCHAR(255), job_title VARCHAR(255), employment_type VARCHAR(255), start_date VARCHAR(255), end_date VARCHAR(255), company_type VARCHAR(255), company_logo VARCHAR(255), apply_link VARCHAR(255), job_id VARCHAR(255) UNIQUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        """
        cursor.execute(create_table_query)
        print("✅ 'jobs' 테이블이 성공적으로 생성되었거나 이미 존재합니다.")
    except mysql.connector.Error as err:
        print(f"❌ 테이블 생성 오류: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()

# --------------------------------------------------------------------------
# 핵심 작업 실행 함수 (백그라운드에서 실행될 로직)
# --------------------------------------------------------------------------
def run_job_scraping_task():
    """채용 공고 스크래핑부터 DB 저장까지의 전체 작업을 실행합니다."""
    print("\n=== [Background Task] Job Crawling 에이전트 실행 시작 ===")
    create_jobs_table_if_not_exists()
    companies, aliases = fetch_companies_from_db()
    raw_jobs = fetch_and_filter_jobs(companies, aliases)
    
    if raw_jobs:
        upsert_jobs_to_db(raw_jobs)
        print("\n🎉 [Background Task] 채용공고 수집 및 저장 완료")
    else:
        print("\n💡 [Background Task] 새로운 관심 기업 공고 없음")
    print("\n=== [Background Task] Job Crawling 에이전트 실행 종료 ===")


# --------------------------------------------------------------------------
# FastAPI 엔드포인트 정의
# --------------------------------------------------------------------------
@app.post("/trigger-job-scrape", status_code=202)
def trigger_scrape(background_tasks: BackgroundTasks):
    """
    Worknet 채용 공고 스크래핑 작업을 백그라운드에서 실행합니다.
    """
    print("🚀 API 요청 수신: 채용 공고 스크래핑 작업을 백그라운드에서 시작합니다.")
    background_tasks.add_task(run_job_scraping_task)
    return {"message": "Job scraping task has been started in the background."}

# --------------------------------------------------------------------------
# 서버 실행 (터미널에서 uvicorn job_scraper_api:app --reload)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)