from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any

# LangGraph 실행 함수 import (네가 만든 report_generator.py 안에 있음)
from app.report_generator import run_graph_analysis

router = APIRouter()

# 입력 모델 정의
class UserProfileInput(BaseModel):
    user_profile_raw: Dict[str, Any]

# 보고서 생성 엔드포인트
@router.post("/report/generate")
def generate_report(profile: UserProfileInput):
    """
    사용자 프로필 기반으로 맞춤형 분석 보고서를 생성합니다.
    """
    try:
        result = run_graph_analysis(profile.user_profile_raw)
        return {"success": True, "report": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
