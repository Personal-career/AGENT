from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 각 파일에서 router = APIRouter() 를 export한다고 가정
from app.api_db import router as api_db_router, create_jobs_table
from app.api_company import router as api_company_router
from app.api_job import router as api_job_router
from app.api_report import router as api_report_router

app = FastAPI(
    title="AGENT API",
    version="0.1.0",
    description="에이전트 기반 취업 지원 웹사이트 백엔드 API",
)

# CORS (필요 시 도메인 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # 예: ["https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서버 시작 시 1회 테이블 보장 (실패해도 서비스는 계속)
@app.on_event("startup")
def _startup():
    try:
        create_jobs_table()
    except Exception as e:
        print(f"[startup] jobs 테이블 준비 실패 (무시하고 계속 진행): {e}")

# 라우터 연결
app.include_router(api_db_router, prefix="/api", tags=["1. 수집·DB"])
app.include_router(api_company_router, prefix="/api", tags=["2. 관심기업"])
app.include_router(api_job_router, prefix="/api", tags=["3. 추천"])
app.include_router(api_report_router, prefix="/api", tags=["4. 분석보고서"])

# 기본 라우트
@app.get("/health")
def health():
    return {"ok": True, "service": "AGENT API", "version": "0.1.0"}

@app.get("/")
def root():
    return {"message": "AGENT API", "docs": "/docs", "openapi": "/openapi.json"}

