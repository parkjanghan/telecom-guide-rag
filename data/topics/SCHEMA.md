# 상담 주제 메타데이터 형식

각 주제는 하나의 Markdown 파일입니다. 현재 YAML frontmatter 값은 JSON 문법으로 작성했습니다. 검색 로더는 안전한 YAML 파서로 읽으며 Obsidian이 저장하는 일반 YAML 목록·날짜도 지원합니다. 파일명과 item_id는 일치합니다. README·SCHEMA·선정/검증 기록은 상담 항목이 아니므로 로더는 frontmatter의 item_id와 source_type을 확인해야 합니다.

|필드|용도|
|---|---|
|item_id / name|고유 식별자와 상담 목적|
|aliases / routing_hints|유사 표현과 탐색 보조어|
|summary / scope|목적 설명과 적용 범위|
|example_questions|검색 표현을 위한 작성 예시. 실제 수집 질문·독립 평가 질문과 구분|
|condition_keys|필요할 때 확인할 변수. 개인정보 값을 저장하지 않음|
|category / service_types|상담 분류·적용 서비스|
|primary_document_id / primary_chunk_ids|대표 공식 근거 문서·청크|
|related_chunk_ids|대표+보조 청크 ID. 실제 경로·연결 이유·범위는 본문의 위키 링크에 기록|
|index_text|주제 검색을 위해 임베딩할 한 덩어리 텍스트|
|evidence_status|linked_draft / partial / missing|
|review_notes / external_lookup_topics|범위 한계와 외부 확인 대상|
|review_status / answer_ready|검토 상태. 현재 draft / false|
|retrieval_ready|필드 작성 완료 여부. 검색 품질이나 인덱스 생성 완료 여부가 아님|
|discovery_sources / discovery_count|일부 게시판 발견 주제의 수요 출처. 정책 근거가 아님|
|source_type / is_policy_evidence|generated_topic_metadata / false|

전체 원문과 URL·추출 범위는 data/SOURCES.md 및 data/chunks의 원문 문서에서 추적합니다. metadata를 정답 근거로 인용하지 않습니다. 자료에 직접 없는 결론을 추론할 때는 확인한 문서에 직접 명시되지 않았다는 고지를 붙입니다.

주제·별칭·예시만 보고 원문 근거의 적용 범위를 확대하면 안 됩니다. missing 항목은 주제를 인식한 뒤 외부 확인으로 안내할 수 있지만 내부 원문을 확보한 것으로 처리하지 않습니다.

## 다음 단계

메타데이터 초안 103개를 유지한 채 실제 로컬 임베딩과 주제·원문 두 컬렉션을 구성했습니다. 작성 점검 질문과 기존 게시판 질문의 검색 회귀 점검을 진행했습니다. 의미·조건의 완전 검수와 독립 질문 평가는 아직 남아 있습니다. 실행 방법은 저장소 루트 RETRIEVAL.md를 참고하세요. 원문 MD와 주제를 수정한 뒤에는 index를 다시 실행해야 합니다.

## 서비스 지원 상태

service_status=unsupported_draft이면 조사용으로 보존하되 챗봇 선택·자동 카탈로그·직접 요청에서 제외합니다. support_reason과 support_checked_at에 사유·확인일을 기록합니다. retrieval_ready=false는 준비 중임을 뜻합니다. service_status가 없는 기존 주제는 supported_draft로 해석합니다. UI/API의 지원 수와 조사용 전체 메타데이터/색인 수는 구분합니다.
