# AGENT

### 
1. 터미널을 엽니다.  
2. 환경 설정  
3. 프로젝트 폴더로 이동. ```cd src```  
4. 아래 명령어 입력. ```uvicorn api_server:app --reload```  
5.  ```http://127.0.0.1:8000``` 서버에 접속.  

```
agent-services/
├─ README.md                 # 핸드오프 요약(엔드포인트/스케줄/cURL)
├─ openapi.yaml              # API 계약서(4개 엔드포인트)
├─ .env.example              # 키/DB 샘플
├─ requirements.txt          # 파이썬 의존성
├─ schemas/                  # 요청/응답 모델(Pydantic)
│  ├─ jobs.py
│  ├─ recommend.py
│  └─ chatbot.py
├─ services/                 # 핵심 로직(엔드포인트에서 호출)
│  ├─ job_sync.py
│  ├─ jobs_query.py
│  ├─ recommend.py
│  └─ gemini.py
├─ utils/                    # 공통 유틸(커서/시간/텍스트)
│  ├─ paging.py
│  ├─ datetime.py
│  └─ text.py
├─ db/                       # (선택) 참고용 스키마/시드
│  ├─ ddl.sql
│  └─ seed.sql
└─ examples/
   └─ fastapi_app/           # 참고용 FastAPI 서버(데모)
      ├─ main.py
      ├─ core/config.py
      ├─ routers/
      │  ├─ jobs.py         # /jobs/sync, /jobs/by-company
      │  ├─ recommend.py    # /jobs/recommend
      │  └─ chatbot.py      # /chatbot/query
      └─ db/                # (데모용) 세션/모델
         ├─ session.py
         └─ models/...

```
