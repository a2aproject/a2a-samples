# a2a_skeleton
## 개요

a2a_skeleton은 다양한 에이전트 기반 서비스(게이트웨이, 콘텐츠 생성, 검색, 호스트 관리 등)로 구성된 마이크로서비스 아키텍처의 예시 프로젝트입니다. 각 에이전트는 독립적으로 동작하며, Gateway를 통해 통합적으로 접근할 수 있습니다.

## 전체 구조

- **gateway**: 모든 외부 요청을 받아 각 에이전트로 라우팅하는 중간 다리 역할을 합니다.
- **generate_contents_agent**: 텍스트, 카드 등 다양한 콘텐츠를 자동으로 생성하는 에이전트입니다.
- **search_agent**: 문서, 카드, 외부 데이터 등에서 정보를 검색하는 에이전트입니다.
- **host_agent**: 각 에이전트의 등록, 연결, 상태 확인 등 에이전트 관리 및 서비스 디스커버리를 담당합니다.

## 설치 방법

각 디렉토리(gateway, generate_contents_agent, search_agent, host_agent)에서 아래 명령어로 의존성을 설치합니다.

```
uv sync
```

## 실행 방법

각 서비스는 아래와 같이 실행할 수 있습니다. (포트는 환경에 맞게 조정하세요)

- **gateway**
  ```
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
- **generate_contents_agent**
  ```
  uvicorn main:app --reload --host 0.0.0.0 --port 8002
  ```
- **search_agent**
  ```
  uvicorn main:app --reload --host 0.0.0.0 --port 8003
  ```
- **host_agent**
  ```
  uvicorn main:app --reload --host 0.0.0.0 --port 8001
  ```

## 사용 예시

1. 각 서비스의 서버를 실행합니다.
2. Gateway(8000 포트)로 요청을 보내면, 내부적으로 적절한 에이전트로 라우팅되어 결과를 받을 수 있습니다.

- 예시

curl -X POST "http://localhost:8000/message" \
  -H "Content-Type: application/json" \
  -N \
  -d '{
    "query": "양자역학에대해서 글써줘",
    "user_id": "test-user",
    "app_name": "test-app"
  }'

## 참고

- 각 에이전트별 상세 역할 및 실행 방법은 각 디렉토리의 README.md를 참고하세요.
- uv(https://github.com/astral-sh/uv) 기반으로 의존성 관리 및 실행을 권장합니다.

