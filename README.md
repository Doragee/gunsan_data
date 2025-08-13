# 공감 군산: 데이터 시각화 및 AI 챗봇 웹 서비스

## 1. 프로젝트 개요

### 공감 군산은 군산시의 다양한 공공데이터(뉴스, 공공시설 정보 등)를 네이버 지도 위에 시각화하여 시민들이 도시 정보를 직관적으로 탐색할 수 있도록 돕는 웹 애플리케이션입니다.
### 또한, Supabase 벡터 데이터베이스와 연동된 AI 챗봇을 통해 사용자가 자연어 질문으로 원하는 정보를 쉽고 빠르게 찾을 수 있는 대화형 경험을 제공하는 것을 목표로 합니다.

## 2. 주요 기능

### 🗺️ 인터랙티브 지도 시각화
- *지역별 정보 요약*: '개요' 탭에서는 각 지역별 뉴스 및 공공시설 데이터 보유 현황을 이름표(Overlay) 위에 요약하여 표시합니다. 정보가 0건인 항목은 텍스트를 생략하여 깔끔한 UI를 제공합니다.
- *지도 위 시설 표시*: 사용자가 특정 지역 이름표를 클릭하면, 해당 지역으로 줌인되면서 지도 위에 직접 공공시설들의 이름표가 동적으로 표시됩니다.

### 📰 데이터 기반 콘텐츠 뷰
- 정책,소식 & 공공정보: 메뉴 탭을 통해 뉴스 기사와 공공시설 정보를 별도의 페이지에서 확인할 수 있습니다.
- 카드 그리드 UI: 각 정보는 가독성이 높은 카드 형태로 배열되어, 사용자는 화면 낭비 없이 효율적으로 정보를 탐색할 수 있습니다.
- 지역별 필터링: 각 페이지 상단에 제공되는 체크박스를 통해 원하는 지역의 정보만 필터링하여 볼 수 있습니다.

### 🤖 AI 챗봇 (벡터 DB 연동)
- 대화형 정보 검색: 사용자는 화면 우측 하단의 챗봇을 통해 "수송동에 있는 공공시설 알려줘" 와 같이 자연어로 질문할 수 있습니다.
- Supabase 벡터 DB 기반 답변: 챗봇은 Supabase Edge Function을 통해 사용자의 질문과 가장 관련성 높은 정보를 벡터 DB에서 찾아내고, Gemini AI가 이 정보를 바탕으로 최종 답변을 생성합니다.
- 지도 연동: AI가 답변 시, 질문에 언급된 지역이 있다면 지도가 해당 위치로 자동으로 줌인되어 시각적인 컨텍스트를 함께 제공합니다.

### 💬 사용자 참여 유도
- 실시간 질문 피드: 하단 푸터 영역에는 다른 사용자들이 최근에 질문했던 내용들이 뉴스 속보처럼 부드럽게 흘러갑니다.
- 원클릭 질문: 사용자는 피드에서 흥미로운 질문을 클릭하여 챗봇 창에 바로 입력하고 답변을 확인할 수 있습니다.

## 3. 기술 스택
- Frontend: HTML, CSS, JavaScript (Vanilla JS)
- Backend & DB: Supabase (PostgreSQL with pgvector, Edge Functions)
- APIs:
  - Naver Maps API V3
  - Google Gemini AI API (Embedding & Generative Model)
- Libraries
  - marked.js (Markdown 렌더링)
  - marker-clustering.js (네이버 지도 마커 클러스터링)

## 4. 주요 파일 구조
- index.html (또는 gunsanmap.html): 모든 HTML, CSS, JavaScript 로직이 포함된 메인 애플리케이션 파일입니다.
- Supabase Edge Functions
  - query-rag-v2: 사용자의 질문을 받아 라우팅, 벡터 검색, AI 답변 생성 요청까지 처리하는 핵심 함수입니다.
- Supabase Database
  - administrative_welfare_centers: 지역별 중심 좌표 데이터
  - publicFacilities: 공공시설 상세 정보
  - gunsan_news: 군산시 관련 뉴스 정보
  - chatbot_embeddings: 뉴스 및 시설 정보를 벡터로 변환하여 저장한 테이블
  - query_logs: 사용자 질문 기록
- n8n_news_collect : n8n 에서 네이버 뉴스 수집을 자동화하는 API
- CSV Chunking & Embedding (facilities, news).py : supabase 테이블에 있던 데이터를 임베딩화하는 파이썬 스크립트
