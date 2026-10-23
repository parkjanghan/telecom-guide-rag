# 상담 주제 메타데이터 — 103개 초안

기존 10개 파일럿을 유지·확장하고, FAQ 기반 신규 90개 및 게시판에서 발견한 3개를 같은 형식으로 정리했습니다. 모두 draft이며 정책 근거 자체가 아닙니다. 원문 청크는 변경하지 않습니다.

## 서비스 지원 상태 (2026-10-23)

총103개 중101개를 챗봇에서 선택할 수 있습니다. 대표 근거가 없는 internet_renewal_comparison과 internet_sales_dispute는 unsupported_draft로 보존하며 미지원 영역에 따로 표시합니다. 아래 목록/건수는 조사 자료를 포함합니다.

## 현재 상태

- 주제 103개 / 근거 연결 180개 / 고유 원문 175개.
- `retrieval_ready: true`는 탐색용 필드를 채웠다는 뜻입니다. 임베딩이나 검색 품질 검증 완료를 뜻하지 않습니다.
- `answer_ready: false`는 전체 주제의 답변 생성 검증을 아직 완료하지 않았다는 뜻입니다. 연결이 존재해도 바로 정답으로 사용하지 않습니다.
- `linked_draft`: 대표 근거가 연결된 초안. `partial`: 범위·조건 또는 상세 근거 보완 필요. `missing`: 공식 근거 미연결.
- 선정 당시 목록은 [[TOPICS_100]], 확장 이유는 [[BOARD_VALIDATION_01]], 수집 보류 후보는 [[BOARD_VALIDATION_02]]에 남깁니다.

## 검토 순서

1. 이 목록에서 주제의 이름·별칭·대표 질문을 확인합니다.
2. 주제 문서의 원문 링크와 범위 메모를 확인합니다.
3. 부분 근거·미연결 항목을 보완한 뒤 주제 컬렉션과 원문 컬렉션을 구성합니다.
4. 주제 선정·수정에 사용하지 않은 독립 질문으로 검색을 평가합니다. 기존 10개용 규칙 분류기는 103개 검색 평가로 사용하지 않습니다.

## 주제 목록

|번호|분류|상담 주제|근거 상태|연결 수|
|---:|---|---|---|---:|
|1|납부·청구|[[payment_method_change|자동납부 수단 변경]]|linked_draft|6|
|2|납부·청구|[[payment_due_date_change|납부 기준일 변경]]|linked_draft|4|
|3|납부·청구|[[billing_delivery_change|요금명세서 수령 방법 변경]]|linked_draft|3|
|4|가입·변경·약정|[[mobile_ownership_transfer|휴대폰 명의변경]]|linked_draft|2|
|5|가입·변경·약정|[[mobile_temporary_suspension|휴대폰 일시정지]]|linked_draft|5|
|6|가입·변경·약정|[[mobile_termination|휴대폰 회선 해지]]|linked_draft|4|
|7|가입·변경·약정|[[call_history_access|통화내역 열람]]|linked_draft|3|
|8|안전·부가서비스·혜택|[[lost_phone_response|휴대폰 분실 대응]]|linked_draft|3|
|9|할인·결합|[[selective_contract_discount|선택약정 할인 가입]]|linked_draft|5|
|10|할인·결합|[[family_bundle_maintenance|가족결합 유지 조건 확인]]|partial|6|
|11|납부·청구|[[consultation_011|이용요금과 청구내역 조회]]|linked_draft|1|
|12|납부·청구|[[consultation_012|정보이용료 청구 원인 확인]]|linked_draft|1|
|13|납부·청구|[[consultation_013|요금내역서 발급]]|linked_draft|1|
|14|납부·청구|[[consultation_014|명세서 미수신·배송 지연 해결]]|linked_draft|2|
|15|납부·청구|[[consultation_015|여러 회선의 청구서 통합]]|linked_draft|1|
|16|납부·청구|[[consultation_016|현재 납부수단 조회]]|linked_draft|1|
|17|납부·청구|[[consultation_017|요금 즉시 납부]]|linked_draft|2|
|18|납부·청구|[[consultation_018|전용계좌 발급과 입금 납부]]|linked_draft|1|
|19|납부·청구|[[consultation_019|지로 요금 납부]]|linked_draft|2|
|20|납부·청구|[[consultation_020|단말기 할부 잔액 조회]]|linked_draft|1|
|21|납부·청구|[[consultation_021|휴대폰결제 서비스 이용 신청]]|partial|2|
|22|납부·청구|[[consultation_022|휴대폰결제 차단·한도 관리]]|linked_draft|1|
|23|납부·청구|[[consultation_023|선불요금 충전과 잔액 관리]]|linked_draft|3|
|24|납부·청구|[[consultation_024|문자 발송 요금 확인]]|linked_draft|1|
|25|가입·변경·약정|[[consultation_025|휴대폰 신규가입]]|linked_draft|2|
|26|가입·변경·약정|[[consultation_026|휴대폰 번호이동]]|linked_draft|1|
|27|가입·변경·약정|[[consultation_027|휴대폰 기기변경]]|linked_draft|1|
|28|가입·변경·약정|[[consultation_028|휴대폰 번호변경]]|linked_draft|1|
|29|가입·변경·약정|[[consultation_029|휴대폰 요금제 변경]]|linked_draft|1|
|30|가입·변경·약정|[[consultation_030|요금제 변경에 따른 기존 약정 영향 확인]]|partial|1|
|31|가입·변경·약정|[[consultation_031|자급제·중고·해외 단말 KT 이용]]|linked_draft|1|
|32|가입·변경·약정|[[consultation_032|유심 이동 후 서비스·할인 유지 확인]]|linked_draft|1|
|33|가입·변경·약정|[[consultation_033|개통 취소 절차 확인]]|partial|2|
|34|가입·변경·약정|[[consultation_034|약정 중도해지 반환금 확인]]|linked_draft|1|
|35|가입·변경·약정|[[consultation_035|지원금·선택약정 할인 방식 전환]]|partial|1|
|36|가입·변경·약정|[[consultation_036|유심 구입·발급 비용 확인]]|linked_draft|2|
|37|가입·변경·약정|[[consultation_037|eSIM 삭제와 회선 해지 구분]]|linked_draft|1|
|38|가입·변경·약정|[[consultation_038|고객센터 상담 시간·연락 방법 확인]]|linked_draft|1|
|39|데이터·로밍|[[consultation_039|음성·문자·데이터 잔여량 조회]]|linked_draft|1|
|40|데이터·로밍|[[consultation_040|데이터 추가 충전]]|linked_draft|1|
|41|데이터·로밍|[[consultation_041|데이터 충전 취소]]|linked_draft|1|
|42|데이터·로밍|[[consultation_042|가족·친구에게 데이터 나누기]]|linked_draft|1|
|43|데이터·로밍|[[consultation_043|데이터쉐어링 가입·이용]]|partial|1|
|44|데이터·로밍|[[consultation_044|데이터쉐어링과 테더링 비교]]|linked_draft|1|
|45|데이터·로밍|[[consultation_045|데이터쉐어링 회선 변경·해지 영향 확인]]|linked_draft|3|
|46|데이터·로밍|[[consultation_046|데이터쉐어링 사용량 조회]]|linked_draft|1|
|47|데이터·로밍|[[consultation_047|데이터 초과 요금 방지]]|partial|1|
|48|데이터·로밍|[[consultation_048|모바일 데이터 이용 차단]]|linked_draft|1|
|49|데이터·로밍|[[consultation_049|해외 로밍 상품·요금 확인]]|partial|2|
|50|데이터·로밍|[[consultation_050|로밍 이용 후 귀국 시 설정 확인]]|linked_draft|1|
|51|할인·결합|[[consultation_051|복지할인 대상·혜택 확인]]|linked_draft|3|
|52|할인·결합|[[consultation_052|복지할인 신청 월의 할인 적용 확인]]|linked_draft|1|
|53|할인·결합|[[consultation_053|연령에 따른 요금제 혜택 확인]]|linked_draft|2|
|54|할인·결합|[[consultation_054|군인 전용 혜택 확인]]|partial|2|
|55|할인·결합|[[consultation_055|가족결합 가입 자격·가족 범위 확인]]|partial|3|
|56|할인·결합|[[consultation_056|결합 가입 신청·구비서류 확인]]|linked_draft|2|
|57|할인·결합|[[consultation_057|기존 결합에 휴대폰 회선 추가]]|linked_draft|2|
|58|할인·결합|[[consultation_058|결합상품 간 전환]]|partial|1|
|59|할인·결합|[[consultation_059|복지할인·결합할인 중복 적용 확인]]|linked_draft|2|
|60|할인·결합|[[consultation_060|결합할인 금액·적용 항목 확인]]|partial|2|
|61|안전·부가서비스·혜택|[[consultation_061|스팸 전화·문자 차단]]|linked_draft|1|
|62|안전·부가서비스·혜택|[[consultation_062|특정 번호 수신 차단]]|linked_draft|1|
|63|안전·부가서비스·혜택|[[consultation_063|명의도용 예방·피해 대응]]|linked_draft|1|
|64|안전·부가서비스·혜택|[[consultation_064|스미싱 예방·대응]]|linked_draft|1|
|65|안전·부가서비스·혜택|[[consultation_065|유심 PIN 설정·잠금 관리]]|partial|3|
|66|안전·부가서비스·혜택|[[consultation_066|유심 PUK 잠금 해제]]|linked_draft|1|
|67|안전·부가서비스·혜택|[[consultation_067|휴대폰 보험 가입·보장 확인]]|partial|1|
|68|안전·부가서비스·혜택|[[consultation_068|휴대폰 분실·파손 보험 보상 신청]]|linked_draft|2|
|69|안전·부가서비스·혜택|[[consultation_069|장기고객 혜택·쿠폰 이용]]|partial|3|
|70|안전·부가서비스·혜택|[[consultation_070|요금제 제공 OTT 계정 등록·관리]]|partial|4|
|71|인터넷·와이파이|[[consultation_071|인터넷 설치 가능 지역·상품 확인]]|partial|1|
|72|인터넷·와이파이|[[consultation_072|인터넷 신규가입 후 개통 일정 확인]]|partial|1|
|73|인터넷·와이파이|[[consultation_073|인터넷 속도 측정]]|linked_draft|1|
|74|인터넷·와이파이|[[consultation_074|인터넷 속도 저하 해결]]|linked_draft|3|
|75|인터넷·와이파이|[[consultation_075|인터넷 접속 장애 신고·해결]]|linked_draft|1|
|76|인터넷·와이파이|[[consultation_076|인터넷 모뎀·공유기 고장과 교체]]|linked_draft|2|
|77|인터넷·와이파이|[[consultation_077|인터넷 이사 이전 신청·일정·비용 확인]]|linked_draft|4|
|78|인터넷·와이파이|[[consultation_078|집 안 인터넷 설치 위치 변경]]|linked_draft|1|
|79|인터넷·와이파이|[[consultation_079|인터넷 장기 일시정지]]|partial|1|
|80|인터넷·와이파이|[[consultation_080|인터넷 해지 시 임대장비 반납]]|linked_draft|1|
|81|인터넷·와이파이|[[consultation_081|인터넷 약정 만료 후 요금 확인]]|partial|1|
|82|인터넷·와이파이|[[consultation_082|인터넷 해지 후 청구요금 확인]]|linked_draft|1|
|83|인터넷·와이파이|[[consultation_083|타사 인터넷 원스톱 전환]]|partial|1|
|84|인터넷·와이파이|[[consultation_084|와이파이 이름·비밀번호 확인과 접속]]|partial|1|
|85|인터넷·와이파이|[[consultation_085|와이파이 속도 저하 해결]]|linked_draft|1|
|86|TV·콘텐츠|[[consultation_086|TV 가입 가능 조건·필요 기기 확인]]|linked_draft|2|
|87|TV·콘텐츠|[[consultation_087|TV 여러 대 가입·추가 이용]]|partial|1|
|88|TV·콘텐츠|[[consultation_088|TV 요금제·유료 콘텐츠 과금 범위 확인]]|linked_draft|1|
|89|TV·콘텐츠|[[consultation_089|TV 월정액 부가상품 가입]]|linked_draft|1|
|90|TV·콘텐츠|[[consultation_090|TV VOD 구매·이용내역 조회]]|linked_draft|1|
|91|TV·콘텐츠|[[consultation_091|TV 콘텐츠 구매 환불]]|partial|1|
|92|TV·콘텐츠|[[consultation_092|TV 쿠폰 등록·사용]]|partial|1|
|93|TV·콘텐츠|[[consultation_093|TV 비밀번호 설정·분실 해결]]|linked_draft|2|
|94|TV·콘텐츠|[[consultation_094|TV 성인 콘텐츠·시청 연령 제한 관리]]|linked_draft|1|
|95|TV·콘텐츠|[[consultation_095|TV 리모컨 설정·고장·분실 해결]]|linked_draft|4|
|96|TV·콘텐츠|[[consultation_096|TV 화면·음성 이상 해결]]|linked_draft|3|
|97|TV·콘텐츠|[[consultation_097|TV 채널이 나오지 않는 문제 해결]]|linked_draft|2|
|98|TV·콘텐츠|[[consultation_098|TV 다시보기·VOD 재생 장애 해결]]|partial|2|
|99|TV·콘텐츠|[[consultation_099|TV 이사 이전 신청·일정·비용 확인]]|linked_draft|4|
|100|TV·콘텐츠|[[consultation_100|지니 TV 모바일 연결·페어링]]|linked_draft|1|
|101|인터넷·와이파이|[[internet_renewal_comparison|인터넷·TV 재약정과 통신사 이동 비교]]|missing|0|
|102|가입·변경·약정|[[wired_ownership_transfer|인터넷 명의변경]]|partial|1|
|103|안전·부가서비스·혜택|[[internet_sales_dispute|인터넷 가입 권유·이중계약 피해 상담]]|missing|0|
