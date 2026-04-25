"""
전체 데이터 파이프라인 실행 스크립트
  1. compound_list.py 에서 화합물 목록 로드 (label, group 포함)
  2. PubChem  → 분자구조 (SMILES, InChI, 분자량 등)
  3. CoolProp → 열역학 물성 (Tc, Pc, ω)
  4. 데이터 품질 검증
  5. 최종 CSV 저장
"""

import pandas as pd
import time
import logging
from pathlib import Path

from data_pipeline.compound_list import get_all_compounds
from data_pipeline.pubchem_fetcher import fetch_compound_data, get_2d_sdf
from data_pipeline.coolprop_fetcher import get_coolprop_properties
from data_pipeline.nist_fetcher import get_nist_properties
from data_pipeline.manual_props import get_manual_properties
from data_pipeline.manual_smiles import get_manual_smiles, get_invalid_reason
from data_pipeline.validate import validate, report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUEST_DELAY = 0.3


def main():
    raw_path       = "data/raw/refrigerants_raw.csv"
    processed_path = "data/processed/refrigerants_final.csv"
    sdf_dir        = Path("data/raw/sdf")

    compounds = get_all_compounds()
    logger.info(f"총 {len(compounds)}종 수집 시작 "
                f"(정례={sum(c['label']==1 for c in compounds)}, "
                f"반례={sum(c['label']==0 for c in compounds)})")

    records = []
    for i, entry in enumerate(compounds):
        identifier = entry["identifier"]
        logger.info(f"[{i+1}/{len(compounds)}] {identifier} (label={entry['label']}, group={entry['group']})")

        # PubChem: 분자구조
        record = fetch_compound_data(identifier, id_type="name")

        # Manual SMILES 덮어쓰기 (PubChem 오류/미제공 대응)
        manual_smi = get_manual_smiles(identifier)
        if manual_smi is not None:
            record["SMILES"]             = manual_smi["smiles"]
            record["ConnectivitySMILES"] = manual_smi["connectivity"]
            record["InChIKey"]           = manual_smi["inchikey"]
            record["InChI"]              = manual_smi["inchi"]
            record["smiles_source"]      = "Manual"
            logger.info(f"  [Manual SMILES] {identifier}: {manual_smi['reason']}")
        else:
            record["smiles_source"] = "PubChem" if record.get("cid") else None

        # has_stereo: SMILES에 입체화학 표기 포함 여부
        smi = record.get("SMILES")
        record["has_stereo"] = (
            ("/" in smi or "\\" in smi or "@" in smi) if smi else None
        )

        # SDF 저장
        if record.get("cid"):
            time.sleep(REQUEST_DELAY)
            sdf_text = get_2d_sdf(record["cid"])
            if sdf_text:
                sdf_path = sdf_dir / f"{record['cid']}.sdf"
                sdf_path.parent.mkdir(parents=True, exist_ok=True)
                sdf_path.write_text(sdf_text)

        # CoolProp: 열역학 물성
        thermo = get_coolprop_properties(identifier)

        # CoolProp 실패 시 fallback 체인: Manual (권위 문헌) → NIST WebBook
        if thermo["Tc_K"] is None:
            # 문헌값 직접 입력 데이터가 있으면 우선 사용 (NIST 오류값 방지)
            manual = get_manual_properties(identifier)
            if all(manual[k] is not None for k in ("Tc_K", "Pc_MPa", "omega")):
                logger.info(f"  CoolProp 없음 → 문헌값 사용: {identifier}")
                thermo = manual
                record["source_thermo"] = "Manual"
            else:
                # NIST WebBook HTML 파싱
                logger.info(f"  CoolProp 없음 → NIST WebBook 조회: {identifier}")
                thermo = get_nist_properties(identifier)
                record["source_thermo"] = "NIST"

                # NIST에서도 일부 누락 시 문헌값으로 보완
                if thermo["Tc_K"] is None or thermo["Pc_MPa"] is None or thermo["omega"] is None:
                    filled = []
                    for key in ("Tc_K", "Pc_MPa", "omega"):
                        if thermo[key] is None and manual[key] is not None:
                            thermo[key] = manual[key]
                            filled.append(key)
                    if filled:
                        logger.info(f"  문헌값 보완 ({identifier}): {filled}")
                        record["source_thermo"] = "NIST+Manual"
        else:
            record["source_thermo"] = "CoolProp"

        record.update(thermo)

        # label, group 추가
        record["label"] = entry["label"]
        record["group"] = entry["group"]

        records.append(record)
        time.sleep(REQUEST_DELAY)

    df_raw = pd.DataFrame(records)
    Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
    df_raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
    logger.info(f"원본 저장: {raw_path}")

    # 검증
    print("\n>>> 데이터 품질 검증...")
    df_valid = validate(df_raw)

    # INVALID_COMPOUNDS 강제 invalid 처리
    for idx, row in df_valid.iterrows():
        reason = get_invalid_reason(row["identifier"])
        if reason is not None:
            df_valid.at[idx, "valid"] = False
            df_valid.at[idx, "validation_notes"] = reason
            logger.warning(f"  [Invalid] {row['identifier']}: {reason}")

    report(df_valid)

    # 저장
    Path(processed_path).parent.mkdir(parents=True, exist_ok=True)
    df_valid.to_csv(processed_path, index=False, encoding="utf-8-sig")
    logger.info(f"최종 저장: {processed_path}")

    # 미리보기
    key_cols = ["identifier", "label", "group", "MolecularFormula",
                "Tc_K", "Pc_MPa", "omega", "valid"]
    print("\n=== 최종 데이터 미리보기 ===")
    print(df_valid[[c for c in key_cols if c in df_valid.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
