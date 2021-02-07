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

