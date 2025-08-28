import traceback
from sqlalchemy.orm import Session
from database import AnalysisReport
from services import worknet_crawler, llm_summary_agent, report_generator

def run_daily_job_recommendation(db: Session, user_id: int):
    """시나리오 1: 일일 채용 공고 추천 실행"""
    print(f"\n--- 시나리오 1: 사용자(id={user_id}) 채용 공고 추천 시작 ---")
    try:
        # 1. 워크넷에서 관심기업 채용 공고 크롤링
        raw_jobs = worknet_crawler.run_worknet_crawling(db, user_id)
        
        if not raw_jobs:
            print("추천할 신규 채용 공고가 없습니다.")
            return

        # 2. LLM을 통해 챗봇 메시지 생성
        summary = llm_summary_agent.generate_chat_summary(raw_jobs)
        
        # 3. (추가) 생성된 메시지를 사용자에게 발송 (e.g., DB 저장, 푸시 알림)
        # 이 예제에서는 단순히 출력합니다.
        print("\n--- 최종 추천 메시지 ---")
        print(summary)
        print("--------------------")

    except Exception as e:
        print(f"시나리오 1 실행 중 오류 발생: {e}")
        traceback.print_exc()

def run_analysis_report_task(report_id: int, target_job: str, target_company: list, db: Session):
    """시나리오 2: 분석 리포트 생성 (백그라운드 태스크)"""
    print(f"\n--- 시나리오 2: 리포트(id={report_id}) 생성 작업 시작 ---")
    
    report = None  # report 변수를 try 블록 이전에 초기화
    try:
        # 1. DB 상태를 'RUNNING'으로 업데이트
        report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
        if not report:
            print(f" 리포트(id={report_id})를 찾을 수 없습니다.")
            return
            
        report.status = "RUNNING"
        db.commit()

        # 2. LangGraph 리포트 생성 실행
        # [수정] report_generator가 기대하는 형식인 딕셔너리로 데이터를 재구성합니다.
        user_profile_for_graph = {
            "목표 직무": target_job,
            "희망 기업": target_company
            # (향후 사용자의 다른 정보-스펙, 학년 등-가 있다면 여기에 추가하면 됩니다.)
        }

        # [수정] 재구성한 딕셔너리 하나만 인자로 전달합니다.
        final_report_content = report_generator.run_graph_analysis(user_profile_for_graph)


        # 3. 성공 시 DB에 결과 저장 및 상태 변경
        report.content = final_report_content
        report.status = "COMPLETED"
        db.commit()
        print(f" 리포트(id={report_id}) 생성 완료.")

    except Exception as e:
        # 4. 실패 시 DB에 에러 메시지 저장 및 상태 변경
        error_msg = traceback.format_exc()
        print(f" 리포트(id={report_id}) 생성 중 오류 발생: {e}")
        
        if 'report' in locals():
            report.status = "FAILED"
            report.error_message = error_msg
            db.commit()
    finally:
        db.close() # 백그라운드 작업이므로 세션을 직접 닫아줘야 합니다.