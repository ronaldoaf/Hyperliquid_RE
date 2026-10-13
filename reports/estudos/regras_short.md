# Regras de short testadas no universo da Hyperliquid

Gerado por `python -m hlre.universe study` em 2026-10-13. Período dos sinais: 2024-12-16 → 2026-10-12. Universo: 232 perps (inclui deslistados; BTC e ETH ficam de fora em A). Retorno = short aberto na abertura do dia seguinte ao sinal e fechado N dias depois, sem taxas e sem funding. IC95 = intervalo de 95% da média por bootstrap de semanas inteiras.

## A. Short depois de alta, de queda ou de repique em tendência de queda

| regra | dias | sinais | média | IC95 da média | mediana | % com lucro | pior 10% | contra mediano | vs. base (IC95) |
|---|---|---|---|---|---|---|---|---|---|
| qualquer alt, qualquer dia (base) | 7 | 115452 | +0.9% | [-0.7%, +2.4%] | +2.2% | 58% | -15.0% | — | — |
| subiu ≥30% em 7d | 7 | 1066 | +3.1% | [+0.2%, +5.8%] | +7.9% | 67% | -20.4% | +12.1% | [-0.8, +4.8] p.p. |
| subiu ≥100% em 7d | 7 | 78 | +10.8% | [-0.3%, +20.5%] | +18.4% | 79% | -19.4% | +20.6% | [-2.1, +19.7] p.p. |
| caiu ≥20% em 7d | 7 | 2574 | -0.2% | [-2.5%, +2.2%] | +1.4% | 56% | -16.1% | +10.5% | [-3.0, +0.9] p.p. |
| repique em queda (30d ≤ −30% e 3d ≥ +15%) | 7 | 384 | +8.2% | [+1.0%, +12.5%] | +12.2% | 79% | -8.7% | +5.3% | [+1.0, +11.5] p.p. |
| qualquer alt, qualquer dia (base) | 14 | 113920 | +1.8% | [-0.6%, +4.3%] | +4.1% | 60% | -20.5% | — | — |
| subiu ≥30% em 7d | 14 | 959 | +2.3% | [-1.2%, +6.3%] | +8.8% | 65% | -29.7% | +15.4% | [-2.7, +4.0] p.p. |
| subiu ≥100% em 7d | 14 | 73 | +8.2% | [-4.2%, +19.9%] | +21.3% | 64% | -41.5% | +27.1% | [-5.5, +17.7] p.p. |
| caiu ≥20% em 7d | 14 | 2219 | +1.8% | [-1.2%, +5.4%] | +3.8% | 58% | -18.7% | +14.6% | [-2.9, +3.2] p.p. |
| repique em queda (30d ≤ −30% e 3d ≥ +15%) | 14 | 359 | +11.5% | [+5.2%, +17.0%] | +14.1% | 82% | -12.7% | +7.8% | [+3.6, +14.9] p.p. |

*contra mediano*: quanto o preço subiu (máxima) acima da entrada durante o período, na mediana. *vs. base*: intervalo de 95% da diferença entre a média da regra e a da base, sorteando as mesmas semanas para as duas (semanas ruins para todas as alts pesam igual nos dois lados); se não inclui zero, a regra fez diferença além de simplesmente estar vendido em alts.

## B. Funding alto como sinal: moedas operadas pela carteira

9 moedas: POPCAT, TRUMP, FARTCOIN, LAUNCHCOIN, AI16Z, MOODENG, ZEC, DOT, HYPE. Retorno de um short de 7 dias por faixa do funding médio do dia do sinal. Janelas sobrepostas (dias seguidos compartilham o futuro); o IC por semanas leva isso em conta só em parte.

| funding anualizado | dias-moeda | média | IC95 da média | mediana | % com lucro |
|---|---|---|---|---|---|
| < 0 | 1062 | -2.7% | [-8.4%, +1.3%] | +1.7% | 56% |
| 0–11% | 2276 | -0.7% | [-3.0%, +1.8%] | +1.8% | 56% |
| 11–30% | 890 | +0.4% | [-2.8%, +3.8%] | +3.3% | 56% |
| 30–60% | 340 | +3.5% | [-0.4%, +7.2%] | +6.8% | 66% |
| > 60% | 177 | +9.7% | [+2.6%, +16.1%] | +11.3% | 72% |

## B. Funding alto como sinal: amostra aleatória de moedas que a carteira não operou

40 moedas: 0G, APT, ARK, AXS, BANANA, BLUR, CFX, CHILLGUY, COMP, CRV, DASH, GALA, GAS, HYPER, IP, JUP, LINK, ME, MEW, MINA, MKR, MNT, NXPC, PNUT, REQ, RSR, RUNE, SCR, SKY, SNX, SUSHI, SYRUP, UNI, W, WIF, WLFI, ZEN, ZK, kFLOKI, kSHIB. Retorno de um short de 7 dias por faixa do funding médio do dia do sinal. Janelas sobrepostas (dias seguidos compartilham o futuro); o IC por semanas leva isso em conta só em parte.

| funding anualizado | dias-moeda | média | IC95 da média | mediana | % com lucro |
|---|---|---|---|---|---|
| < 0 | 6743 | +0.7% | [-1.0%, +2.3%] | +2.0% | 57% |
| 0–11% | 13932 | +0.8% | [-0.9%, +2.4%] | +1.8% | 58% |
| 11–30% | 1531 | +4.7% | [+2.3%, +7.0%] | +6.0% | 69% |
| 30–60% | 410 | +4.5% | [+0.8%, +8.1%] | +6.5% | 68% |
| > 60% | 98 | +4.2% | [-0.1%, +10.1%] | +4.2% | 61% |

## C. BTC e ETH: short abaixo da média móvel em vários anos

Retorno acumulado de ficar vendido quando o fechamento diário está abaixo da média de N dias (fechamentos diários da Binance; sem alavancagem, taxas ou funding).

| ativo | regra | 2020–2024 | 2022 (baixa) | 2023–24 (alta) | período da carteira |
|---|---|---|---|---|---|
| BTC | short abaixo da MA50 | -33.4% | +1.6% | -33.7% | +17.1% |
| BTC | short abaixo da MA100 | -41.9% | +51.6% | -50.7% | +5.8% |
| BTC | short abaixo da MA200 | -55.5% | +85.4% | -41.7% | -6.3% |
| BTC | sempre short | -98.0% | +85.4% | -90.2% | -9.4% |
| ETH | short abaixo da MA50 | -76.8% | +21.6% | -41.9% | +87.6% |
| ETH | short abaixo da MA100 | -82.4% | -8.6% | -50.8% | +26.4% |
| ETH | short abaixo da MA200 | -31.1% | +30.1% | -31.4% | -19.9% |
| ETH | sempre short | -99.5% | +44.1% | -83.9% | -32.8% |
