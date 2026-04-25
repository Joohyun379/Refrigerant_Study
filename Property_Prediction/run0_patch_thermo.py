"""
기존 raw CSV의 분자구조 데이터를 보존하면서
thermo 데이터만 재적용하는 패치 스크립트
"""
import pandas as pd
from pathlib import Path
from data_pipeline.coolprop_fetcher import get_coolprop_properties
from data_pipeline.nist_fetcher import get_nist_properties
from data_pipeline.manual_props import get_manual_properties
from data_pipeline.manual_smiles import get_manual_smiles, get_invalid_reason
from data_pipeline.validate import validate, report
import logging, time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUEST_DELAY = 0.3


def patch_thermo(raw_path: str, processed_path: str, nist_for_missing: bool = True):
    df = pd.read_csv(raw_path)
    logger.info(f"Loaded {len(df)} rows from {raw_path}")

    thermo_cols = ["Tc_K", "Pc_MPa", "omega", "source_thermo"]
    updated = 0

    for idx, row in df.iterrows():
        identifier = row["identifier"]

        # 1) CoolProp 우선
        thermo = get_coolprop_properties(identifier)
        if thermo["Tc_K"] is not None:
            source = "CoolProp"
        else:
            # 2) Manual 문헌값
            manual = get_manual_properties(identifier)
            if all(manual[k] is not None for k in ("Tc_K", "Pc_MPa", "omega")):
                thermo = manual
                source = "Manual"
            else:
                # 3) NIST (기존에 이미 fetched → 재사용, 단 누락분 보완)
                existing_tc = row.get("Tc_K")
                existing_pc = row.get("Pc_MPa")
                existing_om = row.get("omega")

                # 현재 행에 이미 thermo가 있으면 그대로 + manual 보완만
                if pd.notna(existing_tc) or pd.notna(existing_pc) or pd.notna(existing_om):
                    thermo = {
                        "Tc_K":   existing_tc if pd.notna(existing_tc) else None,
                        "Pc_MPa": existing_pc if pd.notna(existing_pc) else None,
                        "omega":  existing_om if pd.notna(existing_om) else None,
                    }
                    # manual 보완
                    filled = []
                    for key in ("Tc_K", "Pc_MPa", "omega"):
                        if thermo[key] is None and manual.get(key) is not None:
                            thermo[key] = manual[key]
                            filled.append(key)
                    source = ("NIST+Manual" if filled else
                              row.get("source_thermo", "NIST"))
                elif nist_for_missing:
                    # 완전 누락 → NIST 재시도
                    logger.info(f"  [{identifier}] NIST 재조회 중...")
                    thermo = get_nist_properties(identifier)
                    source = "NIST"
                    # manual 보완
                    filled = []
                    for key in ("Tc_K", "Pc_MPa", "omega"):
                        if thermo[key] is None and manual.get(key) is not None:
                            thermo[key] = manual[key]
                            filled.append(key)
                    if filled:
                        source = "NIST+Manual"
                    time.sleep(REQUEST_DELAY)
                else:
                    thermo = {"Tc_K": None, "Pc_MPa": None, "omega": None}
                    source = "NIST"

        # Manual SMILES 덮어쓰기 (항상 재적용)
        manual_smi = get_manual_smiles(identifier)
        if manual_smi is not None:
            df.at[idx, "SMILES"]             = manual_smi["smiles"]
            df.at[idx, "ConnectivitySMILES"] = manual_smi["connectivity"]
            df.at[idx, "InChIKey"]           = manual_smi["inchikey"]
            df.at[idx, "InChI"]              = manual_smi["inchi"]
            df.at[idx, "smiles_source"]      = "Manual"
        elif pd.isna(df.at[idx, "smiles_source"]):
            df.at[idx, "smiles_source"] = "PubChem" if pd.notna(df.at[idx, "CID"]) else None

        # has_stereo 재계산
        smi = df.at[idx, "SMILES"]
        df.at[idx, "has_stereo"] = (
            ("/" in smi or "\\" in smi or "@" in smi) if pd.notna(smi) else None
        )

        # 업데이트가 필요한지 확인
        changed = (
            df.at[idx, "source_thermo"] != source or
            df.at[idx, "Tc_K"] != thermo["Tc_K"] or
            df.at[idx, "Pc_MPa"] != thermo["Pc_MPa"] or
            df.at[idx, "omega"] != thermo["omega"]
        )
        if changed:
            df.at[idx, "Tc_K"] = thermo["Tc_K"]
            df.at[idx, "Pc_MPa"] = thermo["Pc_MPa"]
            df.at[idx, "omega"] = thermo["omega"]
            df.at[idx, "source_thermo"] = source
            updated += 1
            logger.info(f"  [{identifier}] {source}: Tc={thermo['Tc_K']} Pc={thermo['Pc_MPa']} ω={thermo['omega']}")

    logger.info(f"Updated {updated} rows")
    df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved patched raw: {raw_path}")

    # validate and save processed
    df_valid = validate(df)

    # INVALID_COMPOUNDS 강제 invalid 처리
    for idx, row in df_valid.iterrows():
        reason = get_invalid_reason(row["identifier"])
        if reason is not None:
            df_valid.at[idx, "valid"] = False
            df_valid.at[idx, "validation_notes"] = reason
            logger.warning(f"  [Invalid] {row['identifier']}: {reason}")

    report(df_valid)
    df_valid.to_csv(processed_path, index=False, encoding="utf-8-sig")
    logger.info(f"Saved processed: {processed_path}")

    # 여전히 invalid인 행 출력
    inv = df_valid[~df_valid["valid"]]
    print(f"\nInvalid ({len(inv)}):")
    print(inv[["identifier", "label", "group", "Tc_K", "Pc_MPa", "omega",
               "source_thermo", "validation_notes"]].to_string())


if __name__ == "__main__":
    patch_thermo(
        raw_path="data/raw/refrigerants_raw.csv",
        processed_path="data/processed/refrigerants_final.csv",
        nist_for_missing=True,
    )
