# 데이터 소개

Synthea를 이용하여 가상으로 생성한 EMR 데이터를 Common Data Model로 변환한 데이터가 제공됩니다.
	•	person: 환자
	•	visit_occurrence: 방문
	•	condition_occurrence: 진단
	•	drug_exposure: 의약품 처방
	•	death: 사망
	•	concept: concept_id 정보

# 문제 정의: 사망률과 연관성이 높은 변수 탐색¶
제공된 데이터셋의 사망률은 15.2% 입니다. 사망률과 연관성이 높은 변수를 탐색합니다. 연관이 높다 낮다를 말할 수 있는 척도를 정하고, 아래 카테고리에 해당하는 변수를 연관성이 높은 순서대로 나열합니다.
	•	death:
	▪	사망일: death_date
	•	person:
	▪	성별: gender
	▪	인종: ethnicity_concept_id
	▪	나이: year_of_birth를 활용하여 계산
	•	visit_occurrence:
	▪	입원: visit_concept_id=9201
	▪	외래: visit_concept_id=9202
	▪	응급: visit_concept_id=9203
	▪	내원일수: visit_end_date - visit_start_date
	•	condition_occurrence:
	▪	진단: condition_concept_id, condition_source_value
	•	drug_exposure:
	▪	의약품: drug_concept_id, drug_source_value

사망자 생존환자 모두 인종 데이터의 분포가 불균형하게 나타남
한 인종만 데이터 크기가 불충분하지 않다고 할 수 있어서 사망률과 인종의 연관성을 배제하고 해당 인종의 다른 변수들을 집중적으로 탐색적 분석 진행

![스크린샷 2021-02-07 오후 11 52 31](https://user-images.githubusercontent.com/68261338/107150204-14d32d80-69a0-11eb-8803-c0183477099a.png)
![스크린샷 2021-02-07 오후 11 52 37](https://user-images.githubusercontent.com/68261338/107150207-17358780-69a0-11eb-8273-5413d96b1b12.png)

로지스틱회귀분석:
결론적으로 모든 변수의 유의관계를 확인하진 못했습니다
로지스틱 회귀분석으로 확인해본 독립변수들의 유의한 정도의 순서는 다음과 같습니다:
1. 연령
2. 성별

무의미한 독립변수:
- hispanic(유/무) 파생변수
- 인종 - 데이터 부족
- 왜래진료 평균 횟수
- 상병 보유 갯수

회고록:
- 우선순위 설정 잘할것: 처음부터 파생변수 만들려고 한건 잘못된 접근
- 데이터 탐색에 매진된 나머지 시간 분배를 잘못했다
- 파이썬으로 모든 변수를 일일히 확인해보는건 추후에 데이터 칼럼 수가 많아질텐데 어쩌면 비효율적인 습관일수도 있다. SQL을 더 적극적으로 활용해볼것
- 탐색적 분석과 상관관계 분석을 하나씩 클리어한다는 자세가 아니라 병행하면서 상호보완적인 방식으로 전체적인 분석의 성과를 끌어올릴 것 
