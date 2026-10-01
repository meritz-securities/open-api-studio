# API 목록 (75건)

개발자 포털 기준 명세다. 기준일 2026-09-22 · 출처 메리츠증권 개발자 포털 등록 명세

`⚠` 는 상태를 바꾸는 요청이다 — 미리보기와 사용자 확인 없이 실행하지 않는다.

## oauth2

| api_type | 호출 | 이름 |
|---|---|---|
| `oauth2_revoke` | POST /oauth2/revoke | ⚠ 접근토큰 폐기 |
| `oauth2_token` | POST /oauth2/token | 접근토큰 발급 |

## reference

| api_type | 호출 | 이름 |
|---|---|---|
| `ref_market_days` | GET /reference/v1/market-days | 국내 영업일 조회 |
| `ref_market_hours` | GET /reference/v1/market-hours | 국내 장운영 조회 |
| `ref_ovs_market_hours` | GET /reference/v1/overseas/market-hours | 해외 장운영 조회 |
| `ref_ovs_market_days` | GET /reference/v1/overseas/market-days | 해외 영업일 조회 |
| `ref_ovs_exchanges` | GET /reference/v1/overseas/exchanges | 해외 거래소 조회 |

## domestic_market

| api_type | 호출 | 이름 |
|---|---|---|
| `market_candles_days` | GET /market/v1/candles/days | 시세추이 조회(일봉) |
| `market_candles_minutes` | GET /market/v1/candles/minutes | 시세추이 조회(분봉) |
| `market_investors` | GET /market/v1/investors | 종목별 투자자매매동향 |
| `market_investors_detail` | GET /market/v1/investors/detail | 국내주식 종목별 투자자매매동향 상세 |
| `market_orderbook` | GET /market/v1/orderbook | 호가 조회 |
| `market_orderbook_after` | GET /market/v1/orderbook/after | 시간외 단일가 호가 조회 |
| `market_prices` | GET /market/v1/prices | 현재가 조회 |
| `market_prices_after` | GET /market/v1/prices/after | 시간외 단일가 조회 |
| `market_trades_minutes` | GET /market/v1/trades/minutes | 체결추이 조회(분) |
| `market_trades_ticks` | GET /market/v1/trades/ticks | 체결추이 조회(틱) |

## trading

| api_type | 호출 | 이름 |
|---|---|---|
| `credit_orders_buy` | POST /trading/v1/credit-orders/buy | ⚠ 신용매수 주문 |
| `orders_buy` | POST /trading/v1/orders/buy | ⚠ 일반주문 매수 |
| `credit_orders_sell` | POST /trading/v1/credit-orders/sell | ⚠ 신용매도 주문 |
| `orders_sell` | POST /trading/v1/orders/sell | ⚠ 일반주문 매도 |
| `orders_modify` | POST /trading/v1/orders/modify | ⚠ 국내주식 주문 정정 |
| `orders_cancel` | POST /trading/v1/orders/cancel | ⚠ 국내주식 주문 취소 |
| `reserved_orders` | GET /trading/v1/reserved-orders | 국내주식 예약주문 조회 |
| `reserved_orders_buy` | POST /trading/v1/reserved-orders/buy | ⚠ 국내주식 예약주문 매수 |
| `reserved_orders_sell` | POST /trading/v1/reserved-orders/sell | ⚠ 국내주식 예약주문 매도 |
| `reserved_orders_cancel` | POST /trading/v1/reserved-orders/cancel | ⚠ 국내주식 예약주문 취소 |
| `orders_estimate` | GET /trading/v1/orders/estimate | 주문가능금액·수량 조회 |
| `orders_history` | GET /trading/v1/orders/history | 주문내역 조회 |
| `ovs_orders_sell` | POST /trading/v1/overseas/orders/sell | ⚠ 해외주식 매도 주문 |
| `ovs_orders_buy` | POST /trading/v1/overseas/orders/buy | ⚠ 해외주식 매수 주문 |
| `ovs_reserved_orders_sell` | POST /trading/v1/overseas/reserved-orders/sell | ⚠ 해외주식 예약주문 매도 |
| `ovs_reserved_orders_buy` | POST /trading/v1/overseas/reserved-orders/buy | ⚠ 해외주식 예약주문 매수 |
| `ovs_reserved_orders_cancel` | POST /trading/v1/overseas/reserved-orders/cancel | ⚠ 해외주식 예약주문 취소 |
| `ovs_reserved_orders` | GET /trading/v1/overseas/reserved-orders | 해외주식 예약주문 조회 |
| `ovs_orders_modify` | POST /trading/v1/overseas/orders/modify | ⚠ 해외주식 주문 정정 |
| `ovs_orders_cancel` | POST /trading/v1/overseas/orders/cancel | ⚠ 해외주식 주문 취소 |
| `ovs_orders_history` | GET /trading/v1/overseas/orders/history | 해외주식 주문체결내역 조회 |
| `ovs_orders_detail` | GET /trading/v1/overseas/orders/detail | 해외주식 주문체결  상세조회 |
| `ovs_orders_estimate` | GET /trading/v1/overseas/orders/estimate | 해외주식 주문가능금액 조회 |
| `ovs_orders_today` | GET /trading/v1/overseas/orders/today | 해외주식 당일 주문체결내역 조회 |

## account

| api_type | 호출 | 이름 |
|---|---|---|
| `profit_loss` | GET /accounts/v1/me/profit-loss | 국내주식 실현손익 (일자별) |
| `profit_loss_symbols` | GET /accounts/v1/me/profit-loss/symbols | 국내주식 실현손익 (종목별) |
| `profit_loss_summary` | GET /accounts/v1/me/profit-loss/summary | 국내주식 실현손익 (합계) |
| `collateral` | GET /accounts/v1/me/collateral | 내 계좌 담보 현황 조회 |
| `deposit` | GET /accounts/v1/me/deposit | 내 계좌 예수금 상세 조회 |
| `transactions` | GET /accounts/v1/me/transactions | 내 계좌 입출금 내역 조회 |
| `valuation` | GET /accounts/v1/me/valuation | 내 계좌 자산평가 조회 |
| `holdings` | GET /accounts/v1/me/holdings | 내 계좌 종목별 평가 조회 |
| `ovs_holdings` | GET /accounts/v1/me/overseas/holdings | 해외주식 잔고 조회 |
| `ovs_currencies` | GET /accounts/v1/me/overseas/currencies | 해외주식 외화잔고 조회 |
| `ovs_profit_loss` | GET /accounts/v1/me/overseas/profit-loss | 해외주식 실현손익 |

## overseas_market

| api_type | 호출 | 이름 |
|---|---|---|
| `ovs_market_candles_minutes` | GET /market/v1/overseas/candles/minutes | 해외주식 시세추이 조회 (분봉) |
| `ovs_market_candles_days` | GET /market/v1/overseas/candles/days | 해외주식 시세추이 조회 (일봉) |
| `ovs_market_trades_ticks` | GET /market/v1/overseas/trades/ticks | 해외주식 체결추이 (틱) |
| `ovs_market_trades_minutes` | GET /market/v1/overseas/trades/minutes | 해외주식 체결추이 조회 (분) |
| `ovs_market_orderbook` | GET /market/v1/overseas/orderbook | 해외주식 호가 조회 |
| `ovs_market_prices` | GET /market/v1/overseas/prices | 해외주식 현재가 조회 |

## forex

| api_type | 호출 | 이름 |
|---|---|---|
| `fx_exchanges_history` | GET /forex/v1/exchanges/history | 환전 내역 조회 |
| `fx_rates_applied` | GET /forex/v1/rates/applied | 환전 적용환율 조회 |
| `fx_rates` | GET /forex/v1/rates | 고시환율 조회 |
| `fx_exchanges` | POST /forex/v1/exchanges | ⚠ 실시간 환전신청 |

## 실시간 (WebSocket)

접속점은 하나다. 무엇을 받을지는 구독 메시지의 `tr_cd` 가 정한다.

| api_type | tr_cd | 이름 |
|---|---|---|
| `ws_stck_cntg` | `ohhts_stck_cntg` | (실시간) 국내주식 현재가 (KRX) |
| `ws_nxt_cntg` | `ohhts_nxt_cntg` | (실시간) 국내주식 현재가 (NXT) |
| `ws_unt_cntg` | `ohhts_unt_cntg` | (실시간) 국내주식 현재가 (SOR 통합) |
| `ws_ovtp_cntg` | `ohhts_ovtp_cntg` | (실시간) 국내주식 현재가 (시간외단일가) |
| `ws_ovan_cntg` | `ohhts_ovan_cntg` | (실시간) 국내주식 시간외예상체결가 |
| `ws_stck_aspr` | `ohhts_stck_aspr` | (실시간) 국내주식 호가 |
| `ws_ovtp_aspr` | `ohhts_ovtp_aspr` | (실시간) 국내주식 호가 (시간외단일가) |
| `ws_cntg_infr` | `ohhts_cntg_infr` | (실시간) 주문 접수 통보 |
| `ws_cntg_rslt` | `ohhts_cntg_rslt` | (실시간) 주문 체결 통보 |
| `ws_exst_aspr` | `ohhts_exst_aspr` | (실시간) 해외주식 호가 |
| `ws_exst_cntd` | `ohhts_exst_cntd` | (실시간) 해외주식 현재가 (주간거래) |
| `ws_exst_cntg` | `ohhts_exst_cntg` | (실시간) 해외주식 현재가 (정규장) |
| `ws_exst_cnta` | `ohhts_exst_cnta` | (실시간) 해외주식 현재가 (After) |
