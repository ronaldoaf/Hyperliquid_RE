# Engenharia reversa: carteira `0x63d4…0522`

`0x63d417a577b50c96f4f09148d4e4d70950db0522` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x63d417a577b50c96f4f09148d4e4d70950db0522) · dados até 15/out/2026

Fonte: API pública da Hyperliquid. A conta começou em ago/2023, mas a API só guarda os fills desde 08/jul/2026 (26.407 fills). O PnL de antes é estimado pelo funding. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md). Liquidações próprias e livro atual: [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **Quem é:** trader **manual, discricionário e alavancado, em altcoins**. Opera pelo site, sem API wallet. Volume de US$ 365M e PnL all-time de **+US$ 3,29M** (perps +US$ 3,10M), com conta de US$ 3,05M (perp + spot).
- **De onde veio o lucro:** na janela exata (jul–out/2026, ~US$ 1,0M), LIT (+US$ 259k), GRASS (+US$ 181k), HYPE, ETH e CASHCAT. Antes de jul/2026 o relatório só estima. O maior bloco estimado é um **short de MERL** (+US$ 1,7M), mas a atribuição aproximada não fecha com o portfolio (§3).
- **Onde perde:** **13 eventos de liquidação própria** nos fills somam **−US$ 383k** realizados. LIT sozinho perdeu −US$ 237k (20/ago, −US$ 156k; 13/out, −US$ 81k). Funding líquido: −US$ 197k.
- **Hoje:** 25 posições, **US$ 2,9M líquidos comprados** (bruto US$ 3,5M), a maior parte em altcoins de baixa liquidez. Maior posição: XRP long de US$ 805k a 20x, com −US$ 63k. A conta cross está longe de liquidar (manutenção de US$ 225k contra equity de US$ 1,49M), mas um movimento de cerca de 40% contra o livro comprado a levaria perto da manutenção.
- **Dá para copiar?** Passa no teste de copiabilidade. Com 30 min de atraso, a cópia fica com 82% do resultado da janela. Mas não há regra replicável (o teste de MERL perde US$ 344k fora da amostra), a amostra é de 3 meses e o simulador ignora margem e liquidação. **Não copiável como regra.**

---

## 1. Como opera

- **Manual, pelo site.** Nenhum agente de API. Das 1.096 ordens mais recentes que a API guarda: 776 limites de entrada (GTC), 178 limites *reduce-only*, 73 *post-only* (`Alo`), 2 a mercado pela interface, 14 de liquidação e 24 de gatilho (stop e take-profit).
- **Lotes repetidos.** Os 5 tamanhos mais comuns respondem por 71% das ordens de MERL. Lotes redondos e repetidos são assinatura de execução manual.
- **Ritmo.** 468 sessões (ordens a menos de 30 min uma da outra), com mediana de 2 ordens. Ativo em 91 de 98 dias. Fins de semana são 19% da atividade (sáb 10%, dom 9%).
- **Execução.** 23% do nocional é a mercado (taker). O resto entra como limite.
- **Moedas.** Maior volume: BTC (US$ 17,0M), ETH (13,9M), LIT (6,8M), XRP (5,9M), CASHCAT (3,3M), HYPE (2,5M). Dos 125 episódios com nocional de US$ 50k ou mais, 70% fecharam com lucro.
- **Alavancagem.** Mediana de 1,8x, com pico mensal de 3,2x em jun/26. A exposição bruta chegou a US$ 4,1M em set/26, com a conta cross hoje em US$ 1,5M.

## 2. Fases

Exposição mensal do relatório (bruto e líquido, em US$):

| período | bruto | líquido | o que se vê |
|---|---|---|---|
| set–dez/24 | 49k → 400k | comprado | escala lenta, 2,5–3,3x |
| abr–out/25 | 0,6M → 3,8M | comprado | pico em out/25 (1,9x) |
| dez/25–mar/26 | 1,3–2,0M | vendido (−0,1M a −0,9M) | virou net short; equity de 1,7–2,1M |
| abr–mai/26 | 3,0–3,8M | perto de zero, depois comprado (+0,9M em mai) | |
| jun/26 | 2,5M | vendido (−1,3M), 3,2x | o mês de maior alavancagem |
| jul–out/26 | 2,8–4,1M | comprado (+2,8M em set) | alts: ETH, LIT, GRASS, HYPE |

A direção líquida muda de um mês para outro. Não há um viés fixo, só um tamanho que cresce.

## 3. De onde veio o PnL

| moeda | preço + funding, aprox. (histórico) | preço exato (jul–out/26) |
|---|---|---|
| MERL | +1,73M | +1,9k |
| MET | −373k | — |
| ETH | −323k | +78k |
| ZEC | −214k | +1,2k |
| SUI | +177k | −31k |
| SOL | −157k | +19k |
| PUMP | −155k | +3k |
| LIT | +141k | +259k |
| APT | +137k | −14k |
| HYPE | +129k | +98k |
| LAYER | +127k | — |
| CASHCAT | −127k | +50k |
| kBONK | +122k | — |
| ASTER | −120k | — |
| GRASS | +115k | +181k |
| outras (145) | +99k | +399k |
| **soma** | **≈ +1,31M** | **≈ +1,04M** |

**A atribuição aproximada não fecha.** A soma da coluna (≈ +US$ 1,31M, já com funding) fica longe do PnL de perps do portfolio (+US$ 3,10M). O método deixa de fora o day trade, e o relatório avisa disso. Então a divisão por moeda antes de jul/26 mostra a direção, não um número exato.

Decomposição da janela exata:
- **MERL (+US$ 1,9k):** quase nada na janela. A posição média foi de −77k MERL (short) e o preço andou ~0% no período. O grosso do short é anterior a jul/26.
- **ETH (+US$ 78k):** carregar a posição +52k (viés +60k, timing −8k) e day trade +26k. Funding (−5k) e taxas (−2,5k) ficam à parte.
- **LIT (+US$ 259k):** é o maior ganho da janela, mas as duas liquidações nessa moeda somam −US$ 237k (§4).
- **GRASS (+US$ 181k):** um long de 76 dias, com +US$ 177k realizados.

## 4. Gestão de risco

- **Aumenta contra o preço.** MERL: os 10 aumentos foram com a posição no prejuízo, com mediana 3,1% acima do preço médio. ETH: 97% das ordens de aumento (88% do tamanho) foram no prejuízo. Reduções com lucro: 78% em MERL (9 reduções) e 68% em ETH (28). Dos 8 episódios de ETH, 57% fecharam com lucro.
- **MERL é um fade de topo.** A carteira vendeu quando o preço já tinha subido +11% em 24h e +44% em 7 dias, com o preço no topo do range de 7 dias (0,99). Em 24h o preço caiu −9,6%. O p-valor é ~0,01, mas são só 3 sessões de adição.
- **Liquidações próprias** (fills com a carteira liquidada; mesmo minuto e moeda = um evento):

| data (UTC) | moeda | PnL realizado nos fills |
|---|---|---|
| 19/jul | PUMP (short) | −46k |
| 27/jul | CASHCAT (long) | −17k |
| 31/jul | xyz:CXMT (short) | −16k |
| 19/ago | xyz:UNITREE (long) | −2k |
| 19/ago | xyz:MRNA (short) | −32k |
| 20/ago | LIT (short) | −156k |
| 22/ago | WLFI (short) | −8k |
| 25/ago | CASHCAT (long) | −7k |
| 10/set | xyz:HOOD (long) | −11k |
| 18/set | io:SNDK | −2k |
| 27–28/set | para:TREAD | −5k |
| 13/out | LIT (long) | −81k |
| **total** | | **−383k** |

  Os lados se misturam. Shorts foram apanhados em alta (PUMP, CXMT, MRNA, LIT em ago, WLFI) e longs em queda (CASHCAT, UNITREE, HOOD, LIT em out). Sete dos 13 eventos estão em mercados HIP-3 de deploy de terceiros (prefixos `xyz:`, `io:`, `para:`).
- **Margem.** Depósitos não seguem prejuízo: 44% vêm depois de 3 dias negativos, contra 47% da base. Saques seguem lucro: 82% vêm depois de 3 dias positivos. Nas categorias do ledger, as saídas (saques US$ 335k, envios US$ 182k, transferências internas US$ 77k, vault US$ 70k) superam as entradas (depósitos US$ 184k, spot US$ 173k, vault US$ 54k) em ~US$ 250k. O lucro foi em parte sacado.

## 5. Estado atual (snapshot de 16/out/2026)

| moeda | lado | nocional | entrada | preço atual | alav. | uPnL |
|---|---|---|---|---|---|---|
| XRP | long | US$ 805k | 1,446 | 1,340 | 20x cross | −63k |
| ETH | long | US$ 469k | 2.324 | 2.452 | 9x cross | +24k |
| HYPE | long | US$ 425k | 85,2 | 81,6 | 3x cross | −19k |
| CHIP | long | US$ 341k | 0,0464 | 0,0502 | 3x cross | +26k |
| NEAR | long | US$ 288k | 5,17 | 5,23 | 10x cross | +3k |
| REZ | long | US$ 206k | 0,00375 | 0,00369 | 3x cross | −3k |
| WLD | long | US$ 176k | 0,490 | 0,522 | 8x cross | +11k |
| SUI | short | US$ 102k | 0,765 | 1,043 | 10x cross | −27k |
| ONDO | short | US$ 60k | 0,306 | 0,470 | 10x cross | −21k |

O restante são posições menores: AVAX, DOGE, XPL, NIL, MON e MEGA estão no prejuízo; LAYER, 2Z, XAI e INJ, no lucro. Total: **bruto US$ 3,55M, líquido comprado US$ 2,94M**, uPnL de −US$ 57k.

- **Dimensão de risco.** Conta cross: equity US$ 1,49M, margem usada US$ 594k (40%), manutenção US$ 225k (15% do equity). O campo `liquidationPx` de cada moeda, quando aparece, é só nominal: sob margem cross, a liquidação depende da conta inteira. A exceção é XPL, isolada a 2x, que liquida em US$ 0,064 contra US$ 0,085 hoje (−25%).
- **Estimativa grosseira.** Se todas as altcoins caírem juntas cerca de 40%, o livro líquido comprado de US$ 2,9M consome quase todo o equity livre. Não é previsão, só a ordem de grandeza do risco de direção.
- **Spot.** Os ~US$ 1,4M restantes da conta (US$ 3,05M contra os US$ 1,66M de perps) estão em spot ou fora da margem de perps. O relatório não abre o spot.

## 6. Dá para copiar?

**Teste de copiabilidade: passa.** 2.065 execuções em perps e HIP-3. Só 5% do volume fechado ficou aberto menos de 30 min. Tempo mediano em posição de 45,8h. 23 execuções por dia ativo, com 77% do nocional maker. Nenhum critério de bot de market making se aplica.

**Simulação de cópia** (10/jul–15/out, 95% do volume de perps; mesmo tamanho em moedas, taxa taker de 0,045%):

| atraso | carteira | cópia | fica com | maior drawdown |
|---|---|---|---|---|
| 30 min | +US$ 1,02M | +US$ 841k | 82% | −279k |
| 1h | +US$ 1,02M | +US$ 857k | 84% | −275k |
| 2h | +US$ 1,02M | +US$ 878k | 86% | −274k |
| 4h | +US$ 1,02M | +US$ 1,01M | 98% | −262k |

O custo de atraso fica dentro do IC de 95% em todos os casos, que cruza zero. Por moeda: LIT 84%, GRASS 100%, ETH 96%, HYPE 83%, BTC 65%. CASHCAT dá −68%: a cópia perde onde a carteira ganha. Por tipo de execução: limites da carteira +US$ 1,73M (cópia com 30 min: +US$ 1,55M); execuções a mercado −US$ 712k. O grupo a mercado provavelmente inclui as liquidações, que são ordens a mercado, mas o relatório não separa.

**Por que não é copiável como regra:**
1. **Sem regra replicável.** A melhor regra de MERL no treino dá +US$ 1,98M, e no teste −US$ 344k. O clone por regressão tem R² de teste de −0,13.
2. **Amostra de 3 meses.** Antes de jul/26 o PnL é estimado e não há como testar a cópia.
3. **Escala e margem.** A cópia usa o mesmo número de moedas. Com pico de US$ 4,1M de bruto, precisa de capital e margem da mesma ordem. O simulador não modela margem nem liquidação. Com menos capital, o copiador seria liquidado antes, como a própria carteira foi 13 vezes.
4. **Depende da escolha de moedas.** Os ganhos vieram de poucas moedas com movimento grande (LIT, GRASS, HYPE). O que a carteira tem de vantagem é essa escolha, e ela não se reduz a uma regra.

## 7. Carteiras relacionadas

Seis carteiras ligadas por transferência, quase todas com pouco volume. `0xbb5d…85f8` (+US$ 554k de PnL all-time, saldo zero) e `0x6f58…8618` (+US$ 216k, saldo de US$ 1) têm lucro grande sem saldo, mas o vínculo é só uma transferência de US$ 47 e uma de US$ 23. `0x24de…` mostra saldo de US$ 2,3 bilhões e PnL de −US$ 3,2 bilhões, o que é erro de preço do token UMON (saldo de 99,9 bi). Não usar esse número.

## Limitações

- **Fills só desde 08/jul/2026.** Antes disso, o PnL é aproximado e sem day trade. A atribuição não fecha com o portfolio (§3).
- **Liquidações:** o ledger registra 6, e os fills mostram 13 eventos. O relatório segue os fills.
- **Lacunas de posição sem fill:** 3 pontos, ~US$ 64k de nocional (TREAD), provavelmente fatias de TWAP fora da API.
- **Spot** (~US$ 1,4M da conta, 969 fills) não é analisado.
- **Intenção** (aposta ou hedge) é inferência a partir de comportamento.

Nada aqui é recomendação de investimento.
