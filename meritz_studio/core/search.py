"""자연어 검색.

이용자가 쓰는 말과 api_type 을 잇는다. 긴 별칭이 짧은 것보다 먼저다 —
"실시간 체결통보" 가 "체결" 에 먼저 걸리면 엉뚱한 것이 나온다.
"""
from __future__ import annotations

ALIASES: dict[str, list[str]] = {
    # 계좌
    "잔고": ["holdings", "ovs_holdings"], "보유종목": ["holdings"], "포지션": ["holdings"],
    "자산": ["valuation"], "평가": ["valuation", "holdings"],
    "예수금": ["deposit"], "출금가능": ["deposit"], "담보": ["collateral"],
    "거래내역": ["transactions"], "입출금": ["transactions"],
    "외화잔고": ["ovs_currencies"],
    # 시세
    "현재가": ["market_prices"], "시세": ["market_prices", "market_orderbook"],
    "호가": ["market_orderbook"], "오더북": ["market_orderbook"],
    "체결추이": ["market_trades_ticks", "market_trades_minutes"],
    "차트": ["market_candles_days", "market_candles_minutes"],
    "일봉": ["market_candles_days"], "분봉": ["market_candles_minutes"],
    "틱": ["market_trades_ticks"],
    "시간외": ["market_prices_after", "market_orderbook_after"],
    "시간외단일가": ["market_prices_after", "market_orderbook_after"],
    # 주문
    "매수": ["orders_buy"], "매도": ["orders_sell"],
    "주문": ["orders_history", "orders_buy", "orders_sell"],
    "정정": ["orders_modify", "ovs_orders_modify"],
    "취소": ["orders_cancel", "ovs_orders_cancel"],
    "주문취소": ["orders_cancel", "ovs_orders_cancel"],
    "주문정정": ["orders_modify", "ovs_orders_modify"],
    "주문내역": ["orders_history"], "미체결": ["orders_history"],
    "주문가능금액": ["orders_estimate"], "주문가능수량": ["orders_estimate"],
    "매수가능": ["orders_estimate"],
    "신용": ["credit_orders_buy", "credit_orders_sell"],
    "신용매수": ["credit_orders_buy"], "신용매도": ["credit_orders_sell"],
    # 해외
    "해외현재가": ["ovs_market_prices"], "해외호가": ["ovs_market_orderbook"],
    "해외잔고": ["ovs_holdings"], "해외매수": ["ovs_orders_buy"],
    "해외매도": ["ovs_orders_sell"], "해외주문내역": ["ovs_orders_history"],
    "거래소": ["ref_ovs_exchanges"],
    # 환전
    "환전": ["fx_exchanges"], "환율": ["fx_rates", "fx_rates_applied"],
    "고시환율": ["fx_rates"], "적용환율": ["fx_rates_applied"],
    "환전내역": ["fx_exchanges_history"],
    # 실시간
    "실시간": ["ws_stck_cntg", "ws_stck_aspr", "ws_cntg_rslt"],
    "실시간현재가": ["ws_stck_cntg"], "실시간시세": ["ws_stck_cntg"],
    "실시간호가": ["ws_stck_aspr"],
    "실시간체결통보": ["ws_cntg_rslt"], "실시간주문통보": ["ws_cntg_infr"],
    "체결통보": ["ws_cntg_rslt"], "주문통보": ["ws_cntg_infr"],
    "실시간해외": ["ws_exst_cntg", "ws_exst_cntd", "ws_exst_aspr"],
    "nxt": ["ws_nxt_cntg"], "sor": ["ws_unt_cntg"],
}

CATEGORY_KO = {
    "account": "계좌", "domestic_market": "국내주식 시세", "trading": "주문",
    "forex": "환전", "reference": "기준정보", "realtime": "실시간(웹소켓)",
    "overseas_market": "해외주식 시세",
}


def text_of(api) -> str:
    parts = [api.key, api.name, api["category"], api.path, api["tr_id"],
             CATEGORY_KO.get(api["category"], ""), (api.get("description") or "")[:400]]
    parts += [p.get("name_ko") or "" for p in api.params]
    return " ".join(parts)


# 범위를 좁히는 말. 별칭이 아니라 **필터**로 쓴다.
#   "해외 주문 취소" 에서 "주문"·"취소" 별칭이 국내 API 를 먼저 물어오는 것을 막는다.
SCOPES = {
    "해외": lambda a: "overseas" in a.path or a.key.startswith(("ovs_", "ws_exst_")),
    "외화": lambda a: a["category"] == "forex" or "currencies" in a.path,
    "국내": lambda a: "overseas" not in a.path and not a.key.startswith("ovs_"),
    "실시간": lambda a: a.is_websocket,
}
# 행위를 지목하는 말. 이 말이 없으면 상태변경 API 를 앞에 두지 않는다.
ACTION_WORDS = ("매수", "매도", "주문", "정정", "취소", "환전", "신청", "체결")


def search(catalog, keyword: str, category: str | None = None) -> list[dict]:
    kw = (keyword or "").replace(" ", "").lower()
    if not kw:
        return []

    # 질의에 범위어가 있으면 그 범위 밖은 아예 뺀다
    scopes = [f for w, f in SCOPES.items() if w.replace(" ", "").lower() in kw]
    # 행위어가 없는데 상태변경 API 를 먼저 보여주면 위험하다
    wants_action = any(w in kw for w in ACTION_WORDS)

    hits: list[dict] = []
    seen: set[str] = set()

    def add(api, why: str):
        if api.key in seen or (category and api["category"] != category):
            return
        if scopes and not all(f(api) for f in scopes):
            return
        if api.is_state_changing and not wants_action:
            return
        seen.add(api.key)
        h = {"api_type": api.key, "name": api.name, "category": api["category"],
             "category_ko": CATEGORY_KO.get(api["category"], ""),
             "method": api.method, "api_path": api.path, "tr_id": api["tr_id"],
             "is_websocket": api.is_websocket, "matched": why}
        if api.is_state_changing:
            h["state_changing"] = True
            h["caution"] = "실제 주문·환전입니다. 생성 코드는 confirm=True 전까지 보내지 않습니다."
        if catalog.corrections_for(api.key):
            h["response_handling_note"] = [c["kind"] for c in catalog.corrections_for(api.key)]
        hits.append(h)

    # 질의에 구체적인 행위어가 있으면 넓은 별칭("주문")은 쓰지 않는다.
    # "주문 정정" 에서 "주문" 이 매수·매도를 먼저 물어오는 것을 막는다.
    SPECIFIC = ("매수", "매도", "정정", "취소", "환전", "체결통보", "가능")
    narrow = any(w in kw for w in SPECIFIC)

    # 별칭 순위
    #   ① 정확히 같은 말        "매수" → orders_buy
    #   ② 질의가 별칭을 포함     "삼성전자 현재가" → market_prices
    #   ③ 별칭이 질의를 포함     "매수" → "매수가능"
    # ②·③ 안에서는 긴 별칭이 먼저다 — 더 구체적인 뜻이다.
    def rank(word: str) -> tuple[int, int]:
        w = word.replace(" ", "").lower()
        if w == kw:
            return (0, 0)
        if w in kw:
            return (1, -len(w))
        return (2, -len(w))

    for word, types in sorted(ALIASES.items(), key=lambda kv: rank(kv[0])):
        w = word.replace(" ", "").lower()
        if narrow and w == "주문" and kw != "주문":
            continue
        if w in kw or kw in w:
            for t in types:
                api = catalog.get(t)
                if api:
                    add(api, f"별칭 '{word}'")

    for api in catalog:
        if kw in text_of(api).replace(" ", "").lower():
            add(api, "본문")

    # 범위어가 걸러낸 결과가 하나도 없으면 범위를 풀어 다시 본다.
    # 빈 결과보다는 넓은 결과가 낫다.
    if not hits and scopes:
        scopes.clear()
        for word, types in sorted(ALIASES.items(), key=lambda kv: rank(kv[0])):
            w = word.replace(" ", "").lower()
            if w in kw or kw in w:
                for t in types:
                    if catalog.get(t):
                        add(catalog.get(t), f"별칭 '{word}' (범위 완화)")
        for api in catalog:
            if kw in text_of(api).replace(" ", "").lower():
                add(api, "본문 (범위 완화)")
    return hits
