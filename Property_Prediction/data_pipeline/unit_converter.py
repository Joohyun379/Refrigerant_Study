"""
물성 단위 통일 유틸리티
PubChem에서 가져온 값들은 출처마다 단위가 다를 수 있으므로 SI 단위로 정규화
"""

import pandas as pd


# ---------------------------------------------------------------------------
# 온도 → K
# ---------------------------------------------------------------------------

def temp_to_K(value: float, unit: str) -> float:
    unit = (unit or "").strip().upper()
    if unit in ("K", "KELVIN"):
        return value
    if unit in ("C", "°C", "CELSIUS", "DEG C"):
        return value + 273.15
    if unit in ("F", "°F", "FAHRENHEIT", "DEG F"):
        return (value - 32) * 5 / 9 + 273.15
    if unit in ("R", "RANKINE"):
        return value * 5 / 9
    # 단위 불명확 → 값이 합리적 범위(100~1000 K)면 K로 간주
    if 100 <= value <= 1500:
        return value
    raise ValueError(f"Unknown temperature unit: '{unit}' for value {value}")


# ---------------------------------------------------------------------------
# 압력 → MPa
# ---------------------------------------------------------------------------

def pressure_to_MPa(value: float, unit: str) -> float:
    unit = (unit or "").strip().upper()
    conversions = {
        "MPA":   1.0,
        "KPA":   1e-3,
        "PA":    1e-6,
        "BAR":   0.1,
        "MBAR":  1e-4,
        "ATM":   0.101325,
        "TORR":  0.101325 / 760,
        "MMHG":  0.101325 / 760,
        "PSI":   0.00689476,
        "PSIA":  0.00689476,
        "BAR":   0.1,
    }
    if unit in conversions:
        return value * conversions[unit]
    # 단위 불명확 → 값이 합리적 범위면 MPa 간주
    if 0.01 <= value <= 1000:
        return value
    raise ValueError(f"Unknown pressure unit: '{unit}' for value {value}")


# ---------------------------------------------------------------------------
# DataFrame 정규화
# ---------------------------------------------------------------------------

def normalize_units(df: pd.DataFrame) -> pd.DataFrame:
    """
    수집된 DataFrame의 단위를 통일
    - critical_temperature → K
    - critical_pressure    → MPa
    - acentric_factor      → 무차원 (변환 불필요)
    """
    df = df.copy()

    # 임계온도
    if "critical_temperature" in df.columns:
        df["Tc_K"] = df.apply(
            lambda r: _safe_convert(temp_to_K, r["critical_temperature"], r.get("critical_temperature_unit")),
            axis=1,
        )

    # 임계압력
    if "critical_pressure" in df.columns:
        df["Pc_MPa"] = df.apply(
            lambda r: _safe_convert(pressure_to_MPa, r["critical_pressure"], r.get("critical_pressure_unit")),
            axis=1,
        )

    # 이심인자 (단위 없음)
    if "acentric_factor" in df.columns:
        df["omega"] = pd.to_numeric(df["acentric_factor"], errors="coerce")

    return df


def _safe_convert(func, value, unit):
    try:
        if pd.isna(value):
            return None
        return func(float(value), str(unit) if unit else "")
    except Exception:
        return None
