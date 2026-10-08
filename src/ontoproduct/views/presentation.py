import math

LABELS = {
    "manufacturer": "제조사",
    "rated_voltage": "정격 전압",
    "rated_power": "정격 출력",
    "rated_speed": "정격 속도",
    "weight": "중량",
    "inner_diameter": "내경",
    "outer_diameter": "외경",
}
CLASS_LABELS = {
    "BLDCMotor": "BLDC 모터",
    "Bearing": "베어링",
    "Motor": "모터",
    "Product": "제품",
    "ElectricalPart": "전기 부품",
    "MechanicalPart": "기계 부품",
}
CHECK_LABELS = {
    "PARENT_CLASS": "근거보다 넓은 상위 분류를 선택",
    "UNSUPPORTED_SUBCLASS": "근거 없이 더 좁은 하위 분류를 선택",
    "OTHER_BRANCH": "근거와 다른 계열의 분류를 선택",
}
STATUS_LABELS = {
    "NEEDS_FIX": "수정 필요",
    "READY_FOR_HUMAN": "승인 대기",
    "REGISTERED": "등록 완료",
    "REJECTED": "등록 거절",
    "STOPPED": "작업 중단",
    "ERROR": "오류 확인 필요",
    "NEW": "새 작업",
}
AGENT_LABELS = {
    "parser": "문서 처리",
    "extraction": "정보 추출",
    "ontology": "분류·단위 매핑",
    "validation": "규칙 검증",
    "duplicate": "중복 조회",
    "reviewer": "등록 검토",
    "registration": "제품 저장",
}


def attribute_rows(state):
    product = state.get("normalized_product", {})
    mapping = state.get("ontology_mapping", {})
    required = mapping.get("required_properties", {})
    keys = list(
        dict.fromkeys(
            [
                *required,
                *mapping.get("optional_properties", {}),
                *product.get("attributes", {}),
            ]
        )
    )
    rows = []
    for key in keys:
        attr = product.get("attributes", {}).get(key, {})
        confidence = attr.get("confidence")
        rows.append(
            {
                "항목": LABELS.get(key, key),
                "필수": "●" if key in required else "",
                "값": "—" if attr.get("value") is None else str(attr["value"]),
                "단위": attr.get("unit") or "—",
                "출처": attr.get("provenance") or "—",
                "AI 신뢰도": f"{confidence:.0%}" if confidence is not None else "—",
            }
        )
    return rows


def parse_value(text, property_type):
    if not text.strip():
        return None
    if property_type == "string":
        return text
    if property_type == "boolean":
        return {"예": True, "아니오": False}[text]
    if property_type == "integer":
        return int(text)
    number = float(text)
    if not math.isfinite(number):
        raise ValueError("숫자는 유한한 값이어야 합니다.")
    return int(number) if number.is_integer() else number
