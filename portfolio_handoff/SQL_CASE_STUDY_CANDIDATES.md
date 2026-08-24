# SQL / Data Case Study Candidates

## 1. P01 — 등록 퍼널·리드타임·운영 규칙 개선

- **Business Question:** 어떤 단계/카테고리에서 지연과 재작업이 발생하며, 어떤 운영 규칙 보강이 효과적인가?
- **Current Data:** 단계 상태, 날짜, 지연 사유, 브랜드/카테고리, 규칙 문서.
- **Missing Data:** 규칙 개정 이력, 담당자 구분, 문의/CS/보류/재작업, 거래 성과.
- **Suggested SQL:** JOIN, CASE WHEN, CTE, DATE functions, window functions, Pareto GROUP BY.
- **Decision Value:** 규칙·프로세스 개선의 우선순위를 감각이 아닌 병목과 영향도로 정할 수 있다.

## 2. P04 — 매입 수익성·SKU/옵션 우선순위

- **Business Question:** 제한된 매입 자본을 어떤 SKU/옵션에 배분해야 하는가?
- **Current Data:** SKU/옵션, 가격, 거래량, 재고, 수익성, 컨펌/예정 수량.
- **Missing Data:** 실제 주문/판매/반품/정산, 가격 스냅샷, 고유 키.
- **Suggested SQL:** JOIN, CASE WHEN, CTE, RANK, LAG, window functions, scenario tables.
- **Decision Value:** 할인율이 아니라 수요·마진·재고·시즌의 균형으로 우선순위를 판단할 수 있다.

## Third Candidate

P03은 실행 로그와 자동화 전후 처리시간을 확보하면, 대량 SKU 처리 생산성·품질 분석 사례로 확장한다.
