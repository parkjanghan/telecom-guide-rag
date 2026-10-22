---
item_id: "consultation_092"
name: "TV 쿠폰 등록·사용"
aliases: ["TV 포인트 쿠폰", "VOD 쿠폰 쓰기"]
example_questions: ["받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?"]
condition_keys: ["쿠폰 종류", "유효기간", "구매 대상"]
summary: "TV 쿠폰 등록·사용을 목적으로 신청·조회·이용 조건 또는 문제 해결 경로를 찾는 상담."
routing_hints: ["TV 포인트 쿠폰", "VOD 쿠폰 쓰기"]
scope: "상담 목적: TV 쿠폰 등록·사용. 대표 질문: 받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?"
service_types: ["TV"]
review_notes: ["쿠폰 유형별 대상·유효기간은 원문과 현재 발급 조건을 확인합니다."]
category: "TV·콘텐츠"
schema_version: "1.0"
review_status: "draft"
answer_ready: false
retrieval_ready: true
source_type: "generated_topic_metadata"
is_policy_evidence: false
generation_method: "curated intent fields + existing official chunk links; draft"
source_registry: "data/SOURCES.md"
answer_rules: ["답변의 사실 근거는 원문 청크에서 확인합니다. 이 메타데이터는 정책 근거가 아닙니다.", "여러 상담 목적이 포함되면 주제를 복수 선택합니다.", "문서에 직접 명시되지 않은 결론을 추론할 경우 확인한 문서에 직접 명시되지 않았다는 점을 답변에 덧붙입니다.", "조건 목록은 필요한 경우 확인할 변수이며 모든 질문에 일괄 추가 질문을 요구하는 규칙이 아닙니다."]
primary_chunk_ids: ["kt_faq_KNOW0000271215"]
related_chunk_ids: ["kt_faq_KNOW0000271215"]
primary_document_id: "kt_faq_KNOW0000271215"
evidence_status: "partial"
external_lookup_topics: ["쿠폰 유효기간·현재 사용 가능 여부"]
index_text: "상담 주제: TV 쿠폰 등록·사용\n별칭: TV 포인트 쿠폰, VOD 쿠폰 쓰기\n설명: TV 쿠폰 등록·사용을 목적으로 신청·조회·이용 조건 또는 문제 해결 경로를 찾는 상담.\n분류: TV·콘텐츠\n서비스: TV\n사용자 질문: 받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?\n확인할 조건: 쿠폰 종류, 유효기간, 구매 대상"
---

# TV 쿠폰 등록·사용

TV 쿠폰 등록·사용을 목적으로 신청·조회·이용 조건 또는 문제 해결 경로를 찾는 상담.

## 대표 사용자 질문

- 받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?

## 적용 범위와 확인할 조건

상담 목적: TV 쿠폰 등록·사용. 대표 질문: 받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?

- 쿠폰 종류
- 유효기간
- 구매 대상

## 연결 근거

- [[KNOW0000271215|tv쿠폰을 받았는데 어떻게 사용하나요?]] — 대표 근거
  - 연결 이유: 상담 목적에 대응하는 대표 원문
  - 적용 범위: FAQ·가이드 본문의 상품·기기·신청 경로에 한정

## 검토 메모

- 쿠폰 유형별 대상·유효기간은 원문과 현재 발급 조건을 확인합니다.

## 외부 조회가 필요한 정보

- 쿠폰 유효기간·현재 사용 가능 여부

## 검색용 텍스트

```text
상담 주제: TV 쿠폰 등록·사용
별칭: TV 포인트 쿠폰, VOD 쿠폰 쓰기
설명: TV 쿠폰 등록·사용을 목적으로 신청·조회·이용 조건 또는 문제 해결 경로를 찾는 상담.
분류: TV·콘텐츠
서비스: TV
사용자 질문: 받은 TV 쿠폰을 어디에 어떻게 쓸 수 있나요?
확인할 조건: 쿠폰 종류, 유효기간, 구매 대상
```

## 답변 시 주의

- 답변의 사실 근거는 원문 청크에서 확인합니다. 이 메타데이터는 정책 근거가 아닙니다.
- 여러 상담 목적이 포함되면 주제를 복수 선택합니다.
- 문서에 직접 명시되지 않은 결론을 추론할 경우 확인한 문서에 직접 명시되지 않았다는 점을 답변에 덧붙입니다.
- 조건 목록은 필요한 경우 확인할 변수이며 모든 질문에 일괄 추가 질문을 요구하는 규칙이 아닙니다.
