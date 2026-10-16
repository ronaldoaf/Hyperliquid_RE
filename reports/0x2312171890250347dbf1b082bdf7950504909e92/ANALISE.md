# Engenharia reversa: carteira `0x2312…9e92`

`0x2312171890250347dbf1b082bdf7950504909e92` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x2312171890250347dbf1b082bdf7950504909e92) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. A conta começou em 16/ago/2023; a API guarda os fills desde 27/fev/2025 (38.817 fills, 5.365 ordens). Antes disso o PnL por moeda é estimado pelo funding. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo

- **Quem é:** trader **manual e discricionário, multi-ativo, sem viés fixo**: alterna long e short em ETH, ZEC, UNI, BTC, SOL e mais de 150 moedas. Opera pelo site (257 ordens `FrontendMarket` nas últimas 1.014) e pelo app (agente "Mobile QR"). Sem ordens de gatilho, ou seja, sem stop no livro.
- **Resultado:** **+US$ 1,99M all-time** (perps +US$ 975k; o resto vem de spot/airdrops, com US$ 79k de `spotTransfer`) e volume de US$ 195M. Funding líquido −US$ 68k, taxas −US$ 41k no período dos fills. Sem liquidação no ledger.
- **De onde vem:** ETH (+US$ 206k), UNI (+US$ 184k), ZEC (+US$ 155k), ONDO (+US$ 108k), XRP (+US$ 79k). Nas três principais, quase todo o lucro é **timing** (aumentar e reduzir na hora certa), não viés: ETH +US$ 177k de timing contra −US$ 3k de viés. BTC é o maior perdedor no período dos fills (−US$ 101k).
- **Estilo:** **compra força e vende força**. Em ZEC, os aumentos de long vêm depois de +49% em 7d, no topo do range (0,93, p<0,001); em ETH, as reduções de long vêm depois de +20% em 7d (p=0,001). Em UNI, abre short no topo do range (0,77, p=0,001). Episódios de dias (mediana 2 a 7 dias).
- **Hoje:** dois trades, ambos em cross: long de OP (US$ 94k, 5x, +US$ 8,6k) e short de UNI (US$ 97k, 10x, +US$ 17,8k). O equity de perp é só US$ 29k, mas há **US$ 690k em USDC no spot** que serve de margem; a alavancagem real fica perto de 0,3x.
- **Dá para copiar?** Passa no teste (18 execuções por dia ativo, 27% maker, 2,1 dias em posição). A cópia a mercado fica com **84% com 30 min de atraso e 86% com 4h** (+US$ 607k a +US$ 626k contra +US$ 727k). Não há regra simples que a reproduza.

---

## 1. Como opera

- **Manual.** Das 1.014 ordens que a API guarda (abr → out/2026): 441 limites `Alo` (quase todas *reduce-only*, ou seja, take-profit no livro), 272 `Ioc`, 257 a mercado pela interface, 7 de liquidação. Zero gatilhos. O stop é feito à mão, ou não é feito.
- **Ritmo:** 726 sessões, mediana de 2 ordens e 0,3 min por sessão; ativo em 290 de 596 dias. Fim de semana com 19% das ordens. Lotes redondos (5 tamanhos somam 11% das ordens de ETH).
- **Escala e execução:** 73% do nocional é taker. BTC (US$ 29,5M) e ETH (US$ 17,6M) são o grosso do volume, mas o lucro vem mais de alts.
- **Preço médio:** aumenta com a posição no prejuízo em 36% das ordens de ETH e 39% das de UNI. Não é um "segurador de perdedor" extremo como outros perfis: em ETH só 40% dos episódios fecham no lucro, mas o ganho médio (US$ 9,7k) é o dobro da perda média (US$ 4,5k). Em UNI é o contrário: 81% dos episódios no lucro.
- **Subconta "hedge"** (`0x51c9…647e`) existe, mas está vazia. Duas ADL a favor em 10/out/2025 (SOL +US$ 79k, AVAX +US$ 27k): shorts fechados à força no crash, com lucro.

## 2. De onde vem o lucro

- **Período dos fills (preço exato):** ETH +US$ 202k, ZEC +US$ 201k, UNI +US$ 120k, XRP +US$ 118k, HYPE +US$ 52k, AAVE +US$ 41k. Perdas: NXPC −US$ 48k, SEI −US$ 44k, XPL −US$ 33k e BTC −US$ 101k na simulação.
- **Timing domina.** ETH: carry +US$ 174k, dos quais +US$ 177k de timing; intradiário +US$ 28k. ZEC: timing +US$ 109k, viés +US$ 47k, intradiário +US$ 46k. UNI: timing +US$ 130k.
- **Maiores acertos:** ZEC long 2/out/2025 (+272% em 30d antes da entrada, **+US$ 106k**), XRP long 28/fev/2025 (+US$ 108k em 2 dias), ETH short 28/out/2025 (+US$ 91k), SOL short 2/out/2025 (+US$ 79k, via ADL), UNI short 23/dez/2025 (+US$ 64k).
- **Maiores erros:** BTC long 22/dez/2025 (até US$ 719k de nocional, −US$ 96k aberto, **−US$ 100k**), BTC long 28/out/2025 (−US$ 58k), NXPC long (−US$ 51k), BTC long 8/out/2025 (−US$ 44k), HYPE long fev/2025 (−US$ 43k). BTC long é o ponto fraco recorrente.
- **Funding pesa contra:** −US$ 102k pago em longs de alts, +US$ 34k recebido em shorts. Ele paga funding alto para seguir momentum (ZEC entrou com funding de +333% a.a.).
- A tabela do relatório mostra limite −US$ 1,48M e mercado +US$ 2,20M. Isso quase com certeza é efeito de atribuição (o PnL de cada fill é marcado de forma diferente para quem abre e quem fecha), não uma perda real das ordens limite. É inferência.

## 3. Gestão de risco e de capital

- **Alavancagem baixa de fato.** A mediana mensal foi de 0,1x a 4x até mai/2026. Desde jun/2026 o relatório mostra 4x a 8x, mas é porque a margem migrou para o USDC spot (US$ 690k) e o equity de perp caiu para US$ 25k a 85k. Somando o spot, a exposição bruta (US$ 190k a 490k) fica abaixo de 1x.
- **Pico de exposição:** US$ 1,94M bruto em jul/2025; maior posição única ETH short de US$ 633k (jul/2026, −US$ 33k em 1 dia).
- **Saca lucro.** Depósitos de US$ 684k contra saques de US$ 2,07M: tirou três vezes o que pôs. 70% dos saques vêm depois de 3 dias positivos.
- **Carteiras ligadas:** só transferências simbólicas (US$ 13 a US$ 40). Uma delas, `0x3671…e963`, é grande (US$ 6,2M de conta, +US$ 71,9M all-time), mas uma transferência de US$ 40 não prova vínculo.

## 4. Dá para copiar?

- **Teste:** nenhum critério bloqueia. Só 10% do volume fecha em menos de 30 min.
- **Cópia com atraso** (96% do volume coberto): 30 min fica com 84%, 1h 86%, 2h 80%, 4h 86%. O custo (9 a 13 bp) não é estatisticamente diferente de zero em nenhum atraso. Drawdown da cópia (−US$ 126k) igual ao da carteira (−US$ 129k).
- **Por ativo,** ZEC, ETH, UNI, XRP, HYPE e WLD mantêm 93% a 100% com 30 min. SOL é onde a cópia mais perde (−US$ 86k contra −US$ 45k).
- **Espelho de posição:** ETH e UNI aguentam até 72h de atraso (ETH até melhora). ZEC cai de +US$ 196k para +US$ 96k em 72h: os trades de ZEC são de momentum rápido.
- **Regra:** a regra testada (short-bias em ETH com filtro de tendência) não combina com o estilo, que alterna lado e moeda. Correlação 0,01 com a posição real; o clone por regressão tem R² negativo no teste. Não há regra mecânica que substitua seguir a carteira.

**Veredito:** trader manual experiente (3 anos, +US$ 1,99M, sacou US$ 2,07M), que ganha com timing em momentum de alts e perde em longs de BTC. É copiável: com até 4h de atraso fica com mais de 80% do resultado. Os riscos são a ausência de stop, o funding pago em alts quentes e o fato de o resultado depender de poucos episódios grandes por moeda (o melhor episódio vale 27% a 48% do lucro dos episódios de ETH, ZEC e UNI).
