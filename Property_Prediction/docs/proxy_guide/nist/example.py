"""
NIST WebBook HTML 파싱 - 접속 확인용 최소 예시
proxy 허용 요청 목적으로 작성된 독립 실행 스크립트

접속 도메인: webbook.nist.gov (HTTPS, 443)
"""

import requests
import math
import re
import csv
import time
from pathlib import Path
from bs4 import BeautifulSoup

SEARCH_URL = "https://webbook.nist.gov/cgi/cbook.cgi"
FLUID_URL  = "https://webbook.nist.gov/cgi/fluid.cgi"
DELAY      = 0.5

# 테스트 화합물 3종
# - Propane: fluid.cgi 지원 (직접 API)
# - Acetone: fluid.cgi 미지원 → Antoine 방정식 fallback
# - 1-Propanol: fluid.cgi 미지원 → Antoine 방정식 fallback
COMPOUNDS = [
    {"identifier": "Propane",    "search_name": "propane"},
    {"identifier": "Acetone",    "search_name": "acetone"},
    {"identifier": "1-Propanol", "search_name": "1-propanol"},
]


def step1_get_nist_id(search_name: str) -> dict:
    """
    [STEP 1] 화합물명 검색 → NIST ID 추출
    URL: GET https://webbook.nist.gov/cgi/cbook.cgi?Name={name}&Units=SI
    """
    url    = f"{SEARCH_URL}?Name={requests.utils.quote(search_name)}&Units=SI"
    params = {"Name": search_name, "Units": "SI"}
    print(f"\n[STEP 1] NIST ID 검색")
    print(f"  URL: {SEARCH_URL}?Name={search_name}&Units=SI")

    resp = requests.get(SEARCH_URL, params=params, timeout=15)
    print(f"  HTTP Status: {resp.status_code}")

    # raw HTML 저장
    Path("raw_responses").mkdir(exist_ok=True)
    with open(f"raw_responses/step1_search_{search_name.replace(' ','_')}.html",
              "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"  Raw HTML saved → raw_responses/step1_search_{search_name}.html")

    soup = BeautifulSoup(resp.text, "html.parser")

    # "Phase change data" 링크에서 ID 추출 (가장 신뢰)
    nist_id = None
    for a in soup.find_all("a", href=True):
        if "phase change" in a.get_text(strip=True).lower():
            m = re.search(r"ID=(C\d+)", a["href"])
            if m:
                nist_id = m.group(1)
                break

    # fallback: 최빈 ID
    if nist_id is None:
        from collections import Counter
        counts = Counter()
        for a in soup.find_all("a", href=re.compile(r"ID=C\d+")):
            m = re.search(r"ID=(C\d+)", a["href"])
            if m:
                counts[m.group(1)] += 1
        if counts:
            nist_id = counts.most_common(1)[0][0]

    print(f"  NIST ID: {nist_id}")
    return {"nist_id": nist_id}


def step2_get_phase_page(nist_id: str) -> dict:
    """
    [STEP 2] Phase Change Data 페이지 → Tc, Pc 파싱
    URL: GET https://webbook.nist.gov/cgi/cbook.cgi?ID={nist_id}&Units=SI&Mask=4
    """
    params = {"ID": nist_id, "Units": "SI", "Mask": "4"}
    print(f"\n[STEP 2] Phase Change 페이지 (Tc, Pc)")
    print(f"  URL: {SEARCH_URL}?ID={nist_id}&Units=SI&Mask=4")

    resp = requests.get(SEARCH_URL, params=params, timeout=15)
    print(f"  HTTP Status: {resp.status_code}")

    with open(f"raw_responses/step2_phase_{nist_id}.html",
              "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"  Raw HTML saved → raw_responses/step2_phase_{nist_id}.html")

    soup = BeautifulSoup(resp.text, "html.parser")

    Tc_K = Pc_MPa = None
    antoine_rows = []

    for table in soup.find_all("table"):
        # Tc, Pc 파싱
        for row in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 3:
                continue

            qty   = cells[0].strip()
            val_s = cells[1]
            unit  = cells[2].strip()

            m = re.match(r"([\d.]+)", val_s.replace(",", ""))
            if not m:
                continue
            val = float(m.group(1))

            if qty == "Tc" and Tc_K is None:
                if unit.lower() == "k":
                    Tc_K = round(val, 4)
            elif qty == "Pc" and Pc_MPa is None:
                if unit.lower() == "bar":
                    Pc_MPa = round(val * 0.1, 6)
                elif "mpa" in unit.lower():
                    Pc_MPa = round(val, 6)

        # Antoine 계수 테이블 수집
        rows = table.find_all("tr")
        if rows:
            headers = [td.get_text(strip=True) for td in rows[0].find_all(["td","th"])]
            if "A" in headers and "B" in headers and "C" in headers:
                a_i, b_i, c_i = headers.index("A"), headers.index("B"), headers.index("C")
                for row in rows[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all("td")]
                    if len(cells) > max(a_i, b_i, c_i):
                        try:
                            antoine_rows.append({
                                "T_range": cells[0],
                                "A": float(cells[a_i]),
                                "B": float(cells[b_i]),
                                "C": float(cells[c_i]),
                            })
                        except ValueError:
                            pass

    print(f"  Tc = {Tc_K} K")
    print(f"  Pc = {Pc_MPa} MPa")
    print(f"  Antoine rows: {len(antoine_rows)}")
    for r in antoine_rows:
        print(f"    T={r['T_range']}  A={r['A']}  B={r['B']}  C={r['C']}")

    return {"soup": soup, "Tc_K": Tc_K, "Pc_MPa": Pc_MPa, "antoine_rows": antoine_rows}


def step3a_fluid_api(nist_id: str, Tc_K: float) -> dict:
    """
    [STEP 3-A] fluid.cgi 포화 증기압 API  (Tr = 0.7)
    URL: GET https://webbook.nist.gov/cgi/fluid.cgi?Action=Load&ID={id}&Type=SatT&...
    ※ 알코올/케톤 등은 NIST 유체 DB 미수록 → 400 에러 → Step 3-B로 전환
    """
    T_ref = round(0.7 * Tc_K, 2)
    url = (
        f"{FLUID_URL}?Action=Load&ID={nist_id}&Type=SatT&Digits=5"
        f"&THigh={T_ref}&TLow={T_ref}&TInc=1&RefState=DEF"
        f"&TUnit=K&PUnit=MPa&DUnit=mol%2Fl&HUnit=kJ%2Fmol"
        f"&WUnit=m%2Fs&VisUnit=uPa*s&STUnit=N%2Fm"
    )
    print(f"\n[STEP 3-A] fluid.cgi 포화 증기압  (T_ref={T_ref} K = 0.7×Tc)")
    print(f"  URL: {url}")

    resp = requests.get(url, timeout=15)
    print(f"  HTTP Status: {resp.status_code}")

    fname = f"raw_responses/step3a_fluid_{nist_id}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"  Raw HTML saved → {fname}")

    if not resp.ok:
        print(f"  → 유체 DB 미수록 (400). Step 3-B(Antoine)로 전환")
        return {"psat": None, "T_ref": T_ref}

    soup = BeautifulSoup(resp.text, "html.parser")
    psat = None
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        hdrs = [td.get_text(strip=True).lower() for td in rows[0].find_all(["th","td"])]
        p_idx = next((i for i,h in enumerate(hdrs) if "pressure" in h), None)
        if p_idx is None:
            continue
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) > p_idx:
                try:
                    psat = float(cells[p_idx])
                    break
                except ValueError:
                    pass
        if psat:
            break

    print(f"  Psat({T_ref} K) = {psat} MPa")
    return {"psat": psat, "T_ref": T_ref}


def step3b_antoine(antoine_rows: list, T_ref: float) -> dict:
    """
    [STEP 3-B] Antoine 방정식으로 Psat 계산  (fluid.cgi 실패 시 fallback)
    log₁₀(P/bar) = A - B / (T/K + C)
    """
    print(f"\n[STEP 3-B] Antoine 방정식 fallback  (T_ref={T_ref} K)")

    # T_ref에 가장 가까운 Antoine 계수 선택
    best = None
    best_dist = float("inf")
    for row in antoine_rows:
        nums = re.findall(r"[\d.]+", row["T_range"])
        t_low  = float(nums[0]) if len(nums) >= 1 else None
        t_high = float(nums[1]) if len(nums) >= 2 else t_low
        if t_low and t_high:
            dist = 0 if t_low <= T_ref <= t_high else min(abs(T_ref-t_low), abs(T_ref-t_high))
            if dist < best_dist:
                best_dist = dist
                best = row

    if best is None:
        print("  Antoine 계수 없음")
        return {"psat": None}

    A, B, C = best["A"], best["B"], best["C"]
    log_p   = A - B / (T_ref + C)
    psat    = (10 ** log_p) * 0.1   # bar → MPa

    print(f"  사용 Antoine: T={best['T_range']}  A={A}  B={B}  C={C}")
    print(f"  log10(P/bar) = {A} - {B}/({T_ref}+({C})) = {log_p:.4f}")
    print(f"  Psat = 10^{log_p:.4f} × 0.1 MPa = {psat:.5f} MPa")
    return {"psat": psat, "method": "Antoine", "A": A, "B": B, "C": C}


def main():
    results = []

    for comp in COMPOUNDS:
        identifier  = comp["identifier"]
        search_name = comp["search_name"]
        print(f"\n{'='*60}")
        print(f"화합물: {identifier}")
        print(f"{'='*60}")

        # Step 1
        r1 = step1_get_nist_id(search_name)
        nist_id = r1["nist_id"]
        time.sleep(DELAY)

        # Step 2
        r2 = step2_get_phase_page(nist_id)
        Tc_K, Pc_MPa = r2["Tc_K"], r2["Pc_MPa"]
        antoine_rows = r2["antoine_rows"]
        time.sleep(DELAY)

        # Step 3-A
        r3a = step3a_fluid_api(nist_id, Tc_K)
        psat   = r3a["psat"]
        T_ref  = r3a["T_ref"]
        method = "fluid_api"
        ant_A = ant_B = ant_C = None
        time.sleep(DELAY)

        # Step 3-B fallback
        if psat is None:
            r3b   = step3b_antoine(antoine_rows, T_ref)
            psat  = r3b.get("psat")
            method = r3b.get("method", "Antoine")
            ant_A  = r3b.get("A")
            ant_B  = r3b.get("B")
            ant_C  = r3b.get("C")

        # ω 계산
        omega = None
        if psat and Pc_MPa:
            omega = round(-math.log10(psat / Pc_MPa) - 1, 6)

        print(f"\n  최종: Tc={Tc_K} K, Pc={Pc_MPa} MPa, ω={omega}  (method={method})")

        results.append({
            "identifier":   identifier,
            "nist_id":      nist_id,
            "Tc_K":         Tc_K,
            "Pc_MPa":       Pc_MPa,
            "T_ref_K":      T_ref,
            "Psat_MPa":     round(psat, 6) if psat else None,
            "omega":        omega,
            "omega_method": method,
            "Antoine_A":    ant_A,
            "Antoine_B":    ant_B,
            "Antoine_C":    ant_C,
        })

    # CSV
    with open("output.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"\n\n결과 저장: output.csv ({len(results)}행)")


if __name__ == "__main__":
    main()
