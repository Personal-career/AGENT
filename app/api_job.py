# app/db_job.py
import mysql.connector
from fastapi import APIRouter, Query
from dotenv import load_dotenv
import os


# 🔐 환경 변수 로드
load_dotenv()
# FastAPI Router
router = APIRouter()

# ==========================
#  DB 설정 (사용자 제공 정보 그대로)
# ==========================



# ==========================
# 관심 직무 + 포트폴리오 기반 공고 추천
# ==========================
@router.get("/jobs/recommend")
def recommend_jobs(
    job_keywords: str = Query(..., description="사용자가 관심 있는 직무 (쉼표로 구분)"),
    portfolio_keywords: str = Query("", description="포트폴리오 기반 키워드 (쉼표로 구분)")
):
    """
    사용자의 관심 직무와 포트폴리오 키워드를 기반으로 맞춤형 채용공고 추천 API
    - job_keywords: '백엔드,프론트엔드'
    - portfolio_keywords: 'Django,React'
    """
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # 키워드 분리
        job_list = [kw.strip() for kw in job_keywords.split(",") if kw.strip()]
        portfolio_list = [kw.strip() for kw in portfolio_keywords.split(",") if kw.strip()]

        if not job_list and not portfolio_list:
            return {"message": "검색 키워드가 비어있습니다.", "results": []}

        # SQL LIKE 조건 생성
        conditions = []
        params = []

        for kw in job_list + portfolio_list:
            conditions.append("job_title LIKE %s OR company_name LIKE %s")
            params.extend([f"%{kw}%", f"%{kw}%"])

        query = f"SELECT * FROM jobs WHERE {' OR '.join(conditions)} LIMIT 50"

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()

        return {"count": len(results), "results": results}

    except mysql.connector.Error as err:
        return {"error": f"DB 오류: {err}"}
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
