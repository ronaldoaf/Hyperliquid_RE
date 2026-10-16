# Engenharia reversa: carteira `0x95da…2328`

`0x95da8596c44dd09f4b8becce87ad3b7894fb2328` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x95da8596c44dd09f4b8becce87ad3b7894fb2328) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. A conta nasceu em 18/fev/2026; a API guarda os fills desde 24/mai/2026 (33.924 fills). Antes disso o PnL por moeda é estimado pelo funding. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo

- **Quem é:** trader **manual e discricionário de altcoins, quase só comprado**, que opera pelo site (48 ordens `FrontendMarket`, 76% do nocional em limite maker). Há um agente de API ("Mobile QR", ligado ao app de celular), sem bot.
- **Resultado:** **+US$ 1,26M all-time** (perps +US$ 1,22M) em 8 meses, com conta de US$ 2,34M (perp + spot) e volume de US$ 114M. Sem liquidações, funding líquido de só −US$ 30k e taxas de US$ 17k.
- **Escala rápida:** equity de perp de US$ 73k (fev) para US$ 1,1M (out); exposição bruta de US$ 58k para US$ 1,75M. Mediana de 1,8x de alavancagem. Entrou capital de fora: US$ 1,16M em transferências (US$ 268k, US$ 400k e US$ 300k de contas ligadas e da hot wallet `0x6b9e…0a24`) contra US$ 127k de saques.
- **Maior fonte de lucro:** um único long de SOL (5/jul → 27/ago, até US$ 1,42M, **+US$ 355k**, 89% do lucro dos episódios de SOL). SOL rende +US$ 398k no total. Depois vêm PUMP (+US$ 172k realizado, em 22 episódios curtos), TON, HYPE, ZRO, WLD (+US$ 79k cada).
- **Estilo:** compra recuos e vende repiques. Nas sessões de SOL, as reduções vêm depois de +4,6% em 24h e +12% em 7d, no topo do range (0,99, p<1e-4); as compras vêm depois de queda em 24h (−0,6%, p=0,03). Em PUMP, compra com −2,8% em 24h e vende com +5%.
- **Hoje:** 12 posições, US$ 4,0M de nocional comprado, quase tudo em cross a 5x. As maiores: XRP US$ 1,10M (−US$ 48k, entrada 1,39) e ONDO US$ 1,09M a 7x. Sem short. Maior risco: XRP+ONDO somam 55% do livro.
- **Dá para copiar?** Passa no teste (19 execuções por dia ativo, 7,2h de tempo mediano em posição). Cópia a mercado com **30 min de atraso fica com 91%** (+US$ 1,02M contra +US$ 1,12M); 1h, 79%; 4h, 54%. **Mas é uma amostra de 4,7 meses numa alta de SOL/PUMP/HYPE**, e não há regra replicável: a melhor regra de SOL no treino perde US$ 435k no teste.

---

## 1. Como opera

- **Manual, pelo site.** 1.012 ordens guardadas pela API: 629 limites de entrada (GTC), 255 limites *reduce-only*, 127 a mercado pela interface; zero ordens de gatilho, ou seja, **sem stop**. O stop é a decisão de fechar à mão.
- **Lotes redondos e repetidos** (os 5 mais comuns somam 23% das ordens de SOL), 764 sessões de mediana 2 ordens e 0,5 min, atividade em 126 de 144 dias, fim de semana 19%.
- **Escada de compra e fechamento.** 63% dos aumentos de SOL e 62% dos de PUMP são feitos com a posição no prejuízo (preço médio mais alto). Ele **faz preço médio para baixo e fecha em ganho**: 96% das reduções de SOL, 85% das de PUMP fecham no lucro, ganho médio de US$ 9,1k contra perda média de US$ 339. A assimetria é típica de quem segura o perdedor até voltar.
- **Pior caso aberto:** HYPE (4/jun) chegou a −US$ 162k de PnL aberto, contra 26% de movimento adverso, e fechou em −US$ 34,5k. TON (jun) −US$ 51k aberto, fechou −US$ 11k. TAO (jun) −US$ 39k.

## 2. De onde veio o PnL

Período com fills (24/mai → 15/out, preço exato): SOL +US$ 398k, TON +US$ 98k, HYPE +US$ 93k, ZRO +US$ 80k, WLD +US$ 79k, ONDO +US$ 44k, ENA +US$ 38k; XRP −US$ 29k e TAO −US$ 30k. O resto (57 moedas) soma +US$ 440k. Por mês, realizado menos taxas: mai +39k, jun +132k, jul +86k, **ago +506k**, set +182k, out +196k.

- SOL: carregar a posição rende +US$ 371k (viés +196k, timing +175k) e day trade +US$ 28k. O ganho vem de estar comprado em SOL na alta de 37 dólares, e de aumentar nos recuos.
- PUMP e TON: mais day trade (+US$ 63k e +US$ 39k) do que viés (+US$ 59k e −US$ 1k).
- O "preço aprox." do relatório para moedas antes dos fills (TON −US$ 86k, HYPE −US$ 56k) é apenas estimativa e contradiz o preço exato do período com fills; vale o exato.

## 3. Saldo spot e capital

O perfil spot tem US$ 2,08M de USDC (US$ 958k retidos), **1,5M UXPL** (recebido a ~US$ 0,099, ~US$ 211k de transferências em fev/2026, sendo US$ 150k de custo registrado) e 450k KNTQ. Ou seja, uma parte do patrimônio de US$ 2,34M está em tokens recebidos de contas ligadas, não em PnL de perp. Todas as contas ligadas (`0x4acb…`, `0xf531…`) têm PnL de −US$ 394k: parecem **uma mesma pessoa/grupo** que perdeu fora e passou o saldo para esta conta. A hot wallet `0x6b9e…` é ponte/exchange. Não há HYPE em staking (sem desconto de taxa, 4 bp de taxa taker).

## 4. Risco

- Cross a 5x em altcoins de baixa liquidez, sem stop; sem liquidação no histórico. Um repique contrário de 20% em XRP e ONDO custa cerca de US$ 440k, ou 40% do equity de perp.
- A taxa de acerto de 79% nos episódios de US$ 50k+ e de 85–90% nos principais vem da seleção de fechar só no lucro; o drawdown da carteira nas mesmas operações foi de −US$ 229k.
- A escala (de US$ 73k a US$ 1,1M de equity, com aportes) mostra que o tamanho cresce depois de ganhos e de aportes. O sucesso de 2026 coincide com a alta de SOL, PUMP e HYPE.

## 5. Dá para copiar?

| atraso | cópia | fica com | custo (bp, IC 95%) |
|---|---|---|---|
| 30 min | +US$ 1,02M | 91% | 10,9 (1,2 a 20,7) |
| 1h | +US$ 881k | 79% | 25,1 |
| 2h | +US$ 797k | 71% | 33,9 |
| 4h | +US$ 607k | 54% | 53,9 |

O que a carteira ganha a mercado (taker, US$ 794k) a cópia mantém quase inteiro; o que ganha em limite (maker, US$ 326k) a cópia perde (US$ 214k com 30 min, ~0 com 4h). O espelho da posição com 24h de atraso mantém SOL (+US$ 340k) mas zera PUMP e TON. O simulador ignora margem, liquidação e impacto, e a janela é curta.

**Veredito.** Copiar o SOL (compra de recuos e fechamento nos repiques) funcionou, mas as regras mecânicas não replicam: a melhor regra short-bias de SOL ganha US$ 128k no treino e perde US$ 435k no teste; o clone por regressão tem R² de teste −0,97. O que há de aproveitável é o padrão discricionário (comprar queda de 24h em alt forte, fechar em +5% de repique), não uma regra. **Não copiável como regra; copiável com 30 min de atraso se a alta continuar.**
