"""
PubChem PUG REST API - 접속 확인용 최소 예시
proxy 허용 요청 목적으로 작성된 독립 실행 스크립트

접속 도메인: pubchem.ncbi.nlm.nih.gov (HTTPS, 443)
"""

import requests
import json
import csv
import time
from pathlib import Path

BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
DELAY    = 0.5   # 요청 간격 (초)

# 테스트 화합물 3종
COMPOUNDS = [
    {"identifier": "R-134a",  "search_name": "1,1,1,2-Tetrafluoroethane"},
    {"identifier": "Acetone", "search_name": "acetone"},
    {"identifier": "Benzene", "search_name": "benzene"},
]


def step1_get_cid(name: str) -> dict:
    """
    [STEP 1] 화합물 이름 → CID 조회
    URL: GET /compound/name/{name}/cids/JSON
    """
    url = f"{BASE_URL}/compound/name/{requests.utils.quote(name)}/cids/JSON"
    print(f"\n[STEP 1] CID 조회")
    print(f"  URL: {url}")

    resp = requests.get(url, timeout=10)
    print(f"  HTTP Status: {resp.status_code}")

    raw = resp.json()
    cid = raw["IdentifierList"]["CID"][0]
    print(f"  CID: {cid}")

    # raw 응답 저장
    Path("raw_responses").mkdir(exist_ok=True)
    with open(f"raw_responses/step1_cid_{name.replace(' ','_')}.json", "w") as f:
        json.dump(raw, f, indent=2)

    return {"cid": cid, "raw": raw}


def step2_get_properties(cid: int, name: str) -> dict:
    """
    [STEP 2] CID → 분자구조 속성 조회
    URL: GET /compound/cid/{cid}/property/{fields}/JSON
    """
    fields = ",".join([
        "CanonicalSMILES",
        "IsomericSMILES",
        "InChI",
        "InChIKey",
        "MolecularFormula",
        "MolecularWeight",
        "IUPACName",
        "XLogP",
        "HeavyAtomCount",
    ])
    url = f"{BASE_URL}/compound/cid/{cid}/property/{fields}/JSON"
    print(f"\n[STEP 2] 분자구조 속성 조회")
    print(f"  URL: {url}")

    resp = requests.get(url, timeout=10)
    print(f"  HTTP Status: {resp.status_code}")

    raw = resp.json()
    props = raw["PropertyTable"]["Properties"][0]

    with open(f"raw_responses/step2_props_{name.replace(' ','_')}.json", "w") as f:
        json.dump(raw, f, indent=2)

    return {"props": props, "raw": raw}


def step3_get_sdf(cid: int, name: str) -> str:
    """
    [STEP 3] CID → 2D SDF 파일 다운로드
    URL: GET /compound/cid/{cid}/SDF
    """
    url = f"{BASE_URL}/compound/cid/{cid}/SDF"
    print(f"\n[STEP 3] SDF 다운로드")
    print(f"  URL: {url}")

    resp = requests.get(url, timeout=10)
    print(f"  HTTP Status: {resp.status_code}")
    print(f"  SDF size: {len(resp.text)} chars")

    with open(f"raw_responses/step3_sdf_{name.replace(' ','_')}.sdf", "w") as f:
        f.write(resp.text)

    return resp.text


def main():
    results = []

    for comp in COMPOUNDS:
        identifier  = comp["identifier"]
        search_name = comp["search_name"]
        print(f"\n{'='*60}")
        print(f"화합물: {identifier}  (검색명: {search_name})")
        print(f"{'='*60}")

        # Step 1: CID
        r1 = step1_get_cid(search_name)
        cid = r1["cid"]
        time.sleep(DELAY)

        # Step 2: 분자구조
        r2 = step2_get_properties(cid, search_name)
        props = r2["props"]
        time.sleep(DELAY)

        # Step 3: SDF
        step3_get_sdf(cid, search_name)
        time.sleep(DELAY)

        results.append({
            "identifier":      identifier,
            "search_name":     search_name,
            "cid":             cid,
            "MolecularFormula": props.get("MolecularFormula"),
            "MolecularWeight":  props.get("MolecularWeight"),
            "CanonicalSMILES":  props.get("CanonicalSMILES"),
            "IsomericSMILES":   props.get("IsomericSMILES"),
            "InChI":            props.get("InChI"),
            "InChIKey":         props.get("InChIKey"),
            "IUPACName":        props.get("IUPACName"),
            "XLogP":            props.get("XLogP"),
            "HeavyAtomCount":   props.get("HeavyAtomCount"),
        })

    # CSV 저장
    with open("output.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\n\n결과 저장: output.csv ({len(results)}행)")


if __name__ == "__main__":
    main()
