# Engenharia reversa: carteira `0x78dc…629c`

`0x78dce96236804d6958bf3c4598cf5efbc371629c` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x78dce96236804d6958bf3c4598cf5efbc371629c) · dados até 14/out/2026

Fonte: API pública da Hyperliquid. A conta existe desde 28/jul/2025, mas negocia tanto que os 10 mil fills que a API entrega cobrem só **6 dias** (8 → 14/out/2026, 11.923 fills). As 2.000 últimas ordens cobrem só **69 segundos**. Antes dos fills, a posição vem do histórico de funding (tamanho médio diário) e o resultado vem do `portfolio`. O ledger (491 eventos) está completo.

Os números deste texto que não estão no [`relatorio_auto.md`](relatorio_auto.md) são recalculados por [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **O que é:** um **bot de market making de alta frequência em BTC perp**, e não um trader. É a subconta **"kakaroto"** de uma conta mestre (`0x7839…9916`) com **50 subcontas com nomes de Dragon Ball**. Juntas, elas fazem ~US$ 400M por dia (88% como *maker*), cerca de **7% do volume da Hyperliquid**.
- **Como opera:** só ordens *post-only* (`Alo`) com `cloid`, ~30 ordens por segundo, 0% *taker*, 3,9 bilhões de requisições acumuladas. 92% das ordens são rejeitadas por cruzar o livro: o bot recota no topo do livro sem parar. Recebe rebate de **−0,3 bp** (faixa de *maker share* do grupo).
- **Quanto rendeu:** **+US$ 252k** em 14,5 meses, com US$ 4,76 bilhões de volume e apenas US$ 12–45k de margem. Isso dá **0,53 bp por dólar negociado**: 0,73 bp até set/2026 e **−1,18 bp nos últimos 30 dias**. O lucro é sacado para a mestre a cada poucos dias (−US$ 305k líquidos).
- **O que mudou em ago/2026:** até jul/2026 o estoque ficava em ±2 BTC em torno de zero (market making neutro) e a conta ganhava em quase todos os meses (+US$ 379k). Desde ago/2026 ela **carrega um short de 6–13 BTC (US$ 0,5–1,1M) o tempo todo**, a 17–37x, e cota só para aumentar ou reduzir esse short. Agosto deu **−US$ 119k** e o acumulado caiu para US$ 252k.
- **Agora:** short de 11,6–12 BTC (~US$ 1M, entrada US$ 83,5k) sobre US$ 28k de conta (37x cross), com **liquidação em US$ 85,0k, ~1,8% acima do preço**. A margem é reposta pela mestre em transferências automáticas a cada 5–10 minutos; 7% das últimas ordens foram rejeitadas por falta de margem.
- **O short é hedge?** Não dentro da Hyperliquid. Somando as 50 subcontas, o grupo está **vendido em ~23 BTC** (esta conta tem metade disso). Se houver hedge, é fora da Hyperliquid (CEX ou spot), e a API não mostra.
- **Dá para copiar?** Não. O resultado vem de spread de fração de bp, rebate de 0,3 bp e latência; a cópia com atraso da posição dá prejuízo em todos os atrasos testados (−US$ 2,6k a −US$ 29k em 6 dias). Copiar o short de BTC é só uma aposta na queda, sem a vantagem do bot.

---

## 1. Quem é essa carteira

**Um bot, parte de uma firma de market making.**

- **Subconta de um grupo grande.** `userRole` = `subAccount`, mestre `0x7839e2f2c375dd2935193f2736167514efff9916`. A mestre tem 50 subcontas (songoku, krillin, trunks, kakaroto, vegeta…), US$ 5,1M de equity somada e US$ 12M de exposição bruta. Algumas cotam um único ativo (BTC ou ETH), outras carregam livros de 30–80 altcoins (trunks, yamcha, burter, dende). A mestre acumula US$ 15 bilhões de volume e +US$ 6,35M de PnL all-time.
- **Ritmo de máquina.** Nas últimas 2.000 ordens (69 s): 1.832 `badAloPxRejected`, 145 `perpMarginRejected`, 11 abertas, 10 canceladas, 2 executadas. Todas `Alo`, todas com `cloid`. O `userRateLimit` mostra 3.866.633.185 requisições acumuladas (~100 por segundo, em média, desde a abertura).
- **Execução.** 11.923 fills em 6 dias (mediana de 70 por hora, 24h por dia, fim de semana incluído), lote mediano de 0,2 BTC, 0% *taker*. Compras e vendas somam o mesmo nocional (US$ 31,7M cada): o bot gira o estoque, não acumula.
- **Rebate.** Taxa média de **−0,30 bp** no período dos fills (US$ 1,9k recebidos sobre US$ 63,5M). A faixa vem do *maker share* do grupo (>3% do volume maker da bolsa), já que as subcontas somam volume com a mestre.

## 2. De onde vem o dinheiro

| período | PnL | volume | bp do volume |
|---|---|---|---|
| jul/2025 → set/2026 (sem os últimos 30 dias) | +US$ 310k | US$ 4,26B | **+0,73** |
| últimos 30 dias | −US$ 58k | US$ 0,49B | **−1,18** |
| total | **+US$ 252k** | US$ 4,76B | +0,53 |

PnL mensal (`portfolio`): +US$ 66k em ago/2025, entre +US$ 15k e +US$ 77k por mês até mar/2026, quase zero em abr–jul/2026 e **−US$ 119k em ago/2026**.

**Markout dos fills** (preço 1 a 240 min depois, contra o preço do fill, ponderado pelo nocional; + = a favor do bot; últimos ~3,5 dias, que é o que os candles de 1 min cobrem):

| horizonte | 1 min | 5 min | 15 min | 60 min | 240 min |
|---|---|---|---|---|---|
| markout | +0,26 bp | +0,21 bp | +0,45 bp | +1,20 bp | −2,48 bp |

A vantagem de curto prazo é de **~0,2–0,3 bp por fill**, mais 0,3 bp de rebate. É uma margem de ~0,5 bp que só fecha com bilhões de volume. Em horizontes longos o resultado passa a depender do estoque carregado, e com o short de 11 BTC isso domina tudo: no período dos fills, o *carry* da posição perdeu US$ 19k contra US$ 1,9k de rebate e US$ 0,7k de funding (`relatorio_auto.md`, seção 3).

## 3. A mudança de ago/2026: estoque vendido

| mês | posição BTC (mín. / máx. / média) | funding recebido |
|---|---|---|
| ago/2025 → jul/2026 | entre −6,5 e +3,3, média ≈ 0 | US$ ~1,8k em 12 meses |
| ago/2026 | −12,2 / −0,4 / −6,2 | US$ 3,9k |
| set/2026 | −12,6 / −2,6 / −8,8 | US$ 5,4k |
| out/2026 (até 14) | −12,5 / −3,8 / −10,4 | US$ 2,4k |

Desde ago/2026 a posição nunca passa para o lado comprado. As ordens do bot ficam todas como `Open Short` ou `Close Short`. Isso é market making com um **alvo de estoque negativo**: o bot cota nos dois lados, mas em volta de −10 BTC, e não de zero. O ganho extra é o funding (shorts recebem ~9% a.a. sobre o nocional). O custo é o risco de preço: ago/2026 sozinho perdeu US$ 119k, quase metade do lucro acumulado em um ano.

Por que o grupo faria isso? Há duas leituras, e a API não permite escolher entre elas:

1. **Hedge de algo fora da Hyperliquid** (BTC comprado em CEX ou em spot, ou estoque de outra mesa). Nesse caso, a perda de preço aqui é compensada lá.
2. **Viés direcional da firma.** O grupo inteiro está vendido em ~23 BTC (US$ 1,9M), com as maiores pontas em songoku (−18,3) e trunks (−9,0), e só parte disso é compensada por krillin (+10,3) e baba (+6,0).

## 4. Gestão de margem

- A mestre move dinheiro para dentro e para fora da subconta **automaticamente**. Foram 484 `subAccountTransfer` desde ago/2025, 366 delas desde ago/2026, em rajadas de 5 em 5 ou de 10 em 10 minutos e em valores de US$ 0,3–4k.
- O lucro sai: −US$ 305k líquidos para a mestre (mais que o PnL all-time, porque a conta recebeu US$ 20k no início e mantém só ~US$ 28k).
- **Pouca margem para muita exposição:** 17x de mediana em ago/2026, 20x em set e 21,5x em out. Hoje está a 37x, com a liquidação ~1,8% acima do preço. Isso só funciona porque a mestre repõe margem em minutos. Uma alta rápida de 2% com essa reposição atrasada liquida a conta.

## 5. Dá para replicar ou copiar?

- **Copiar a posição:** não. A vantagem está no spread e no rebate, em horizonte de segundos. O estoque que sobra é ruído ou hedge. Espelhar a posição deu de −US$ 2,6k a −US$ 29k em 6 dias, conforme o atraso (`relatorio_auto.md`, seção 9).
- **Replicar a estratégia:** exige infraestrutura de HFT (colocation ou latência baixa até os validadores, ~30 ordens/s por ativo), volume suficiente para ficar na faixa de rebate (>3% do volume maker da bolsa, hoje centenas de milhões de dólares por dia) e um modelo de risco de estoque. Não é algo que um trader individual reproduz.
- **O que dá para aprender:** num market maker com margem de ~0,5 bp, o risco de estoque manda no resultado. O ano de lucro estável (0,73 bp) virou prejuízo (−1,18 bp nos últimos 30 dias) assim que o bot passou a carregar um short permanente.

## 6. Limitações

- Os fills cobrem só 6 dias e as ordens só 69 segundos. O comportamento antes de out/2026 vem do funding (posição média diária) e do `portfolio` (PnL), sem detalhe de execução.
- O markout usa o fechamento do candle de 1 min, não o *mid* do livro. Serve para medir o sinal e a ordem de grandeza, não o spread exato.
- As subcontas irmãs são uma foto de 14/out/2026. Não reconstruí o histórico delas.
- Hedge fora da Hyperliquid não é visível pela API.
- Nada aqui é recomendação de investimento.
