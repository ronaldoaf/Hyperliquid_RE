# Engenharia reversa: carteira `0xb69e…033a`

`0xb69eec8fea0081343c3b09e652ba1fa7dcf7033a` · [CoinGlass](https://www.coinglass.com/hyperliquid/0xb69eec8fea0081343c3b09e652ba1fa7dcf7033a) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. A conta nasceu em 7/jan/2026, mas só tinha um depósito de US$ 100 até fevereiro; a API guarda os fills desde 14/fev/2026 (29.114 fills, 956 ordens), ou seja, **praticamente todo o histórico operacional tem PnL exato**. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md). Liquidações: [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **Quem é:** trader **manual e discricionário, macro/multiativo**, que opera pelo site (513 ordens `FrontendMarket`, 70% do nocional a mercado, nenhum agente de API, um único stop em 8 meses). Mistura cripto (BTC, ETH, SOL, NEAR, UNI) com ações e commodities do mercado HIP-3 `xyz:` (DRAM, NBIS, CRCL, MU, SKHX, prata, petróleo). Tem uma subconta chamada "抄底存储" ("reserva para comprar o fundo"), hoje vazia.
- **Resultado:** **+US$ 2,48M all-time** (perps +US$ 2,47M) em 8 meses, partindo de ~US$ 127k depositados em fevereiro. Volume de US$ 167M, funding líquido −US$ 87k, taxas −US$ 44k. Sacou US$ 1,71M (US$ 1,39M pela ponte para a HyperEVM) contra US$ 778k depositados.
- **De onde vem:** BTC +US$ 465k (quase tudo de um short de 27/mai a 4/jun, +US$ 361k), NEAR +US$ 484k (dois longs em set–out), xyz:DRAM +US$ 478k, SOL +US$ 267k, xyz:NBIS +US$ 253k, ETH +US$ 191k. Perdeu em HYPE (−US$ 134k, um short contra uma alta de 47%) e BNB (−US$ 74k).
- **Estilo:** muda de lado (vendido em BTC/ETH em abr–mai, comprado em tudo desde set). Em DRAM compra fundo (72h −5,5%, posição no range 0,30, p=0,002) e realiza na alta de 24h (+6,4%, p=0,03). Em NEAR realiza depois de +17% em 72h, no topo do range (0,93, p=0,009). **Não usa stop e já foi liquidado**: 495 fills de liquidação, −US$ 302k realizados, sendo −US$ 168k numa liquidação parcial de US$ 2,7M em 15/set (BTC, ETH, SOL, BNB, UNI).
- **Hoje:** **só comprado, US$ 10,3M de nocional** sobre equity de perp de US$ 696k, **cerca de 15x**, com toda a margem usada. BTC US$ 8,09M a 20x cross (+US$ 132k, liquidação em 77.005, ~6% abaixo), BNB US$ 1,25M (−US$ 118k), NEAR US$ 514k, PONS US$ 287k, HYPE US$ 198k.
- **Dá para copiar?** Os números dizem que sim: a cópia a mercado com **30 min de atraso fica com 104%** do resultado, com 4h, 92% (custo estatisticamente zero). O ganho vem de ordens a mercado (+US$ 2,28M) e de horizontes de dias (2,6 dias de tempo mediano em posição). **Mas o risco é o problema:** drawdown de −US$ 533k nas mesmas operações, uma liquidação e alavancagem atual de ~15x.

---

## 1. Como opera

- **Manual, pelo site.** Das 1.019 ordens guardadas: 335 limites de entrada (GTC), 112 limites *reduce-only*, 513 a mercado pela interface, 30 ordens de liquidação e **um único stop**. Sem agente de API, sem `cloid`. 266 sessões com mediana de 2 ordens e 0,3 min; atividade em 132 de 242 dias, 7 execuções por dia ativo.
- **Multiativo e oportunista.** Os 25 maiores episódios incluem ações tokenizadas (CRCL, NBIS, RKLB, SKHX, MU, DRAM), prata, petróleo (CL, Brent) e cripto. Os tamanhos são grandes e concentrados: episódios de US$ 1–8M de nocional com 4 a 40 ordens.
- **Troca de viés por regime.** Exposição líquida de −US$ 2,0M em maio (vendido) para +US$ 8,4M em outubro (só comprado). A alavancagem mediana subiu de 2,6x (fev) para 10–17x (jul–out).
- **Compra recuo, vende força, sem preço médio para baixo.** Em BTC só 26% dos aumentos são feitos com a posição no prejuízo, em DRAM 11%. Quando erra, ele segura (HYPE short: −US$ 330k de PnL aberto, fechou em −US$ 145k; BTC long atual: −US$ 166k aberto no pior momento).

## 2. De onde vem o lucro

Período com fills (14/fev → 15/out, preço exato): NEAR +US$ 484k, xyz:DRAM +US$ 478k, BTC +US$ 465k, SOL +US$ 267k, xyz:NBIS +US$ 253k, ETH +US$ 191k, UNI +US$ 138k, CRCL +US$ 149k, SKHX +US$ 107k, prata +US$ 108k, MU +US$ 101k. Negativos: HYPE −US$ 134k, BNB −US$ 74k.

- **BTC:** o lucro é timing, não viés (timing +US$ 352k, viés +US$ 106k). Um único short (27/mai → 4/jun, US$ 2,58M, de 75.607 para 65.014) fez +US$ 361k, 82% dos episódios lucrativos de BTC. O long atual (desde 5/set) está −US$ 50k realizado e pagou −US$ 48k de funding.
- **NEAR e DRAM:** vêm do intradiário (+US$ 401k e +US$ 261k): entra e realiza em pedaços dentro da mesma alta. NEAR: dois longs depois de +92% e +20% em 7d, ou seja, **compra momentum** e realiza nos picos (78% das reduções com lucro).
- **Ações HIP-3:** compras depois de quedas fortes (DRAM, SKHX, NBIS com −21% a −34% em 7d e −40% a −48% do máximo de 30d), realizadas em 1 a 7 dias: NBIS +US$ 243k, DRAM +US$ 119k e +US$ 210k.
- **Funding:** −US$ 87k, quase tudo de longs alavancados (BTC long −US$ 53k, a −8,7% a.a.).

## 3. Gestão de risco e de capital

- **Liquidações reais.** O ledger mostra zero, mas os fills mostram 495 execuções de liquidação desta conta, **−US$ 302k** realizados: petróleo CL (2/abr, −US$ 58k), DRAM/SKHX/SPCX (27/jul, −US$ 54k) e, a maior, **15/set às 18h UTC**, quando a conta cross perdeu US$ 2,7M de nocional de uma vez (BTC −US$ 74k, UNI −US$ 30k, BNB −US$ 24k, SOL −US$ 23k, ETH −US$ 18k). Ele não reduziu depois: o BTC long seguiu crescendo até 99 BTC.
- **Alavancagem atual.** US$ 10,3M de nocional contra US$ 696k de equity de perp e margem usada de US$ 696k (100%). O relatório soma US$ 1,50M de valor de conta, mas o USDC spot (US$ 696k) está todo retido como margem; **inferência:** é a mesma margem vista pelos dois lados (conta unificada), e a alavancagem real é ~15x. Uma queda de ~6% no BTC liquida a posição de BTC.
- **Retira lucro.** Em 100% dos 17 dias de saque o PnL dos 3 dias anteriores era positivo (mediana +US$ 123k). Saques de US$ 500k (jun) e US$ 250k (out). Os US$ 1,39M saíram pela ponte para a HyperEVM. Carteiras ligadas: a subconta `0xded3…` (+US$ 274k, hoje zerada) e a hot wallet `0x6b9e…0a24` (exchange/ponte). Sem HYPE em staking.

## 4. Dá para copiar?

| atraso | cópia | fica com | custo (bp, IC 95%) |
|---|---|---|---|
| 30 min | +US$ 2,39M | 104% | −6,1 (−17,9 a 5,8) |
| 1h | +US$ 2,39M | 104% | −5,9 |
| 2h | +US$ 2,09M | 91% | 13,2 |
| 4h | +US$ 2,10M | 92% | 12,0 |

Passa no teste de copiabilidade (1% do volume fica aberto menos de 30 min; 30% maker). Quase todo o resultado vem de ordens a mercado (+US$ 2,28M); o limite rende só +US$ 16k, então a cópia a mercado não perde vantagem. Espelhar a posição com 24h de atraso mantém BTC (+US$ 309k de US$ 500k) mas destrói NEAR (+US$ 26k de US$ 492k): NEAR e DRAM exigem seguir em horas, não em dias. O simulador ignora margem, liquidação e impacto, e copiar no mesmo tamanho exigiria aceitar a liquidação de 15/set.

A regra testada (short-bias em BTC) **não combina com o estilo**, que hoje é long e multiativo: ganha US$ 319k no treino e perde US$ 54k no teste; o clone por regressão tem R² de teste −1,31. Não há regra mecânica; há um trader discricionário.

**Veredito:** copiável em execução (a cópia com 30 min a 4h de atraso guarda 92–104%), mas **só com alavancagem bem menor**: a carteira roda a ~15x, já foi liquidada em US$ 2,7M e hoje tem 78% do nocional num BTC long a 20x com liquidação ~6% abaixo. O lucro está concentrado em poucas apostas (short de BTC em mai, NEAR, DRAM, NBIS). Copiar com fração do tamanho e stop próprio.
