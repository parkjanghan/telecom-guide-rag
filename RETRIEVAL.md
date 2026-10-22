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
