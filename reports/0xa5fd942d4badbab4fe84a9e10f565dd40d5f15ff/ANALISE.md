# Engenharia reversa: carteira `0xa5fd…15ff`

`0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff` · [CoinGlass](https://www.coinglass.com/hyperliquid/0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff) · dados até 15/out/2026

Fonte: API pública da Hyperliquid. A conta existe desde mar/2024 e opera a sério desde dez/2024, mas a API só entrega os fills de **29/mai/2026 em diante** (26 mil fills, ~4,5 meses). Antes disso, a posição diária de cada moeda vem do histórico de funding (21 mil registros), e o resultado vem do `portfolio`. No período com fills, o PnL exato por moeda soma +US$ 854 mil, contra +US$ 892 mil do `portfolio` de perps; a diferença são posições que ficaram paradas, sem fill. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md). Os números que não estão lá vêm de [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **Quem é:** um **trader manual de escadas de ordens limite** num livro largo de **altcoins**: 130 mercados em 22 meses, 40 posições abertas ao mesmo tempo hoje. Coloca de uma vez de 7 a 97 limites do mesmo tamanho (a ordem *Scale* da interface), de 10% a 40% longe do preço, e deixa no livro por dias ou semanas. Hoje são **555 ordens abertas**, US$ 3,9M de compra e US$ 4,0M de venda.
- **Quanto ganhou:** US$ 235 mil depositados em dez/2024 viraram **US$ 2,52M**. São **+US$ 2,21M em perps** (+US$ 2,28M com spot) em 22 meses, sacando só US$ 65 mil. A primeira tentativa, em mar–abr/2024, perdeu quase tudo (US$ 63 mil).
- **De onde vem o lucro:**
  - **Alts compradas, não BTC/ETH.** No período com fills: alts +US$ 935 mil, BTC/ETH −US$ 78 mil, HIP-3 (ações e pré-IPO) ~0. Nos lotes fechados, os longs de alts dão US$ 842 mil de US$ 871 mil.
  - **Entrar e sair com limite.** Os lotes que entraram e saíram com ordem *maker* renderam +US$ 764 mil. As saídas a mercado ou por gatilho somam −US$ 27 mil.
  - **O lucro está no caminho do preço dentro do dia,** não na posição média. Com a posição média diária, o período com fills daria +US$ 420 mil de preço. O exato dá +US$ 990 mil. Antes dos fills a diferença é maior: +US$ 98 mil na aproximação contra **+US$ 1,31M** no `portfolio`. Os degraus compram nas mínimas e vendem nas máximas.
  - **Seleção de moeda.** LIT subiu 144% e MET 203% no período com fills. A alt mediana listada o período inteiro subiu 2,4%. As duas renderam US$ 517 mil.
- **O risco:**
  - **Sem stop:** carrega perdedoras por meses. MET custou ~US$ 154 mil entre nov/2025 e mai/2026 antes de render US$ 257 mil.
  - **Shorts em escada contra squeeze.** O short de IP de fev/2025 (33 mil IP a US$ 1,8; o preço foi a US$ 5,7 em 4 dias) abriu um recuo de **−US$ 336 mil, de US$ 622 mil para US$ 286 mil de patrimônio (−54%)**, de fev a abr/2025.
  - **Liquidado 16 vezes** em 4,5 meses, sempre em margem isolada ou HIP-3 (PUMP, LIT, CASHCAT, LLY, KIOXIA, MSTR, SPCX…): −US$ 128 mil.
- **Dá para replicar ou copiar?** **Não como regra.** Uma escada mecânica em todas as alts (compra X% abaixo do fechamento, venda X% acima) ganha em 51–82% das vezes, mas a média fica perto de zero, sem diferença significativa de comprar em qualquer dia. O formato do resultado é o de quem vende *put*: muitos ganhos pequenos e uma cauda de −30% a −40%. A vantagem da carteira está em **quais** moedas ela escolhe e em quanto põe em cada uma. As escadas ficam visíveis na API (`frontendOpenOrders`), mas espelhar as ordens copiaria o método, não a escolha.

---

## 1. Quem é essa carteira

- **Execução manual pela interface:**
  - não há API wallet (agente) nem `cloid`. O endereço principal assina tudo;
  - as escadas saem com o mesmo timestamp em dezenas de ordens (BTC: 53 limites de US$ 56,0k a US$ 61,1k; REZ: 97 limites), o que é a ordem *Scale* do site;
  - os degraus têm tamanho igual: 8.184 e 4.430 LIT, 17.316 e 21.645 MET. 82% das ordens de abertura repetem o tamanho de pelo menos outras duas da mesma moeda;
  - 86% do nocional de abertura é *maker*. As saídas usam limites `reduceOnly` em preços redondos (LIT 4,44 / 5,15 / 5,33; MET 0,45 / 0,47);
  - só 9 stops e 15 *take-profits* de gatilho entre as ~1.200 ordens mais recentes que a API guarda.
- **Horário.** As ordens se concentram das 12h às 16h UTC (pico às 14h) e das 0h às 3h UTC, e quase nada sai das 4h às 7h UTC.
- **Tamanho do livro.** A mediana de moedas com posição acima de US$ 1 mil por dia subiu com o capital: 10–15 em 2025, 20–30 no 1º semestre de 2026 e 35–41 desde agosto. Hoje há 19 longs (US$ 3,9M) e 13 shorts (US$ 0,5M).
- **Dinheiro.**
  - **1ª fase (mar–ago/2024):** US$ 65 mil depositados. Long de ~US$ 110 mil em AVAX (abril −US$ 39 mil) e US$ 17,9 mil num vault (`0x882d…bb41`) que não voltaram. Em agosto a conta tinha US$ 19.
  - **2ª fase (dez/2024 →):** US$ 234,7 mil em cinco depósitos (1, 4 e 19/dez). Depois disso, só saídas: US$ 30 mil para a HyperEVM (17/set/2026) e US$ 35 mil de saque (23/set/2026).
  - De dez/2024 a mar/2025, US$ 115 mil passaram para o saldo spot. Em 5/mar/2025, US$ 193 mil voltaram para os perps. A contribuição do spot no total é pequena (US$ 2,28M − US$ 2,21M).
  - **Hoje:** conta unificada, com US$ 2,35M em USDC no spot (US$ 2,0M travados como margem). Tem 747 HYPE em *staking* (10% de desconto na taxa) e restos de spot: DEPIN, DRV, USDT0 e 8,4M de MAX recebidos em 13/jun/2026.
  - Usa o código de indicação **"ONCHAINQUANT"**, que tem um único indicado.

## 2. A curva

| período | PnL de perps | patrimônio no fim |
|---|---|---|
| dez/2024 | +US$ 38 mil | US$ 467 mil (com spot) |
| jan–fev/2025 | +US$ 81 mil | US$ 565 mil |
| mar–abr/2025 | −US$ 145 mil | US$ 298 mil |
| mai–dez/2025 | +US$ 495 mil | US$ 878 mil |
| jan–abr/2026 | +US$ 843 mil | US$ 1,65M |
| mai–ago/2026 | +US$ 313 mil | US$ 1,89M |
| set/2026 | +US$ 600 mil | US$ 2,45M |
| out/2026 (até 15) | −US$ 19 mil | US$ 2,52M |

- **O recuo de 2025** (−US$ 336 mil no PnL, de 5/fev a 2/abr) veio de três tombos:
  - **IP:** um short de 33.346 IP (~US$ 60 mil) aberto a ~US$ 1,8 em 16/fev. O preço foi a US$ 2,78 em 19/fev e a US$ 5,66 em 20/fev. Pela aproximação, custou ~US$ 142 mil, e ele fechou na alta.
  - **ETH:** longs de US$ 250–380 mil, um na queda de 3/fev e outro de 23/fev a 4/mar.
  - **KAITO e USUAL:** longs de US$ 60–100 mil que caíram.
- **Em 2026 a curva acelerou com o tamanho.** A exposição bruta passou de US$ 0,7M (jan) para US$ 3–6M (mar–out). A alavancagem bruta mediana ficou em 2–3x o patrimônio, com pico de 5x em mai/2026.

## 3. De onde veio o PnL

**No período com fills (29/mai → 15/out/2026), exato:**

|  | preço | funding | taxas | total |
|---|---|---|---|---|
| alts | +US$ 987 mil | −US$ 46 mil | −US$ 6 mil | **+US$ 935 mil** |
| BTC/ETH | −US$ 52 mil | −US$ 14 mil | −US$ 12 mil | −US$ 78 mil |
| HIP-3 | +US$ 55 mil | −US$ 57 mil | −US$ 1 mil | −US$ 4 mil |

- **Maiores ganhos:** LIT +US$ 261 mil, MET +US$ 257 mil, HYPE +US$ 140 mil, VIRTUAL +US$ 72 mil, CASHCAT +US$ 69 mil, XMR +US$ 58 mil, ENA +US$ 57 mil, REZ +US$ 56 mil.
- **Maiores perdas:** PONS −US$ 79 mil, XRP −US$ 65 mil, BCH −US$ 50 mil, xyz:SPCX −US$ 49 mil, BTC −US$ 45 mil, xyz:BB −US$ 43 mil (US$ 54 mil só de funding, num long que pagava ~125% a.a.), PUMP −US$ 36 mil, APT −US$ 34 mil.

**Lotes fechados (FIFO), por classe e prazo de carregamento:**

| classe | < 1h | 1h–1d | 1–7d | 7–30d | > 30d |
|---|---|---|---|---|---|
| alts | +US$ 4 mil | +US$ 119 mil | +US$ 250 mil | +US$ 346 mil | +US$ 131 mil |
| BTC/ETH | +US$ 16 mil | +US$ 5 mil | −US$ 105 mil | +US$ 51 mil | — |
| HIP-3 | ~0 | −US$ 11 mil | +US$ 20 mil | +US$ 21 mil | +US$ 23 mil |

| classe | long | short |
|---|---|---|
| alts | **+US$ 842 mil** | +US$ 9 mil |
| BTC/ETH | +US$ 69 mil | −US$ 102 mil |
| HIP-3 | +US$ 41 mil | +US$ 12 mil |

| entrada → saída | nocional | PnL |
|---|---|---|
| limite → limite | US$ 27,5M | **+US$ 764 mil** |
| mercado → limite | US$ 3,7M | +US$ 80 mil |
| mercado → mercado | US$ 2,8M | +US$ 46 mil |
| limite → mercado/gatilho | US$ 17,7M | −US$ 21 mil |

O prazo mediano, ponderado por nocional, é de 5,4 dias. O lucro vem de comprar alts em degraus e vender cada lote numa limite acima, dias ou semanas depois. Os shorts de alts empatam. BTC e ETH (blocos de US$ 0,4–1,5M, 69% *maker*) perdem.

**Antes dos fills (dez/2024 → mai/2026).** Pela posição média diária, o preço mais o funding dariam +US$ 98 mil. O `portfolio` de perps mostra **+US$ 1,31M**. A diferença é grande demais para erro de arredondamento. É a mesma assinatura do período com fills, onde a aproximação perde 58% do PnL de preço: comprar abaixo e vender acima do preço médio do dia. Por moeda, a aproximação aponta o mesmo desenho: ganhos em HYPE, MERL, APT, NEAR, OM e MELANIA; perdas em ETH (−US$ 291 mil), IP, ENA, USUAL e BTC. BTC e ETH somados dão −US$ 361 mil. Os valores por moeda dessa fase são aproximados.

## 4. O padrão das escadas

**Onde os degraus de alts são executados** (aberturas *maker*, candles de 4h, médias ponderadas por nocional):

| | fills | distância da máx. de 7d | retorno de 7d antes (mediana) | posição na vela de 4h (0 = mínima) | 1 dia depois | 7 dias depois |
|---|---|---|---|---|---|---|
| compras | 5.584 | −12,2% | +12,8% | 0,37 | +1,4% | 0,0% |
| vendas (abre short) | 4.505 | −8,0% | +10,4% | 0,59 | −1,2% | −0,5% |
| base (qualquer vela das mesmas moedas) | | | | | +0,3% | +2,5% |

- **Compra recuo dentro de alta.** A moeda subiu ~13% na semana, mas a compra sai 12% abaixo da máxima recente e no terço de baixo da vela de 4h.
- **A vantagem é curta.** No dia seguinte, o preço está 1,4% acima da compra (contra 0,3% na base). Em 7 dias, a vantagem some. O lucro depende de ter a venda já posicionada para o repique.
- **Os degraus pegam liquidações.** Em 612 fills, as limites da carteira foram a contraparte de liquidações de terceiros (US$ 2,1M, 33 moedas). É o que se espera de compras deixadas 10–40% abaixo do preço.
- **Exemplo, LIT (ago–set/2026):**
  - compras de 53,7 mil e 24,2 mil LIT a US$ 2,79–2,76 em 21/ago;
  - venda de tudo a US$ 3,57–3,66 em 24/ago (+US$ 64 mil);
  - recompra de 100,4 mil a US$ 3,32 no mesmo dia;
  - venda a US$ 4,44 em 3/set (+US$ 112 mil);
  - depois, degraus de 4.430 LIT a cada ~US$ 0,03 de queda e vendas em US$ 4,88, 5,15 e 5,33.
- **Exemplo, MET:**
  - long de ~540 mil MET herdado do fim de 2025, com prejuízo;
  - +191 mil a US$ 0,13 (17/jul/2026);
  - degraus de 17.316 MET de US$ 0,198 a 0,183 (30–31/ago);
  - vendas a US$ 0,45–0,47 em 8/out (+US$ 111 mil realizados);
  - em seguida, nova escada de 21.645 MET de US$ 0,40 a 0,35, já executada até 0,35.

**Escadas abertas hoje** (ordens não `reduceOnly`, distância do preço atual):

| moeda | lado | ordens | nocional | faixa |
|---|---|---|---|---|
| BTC | compra | 53 | US$ 1,33M | −26% a −32% |
| ETH | compra | 20 | US$ 1,02M | −23% a −41% |
| MET | compra | 38 | US$ 0,27M | −9% a −93% |
| CASHCAT | compra | 32 | US$ 0,11M | −21% a −44% |
| REZ | compra | 97 | US$ 0,14M | −38% a −47% |
| XMR | compra | 7 | US$ 0,14M | −26% a −28% |
| ENA | compra | 32 | US$ 0,05M | −10% a −20% |
| APT | venda | 24 | US$ 0,15M | +17% a +25% |
| KAITO | venda | 31 | US$ 0,09M | +222% a +300% |
| BLUR | venda | 22 | US$ 0,07M | +28% a +82% |

Há ainda escadas em moedas sem posição aberta: compra de ZEC (US$ 215–290) e GRASS; venda de XLM, SUI e SEI. Algumas estão lá desde maio. As escadas de BTC e ETH, 25–40% abaixo, são **apostas em *crash*** (no estilo de 10/out/2025), não trading de rotina.

## 5. Risco

- **Não usa stop; o limite é a margem isolada.** As posições mais especulativas (LIT 4x, CASHCAT 3x, MET 2x e as de HIP-3) ficam em margem isolada, e é a liquidação que fecha a perda. Foram 16 liquidações próprias desde 29/mai, somando −US$ 128 mil:

  | moeda | quando | realizado |
  |---|---|---|
  | PUMP | 19/jul e 20/ago | −US$ 33 mil |
  | CASHCAT | 27/jul–6/ago | −US$ 22 mil |
  | xyz:SPCX | 16/jun e 16/jul | −US$ 14 mil |
  | xyz:KIOXIA | 4/ago | −US$ 14 mil |
  | xyz:MSTR (short) | jun–ago | −US$ 12 mil |
  | LIT | 29/set | −US$ 18 mil |
  | xyz:LLY | 14/jul | −US$ 10 mil |

  O ledger não registra nenhuma liquidação. Elas aparecem só no campo `liquidation` dos fills.
- **Média contra o preço.** Em ETH, 98% dos aumentos foram feitos com a posição no prejuízo. Os degraus fazem exatamente isso por construção: quanto mais cai, mais compra.
- **Perdedoras carregadas.** Hoje PONS está −US$ 81 mil (−49% sobre um long de US$ 166 mil), ETH −US$ 50 mil, BCH −US$ 49 mil e XRP −US$ 40 mil. O não realizado total é ~−US$ 12 mil, porque os shorts (IMX, 2Z, WLFI, 0G) compensam.
- **Funding pago: −US$ 236 mil** no histórico inteiro (longs −US$ 108 mil, shorts −US$ 128 mil). As maiores contas:
  - longs de HIP-3 com funding alto: xyz:BB −US$ 55 mil, vntl:ANTHROPIC −US$ 13 mil;
  - shorts em moedas com funding negativo, onde quem paga é o vendido: 0G −US$ 35 mil, APT −US$ 23 mil, LAYER −US$ 23 mil.

  A carteira escolhe pelo preço e não evita o custo de carregar.
- **Exposição líquida comprada e crescente.** O livro long passou de US$ 0,4–0,9M (médias trimestrais de 2025) para US$ 4,6M (out/2026), contra US$ 1,1M de shorts. Os shorts não fazem hedge: a correlação diária entre a posição líquida em BTC/ETH e a das alts é +0,25, ou seja, andam no mesmo sentido. Uma queda forte das alts acerta o livro inteiro, e as escadas de compra aumentam a posição na descida.

## 6. Dá para copiar?

**Espelhar a posição com atraso** (relatório automático, seção 9):

| atraso | ETH | HYPE | LIT |
|---|---|---|---|
| 0h | +US$ 21,5 mil | +US$ 205 mil | +US$ 244 mil |
| 24h | +US$ 10,3 mil | +US$ 106 mil | +US$ 233 mil |
| 72h | −US$ 36 mil | +US$ 49 mil | +US$ 52 mil |

A posição em LIT e HYPE ainda rende com 24h de atraso. Mas quem copia a posição com ordem a mercado entra no preço médio do dia, e é justamente esse pedaço que a carteira captura: 58% do PnL de preço no período com fills.

**Replicar o método com regra fixa.** Teste no universo inteiro de perps (232 alts, inclusive deslistadas): limite de compra X% abaixo do fechamento, válida no dia seguinte; venda X% acima do preço de entrada; saída no fechamento em 30 dias se o alvo não for atingido. A comparação é com comprar na abertura de qualquer dia, com as mesmas regras de saída. Taxas *maker* incluídas, IC de 95% por bootstrap de semanas.

| período | queda/alvo | filtro | trades | média | % com lucro | pior 10% | base | diferença (IC95) |
|---|---|---|---|---|---|---|---|---|
| dez/2024–out/2025 | 5% | todas | 20.114 | −1,0% | 82% | −30% | −2,8% | +1,9 [+0,2, +3,7] |
| dez/2024–out/2025 | 10% | 30d > 0 | 2.281 | −0,4% | 72% | −35% | −3,0% | +2,6 [−0,5, +5,9] |
| dez/2024–out/2025 | 20% | todas | 833 | +0,4% | 57% | −39% | −2,8% | +3,2 [−4,7, +11,4] |
| nov/2025–set/2026 | 5% | todas | 14.854 | −0,1% | 82% | −24% | −0,4% | +0,3 [−1,3, +1,9] |
| nov/2025–set/2026 | 10% | 30d > 0 | 1.095 | −2,6% | 68% | −37% | −1,5% | −1,1 [−4,2, +1,9] |
| nov/2025–set/2026 | 20% | todas | 272 | +2,9% | 64% | −35% | −0,4% | +3,2 [−3,5, +8,7] |

As outras variantes estão em `analise_extra.py`. A taxa de acerto é alta como a da carteira, mas a média é ~0. Só as duas variantes de 5% do primeiro período ficam acima de zero, e por pouco (o IC começa em +0,2 e +0,0). Elas não se repetem no segundo período. **A escada sozinha não tem vantagem.** O que sobra para a carteira é a seleção (LIT e MET contra uma alt mediana de +2,4%) e o dimensionamento: degraus maiores nas moedas em que ela confia, pequenos ou nenhum no resto. Isso não vira regra com os dados públicos.

## 7. O que esta carteira não é

- **Não é bot nem market maker.** Não tem agente nem `cloid`, as ordens ficam no livro por dias, entra em ~130 mercados de forma irregular e deixa posições direcionais grandes. *Maker* aqui é consequência de usar limites, não de prover liquidez nos dois lados.
- **Não é hedge.** Os shorts são poucos e não acompanham os longs, e BTC/ETH não neutralizam o livro de alts.
- **Não é carry de funding.** Paga funding nos dois lados (−US$ 236 mil).

## 8. Como monitorar

- **As escadas abertas são o sinal antecipado.** `frontendOpenOrders` mostra hoje onde ela compraria (BTC a US$ 56–61k, ETH a US$ 1.450–1.890, MET, REZ, CASHCAT) e onde venderia (APT, KAITO, BLUR, XLM, SUI). Escada nova numa moeda sem posição indica interesse.
- **Exposição bruta contra patrimônio.** Hoje está ~2,2x. Acima de 4x (como em mai/2026), com as escadas de compra sendo executadas numa queda, é o cenário de perda grande.
- **Liquidações em margem isolada** são o "stop" dela. Uma sequência delas no mesmo dia indica que o mercado está indo contra o livro inteiro.
- Rodar `python -m hlre.run 0xa5fd942d4badbab4fe84a9e10f565dd40d5f15ff` e depois o `analise_extra.py`. A API só guarda as últimas 2.000 ordens, e 989 delas estão abertas agora, então o histórico de ordens canceladas se perde rápido.

## 9. Limitações

- **Antes de 29/mai/2026 não há fills.** O PnL por moeda dessa fase é a aproximação diária, que aqui erra muito: mostra +US$ 98 mil onde o `portfolio` tem +US$ 1,31M. As conclusões dessa fase sobre *quais* moedas pesaram (IP, ETH, MET, HYPE, MERL) vêm da posição, que é exata. O valor em dólares por moeda não é.
- **O relatório automático:**
  - lista as liquidações próprias junto com fills em que a carteira foi a contraparte de liquidações. As 276 próprias são as da tabela da seção 5;
  - mostra o HYPE com 869 "ordens" de tamanho 0,49, que são fatias de TWAP de dez/2024;
  - mostra o teste de replicação da seção 10 em ETH, que não é o livro principal.
- **HIP-3:** as posições abertas nos DEXs de terceiros (xyz, vntl, para, cash, km) não aparecem no `clearinghouseState` principal. Só os fills e o funding as mostram.
- **Spot:** a conta guarda tokens recebidos (MAX, DEPIN) cujo valor não foi medido. A contribuição do spot no PnL total é de ~US$ 70 mil.
- **Nada aqui é recomendação de investimento.**
