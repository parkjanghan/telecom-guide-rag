# 실행 검증과 셀프 체크리스트

2026-10-23. 통과는 기재한 실행 범위의 통과이며 전체 정책 정확도를 보장하지 않는다.

| 항목 | 판정 | 증빙 |
|---|---|---|
| 필수 F2001~F2012 구현 | 구현 확인 | requirements.md와 단계 1~4 보고서 |
| 두 번 색인 / 청크·겹침 변경 / top-k 변경 | 통과 | evidence/KT_4단계_실행경계_검증.json |
| 검색·본문 TTL / robots / 버전·다중 주제 연결 | 자동 검사 통과 | tests/test_chatbot_pipeline.py, test_execution_boundaries.py |
| 빈 결과 캐시·동일 본문 upsert 생략 | 통과 | test_execution_boundaries.py |
| 키·색인 누락 HTTP/UI | 통과 (격리 의존성) | 키누락/색인누락 PNG, 서버 실제 처리기 테스트 |
| 주제 A→B→A 기록 복원 | 통과 (키 누락 환경 질문·오류 기록) | KT_4단계_키누락_주제복원.png |
| 근거 종류/메타데이터 비근거 고지 | 통과 | KT_3단계_근거유형_화면.png |
| 실제 GMS 5문항 + 반복 1회 | 실행 통과 | evaluation.md. 명의변경 1건 보완 이력 포함 |
| 응답 시간 NF2001 | 수용성 미확인 | performance 기록. 직접 선택만 측정 |
| 외부 접근 예절 NF2006 | 구현·제한 검사 확인 | 공식 호스트/UA/간격/robots/유한 재시도. 실제 정책 조사에는 제한 존재 |
| 출처 이용 허가 NF2007 | 미완료 | data/USAGE_CONDITIONS.md |
| 모듈 분리 NF2005 | 구현, 도메인 범용화 부분 | 수집/검색/생성/UI 분리. KT 호스트·규칙은 코드에도 존재 |
| API 키 관리 | 현재 파일 추적 제외 확인 | .env.example만 Git 추적. 과거 Git 이력 전수 검사는 범위 밖 |
| 27개 partial 주제의 전체 정책 정확도 | 미확인 | 주제 초안 검토 필요 |
| 다른 교육생 상호점검 | 미실시 | peer_checklist.md |

## 실행

프로젝트 루트에서 PowerShell `./run-chat.ps1`. 기존 서버를 사용 중이면 그 터미널에서 Ctrl+C 후 다시 실행한다. 같은 포트를 쓰는 사용자 서버는 에이전트가 임의 종료하지 않았다.

Python 환경 PYTHONPATH를 src로 설정하고 `python -m unittest discover -s tests`로 자동 테스트한다. 색인은 `./run.ps1 index`. 주제·원문·검색 설정 변경 시 재색인한다. GMS 설정은 .env.example을 참조하되 키를 기록·커밋하지 않는다.

청크 설정 실험은 운영 색인을 건드리지 않는 별도 runtime에서 수행했다. 경계 UI 캡처는 8767/8768 임시 서버로 수행했으며 종료 후 캡처 파일을 증빙으로 보존한다.

## 제출 확인

- README.md, CHATBOT.md, RETRIEVAL.md, requirements.txt, config, src, web, prompts, tests.
- docs/requirements.md, pipeline.md, evaluation.md, validation.md, peer_checklist.md.
- data/SOURCES.md, USAGE_CONDITIONS.md 및 출처별 허용 여부 확인 기록.
- docs/evidence의 결과·화면. .env, .runtime, 로컬 Python 경로 설정은 제외.
- 원문 전체 배포 범위는 허용 근거 확인 후 결정한다. 현재 이 문서는 외부 배포 실행을 뜻하지 않는다.
- 특정 패키지 사용 자체가 평가 대상인지 담당자와 확인한다. 현재 사용 스택의 차이는 requirements.md에 명시했다.

최종 확인: 자동 테스트 82개 통과, git diff --check 통과, 원본 MD 1,426개 해시 변경 0건, 운영 색인 fingerprint 일치. 추가 기록: evidence/KT_최종보완_검증결과.json. 비교 재실행은 PYTHONPATH를 src로 설정한 환경에서 `python scripts/evaluate_mvp.py` (실제 GMS 사용량 발생). 기본 출력은 Git 제외 .runtime/evaluation이다.
