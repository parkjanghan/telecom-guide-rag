# 로컬 상담 주제·근거 검색

103개 상담 주제와 공식 원문 MD 1,426개를 읽어 Chroma 컬렉션 두 개를 구성합니다. 현재 단계는 검색 프로토타입이며 답변 생성·외부 조회·LangGraph·웹 화면은 연결하지 않았습니다.

## 처음 설치

Python 3.12에서 확인했습니다. 저장소 루트의 PowerShell에서 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run.ps1 audit
.\run.ps1 index
```

첫 index 실행 때 공개 ONNX 모델을 다운로드합니다. 임베딩은 CPU에서 실행하며 문서와 질문을 외부 임베딩 API에 보내지 않습니다. 로컬 산출물은 `.runtime/`에 저장하고 Git에서 제외합니다. 기존 PC의 설치 환경을 사용할 경우 `config/local.json`의 `python` 경로를 사용할 수 있습니다. 이 파일은 로컬 전용이며 커밋하지 않습니다.

## 검색해 보기

```powershell
.\run.ps1 search "부모님 통장에서 내 통장으로 바꾸면서 가족결합은 유지하고 싶어요."
```

상위 주제 5개와 임시 선택 상위 3개, 연결된 대표·검색 근거를 표시합니다. 상위 3개는 확정 분류가 아니며 관련 없는 후보가 섞일 수 있습니다. 점수는 정답 확률이 아닙니다.

주제를 직접 정해서 근거를 확인할 수도 있습니다.

```powershell
.\run.ps1 search "부모님 계좌에서 제 계좌로 바꿀 때 가족결합이 유지되나요?" --topic payment_method_change --topic family_bundle_maintenance --output .runtime/first-question.json
.\run.ps1 evaluate
.\run.ps1 evaluate --cases tests/board_regression_cases.json --output .runtime/board-evaluation.json
```

`--output`을 지정하면 주제 메타데이터·근거 원문·URL·범위·경고를 포함한 JSON을 저장합니다. `evaluate`는 작성 점검 질문 19개를 실행합니다. board_regression_cases.json은 이전 주제 선정에 사용한 게시판 질문 12건의 요약이며 별도 회귀 점검입니다. 실제 사용자 독립 평가 정확도로 해석하지 않습니다. `run.ps1` 실행 정책이 제한되면 환경변수 PYTHONPATH를 저장소 src로 지정한 뒤 `python -m telecom_rag`를 직접 실행할 수 있습니다.

## 저장 구조

|위치|내용|
|---|---|
|data/topics/*.md|사람이 수정하는 주제 메타데이터|
|data/chunks/*/*.md|검토용 원문 청크. 색인 과정에서 수정하지 않음|
|data/SOURCES.md|공식 URL과 추출 범위|
|config/retrieval.json|모델·배치·검색 수·검색용 청킹 설정|
|src/telecom_rag|로더·임베딩·두 컬렉션·검색·평가|
|tests|청킹/입력 형식 검사 및 작성 점검 질문|
|.runtime/chroma|kt_task_meta / kt_evidence|
|.runtime/embeddings.sqlite3|모델·텍스트별 임베딩 캐시|
|.runtime/models|공개 임베딩 모델 캐시|
|.runtime/build_manifest.json|원문/설정 식별값·모델 해시·구축 건수|

## 두 컬렉션의 역할

- `kt_task_meta`: 상담 주제당 한 레코드. index_text를 임베딩하고 item_id·분류·상태를 필터 정보로 저장합니다.
- `kt_evidence`: 원문 MD의 본문을 임베딩합니다. 긴 문서만 검색용 하위 레코드로 나누며 원본 MD는 그대로 둡니다. parent_chunk_id·document_version·문자 범위·PDF 페이지·URL을 유지합니다.
- 기본 하위 청킹은 모델 토크나이저 기준 360토큰, 중첩 48토큰입니다. 문서 제목을 덧붙여도 입력 한도 512토큰을 넘지 않는지 검사합니다. 표·문장 경계 보존은 원문 MD에서 유지하며 검색용 하위 레코드는 표 중간에서 나뉠 수 있습니다. 결과에는 부모 원문 전체를 반환합니다.
- 문서에는 `passage:`, 질문에는 `query:` 접두사를 사용하고 평균 풀링·정규화를 적용한 384차원 E5 ONNX 벡터를 저장합니다.
- 전체 1,426개를 색인하지만 현재 자동 검색은 선택 주제에 명시적으로 연결된 원문만 대상으로 합니다. 아직 연결되지 않은 문서는 이후 연결 확대용입니다.

## 유지되는 규칙

- 선택 주제 메타데이터와 대표 문서는 검색 순위와 별개로 반환합니다. 메타데이터 자체는 정책 근거가 아닙니다.
- 여러 주제가 같은 원문을 가리키면 부모 청크·버전 기준으로 한 번만 반환합니다.
- 원문 추출 품질 경고가 있는 청크는 일반 검색에서 제외합니다. PDF 표 검토 전 상태는 그대로 기록합니다.
- 공식 근거 미연결 항목은 미연결 경고와 외부 확인 대상을 반환합니다. 게시판 답변을 공식 근거로 대체하지 않습니다.
- 확인한 문서에 직접 없는 내용을 추론할 때는 직접 명시되지 않았다는 고지를 답변에 포함해야 합니다. 답변 생성 단계에서 적용할 규칙이며 검색기가 정책 결론을 생성하지 않습니다.
- 원문·주제·청킹 설정 변경 후에는 index를 다시 실행해야 합니다. 변경을 감지한 채 기존 인덱스로 검색하지 않습니다.
- 동일 입력은 캐시를 사용하고 안정적인 레코드 ID로 upsert합니다. 더 이상 존재하지 않는 레코드만 이 프로젝트의 두 컬렉션에서 제거합니다. 모델 파일이 달라지면 새 runtime 폴더를 사용해야 합니다.

## 확인한 범위

원문 로딩·URL 추적, 긴 문서 전체 범위 보존, 토큰 한도, 두 컬렉션 실제 생성, 재색인 캐시·중복 방지, 대표 근거 포함, 주제 메타데이터 포함, 미연결 경고, 설정 변경 감지를 점검했습니다. 작성 점검 질문 결과는 실제 사용자 독립 평가가 아닙니다. 자동 주제 확정과 답변 생성 품질은 이후 검증이 필요합니다.

모델/라이브러리 참고: [FastEmbed 사용자 모델](https://github.com/qdrant/fastembed), [E5 ONNX 변환본](https://huggingface.co/Xenova/multilingual-e5-small), [Chroma](https://docs.trychroma.com/).

## 초기 결과와 다음 개선

작성 점검 19개에서 기대 주제가 상위 3개에 모두 포함됐지만, 일반 질문 14개 중 1위가 기대 주제인 것은 12개입니다. 기존 게시판 질문 요약 12개는 필요한 모든 주제가 상위 3개에 포함된 경우 6개, 상위 5개에 포함된 경우 8개였습니다. 모두 개발 중 사용한 질문이며 독립 평가 정확도가 아닙니다. 복합 질문의 재약정·이사·명의변경·결합 영향을 분리해 검색하는 처리가 다음 개선 과제입니다. 현재 임시 상위 후보를 그대로 확정하거나 답변 생성에 넘기면 안 됩니다.

## 선택 옵션: 구절별 주제 검색

기본 single은 유지합니다. `--strategy clauses`는 원래 질문과 최대 4개 구절을 검색하고 전체 질문 및 각 구절의 선두 후보와 순위 융합을 조합합니다. `query_plan`과 `matched_queries`로 어떤 구절에서 후보가 나왔는지 볼 수 있습니다. 이는 생성형 의미 분석이 아니며 자동 확정·답변 생성에 사용하지 않습니다.

```powershell
.\run.ps1 search "인터넷 명의를 부모님께 넘기고 가족결합 영향도 확인하고 싶어요." --strategy clauses
.\run.ps1 evaluate --strategy clauses --cases tests/board_regression_cases.json --output .runtime/board-clauses.json
```

기존 게시판 요약12건의 기대 주제 포함은 top3 6→8건, top5 8→10건으로 바뀌었고 작성19건 top3은19건을 유지했습니다. 둘 다 개발용 집합입니다. 사업자 맥락과 유지·전환 관계를 놓치는 사례가 남아 기본값은 바꾸지 않았습니다. 근거 검색 자체는 전체 질문을 사용합니다.

## SSAFY GMS 연결 확인

GMS_KEY와 사용자가 지정한 Responses 주소·모델은 로컬 .env에서 읽습니다. .env는 Git 제외이고 .env.example에는 빈 키만 보관합니다.

```powershell
.\run.ps1 config-check
.\run.ps1 gms-smoke --output .runtime/gms-smoke.json
```

config-check는 네트워크 요청 없이 설정 여부만 표시합니다. gms-smoke는 실제 외부 API 요청 1회를 보내므로 GMS 할당량을 사용합니다. 기본 자동 재시도는 없고, 리다이렉트를 따라가지 않습니다. 실패 시 인증 키·요청 헤더·원문 오류 본문을 출력하지 않으며 0이 아닌 종료 코드를 반환합니다. 완료되지 않은 응답·거부·빈 본문은 정상 답변으로 처리하지 않습니다.

2026-10-22 실제 점검: 지정 모델 gpt-6.1-sol, 응답 completed, 확인 문구 일치, 1.84초, 입력17/출력8/총25토큰. 비용을 별도로 환산하지 않았습니다. 단위 검사24개 통과. 이 결과는 API 연결 확인이며 아직 상담 답변 생성·프롬프트3개·LangGraph를 연결한 것은 아닙니다.

Responses 형식 참고: [OpenAI 공식 텍스트 생성 문서](https://developers.openai.com/api/docs/guides/text). GMS 주소·모델은 사용자가 제공한 curl 예시를 사용하며 직접 OpenAI 주소로 바꾸지 않습니다.

## 의미 기반 질문 분석 (선택 옵션)

```powershell
.\run.ps1 plan-question "명의는 그대로 두고 납부계좌만 바꾸고 싶어요."
.\run.ps1 search "명의는 그대로 두고 납부계좌만 바꾸고 싶어요." --strategy semantic --output .runtime/semantic-search.json
```

처음 보는 질문은 GMS를 호출합니다. 질문 전체와 목적별 검색어·사실·조건·인용·미확인 정보를 구성하며 정책 답변은 생성하지 않습니다. 같은 모델·주소·프롬프트·질문은 .runtime/semantic_plans 캐시를 사용합니다. 원문 인용 실재·허용 필드·값을 검증하지만 의미 정확성까지 보장하지 않습니다. unknowns 전체를 무조건 추가 질문하는 규칙은 없습니다.

기본 single은 유지합니다. 실제 3사례 중 명의·납부자·부정·사업자 구분은 보존됐지만 TV 해지와 결합 유지 및 KT M모바일 사례에서 기대 주제를 놓쳤습니다. 후보 선별과 검색어 간결화가 남아 있습니다. 질문 분석이 성공했다는 이유로 검색·답변 정확도가 확보됐다고 보지 않습니다. 이 단계는 답변 생성·LangGraph·외부 조회를 아직 연결하지 않습니다.
