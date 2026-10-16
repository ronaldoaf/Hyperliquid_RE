# Engenharia reversa: carteira `0x69b0…40bb`

`0x69b05701f8175c276ecd0138387a197948e240bb` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x69b05701f8175c276ecd0138387a197948e240bb) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. A conta nasceu em 5/jun/2025 e os 14.690 fills cobrem todo o histórico, então o PnL diário é exato (+US$ 702,1k contra +US$ 701,6k do `portfolio`). Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo

- **Quem é:** trader **manual e discricionário, quase sempre comprado, em BTC, ETH e HYPE**, que opera com **pares de ordens limite**: uma limite de entrada (GTC) e uma limite *reduce-only* de saída. Das 823 ordens guardadas, 386 são entradas e 386 são saídas limite; só 51 são a mercado pela interface. Sem gatilhos (sem stop), sem agentes de API, 87% do nocional como *maker*.
- **Resultado:** **+US$ 808k all-time** (perps +US$ 702k) em 16 meses, sobre ~US$ 432k depositados. Sem liquidações. Funding −US$ 66k, taxas −US$ 76k. Dias positivos: 51%. Maior drawdown −US$ 125k (13→21/ago/2025).
- **De onde vem:** HYPE +US$ 369k (preço exato), BTC +US$ 316k, ETH +US$ 154k; o resto das alts soma cerca de −US$ 50k (FARTCOIN, AAVE, XMR, PENDLE, XPL). No HYPE só houve longs (24 episódios, 67% com lucro); o melhor foi o long de 15/mai → 2/jun/2026 (51,3 → 69,5, **+US$ 138k**).
- **O lucro está no timing, não no viés:** no período dos fills, o viés médio rende +US$ 73k no HYPE, −US$ 61k no BTC e −US$ 3k no ETH; o *timing* de aumentar e reduzir rende +US$ 238k, +US$ 256k e +US$ 130k. As limites dão +US$ 901k e as ordens a mercado, **−US$ 130k**.
- **Estilo:** em HYPE e ETH, **compra força e realiza depois de mais força**. Os aumentos de long em ETH vêm depois de +7,1% em 7 dias, no topo do range (0,72, p=0,005); em HYPE, com o range em 0,75 (p=0,017). As reduções vêm depois de +7,4% (HYPE) e +3,7% (ETH) em 7 dias. Em BTC não há sinal estatístico: lotes de 2 BTC, long e short, episódios medianos de 2,6 dias e 45% dos aumentos com a posição no prejuízo.
- **Tamanho estável:** exposição bruta de US$ 0,25–1,0M e alavancagem real abaixo de 2x desde o início. A partir de jun/2026, o relatório mostra alavancagem de 3–9x, mas é efeito de contabilidade: o equity de perp caiu para US$ 30–90k porque o caixa (US$ 723k em USDC) passou a ficar no spot, que serve de margem. Hoje: long de 5 BTC (US$ 410k, 20x cross) e long de 33M PUMP (US$ 149k), ~0,8x da conta de US$ 732k.
- **Dá para copiar?** Passa no teste (3 execuções por dia ativo, 32h de tempo mediano em posição, 5% do volume fecha em menos de 30 min). A cópia a mercado fica com **84% com 30 min de atraso** e 77% com 4h (custo de 9 bp do volume, IC 1–17 bp). Mas **não vira regra**: o clone por regressão tem R² de −0,02 no teste.

---

## 1. Como opera

- **Pares de limites, sem stop.** O número de entradas limite (386) é igual ao de saídas limite *reduce-only* (386): para cada entrada, deixa uma saída no livro. As ordens a mercado (34 de entrada, 17 de saída) são raras e, no conjunto, perdem dinheiro.
- **Manual.** 556 sessões em 283 de 497 dias, mediana de 1 ordem por sessão; atividade menor no fim de semana (sáb 7%, dom 9%). Os tamanhos são redondos (2 BTC, 50 ETH).
- **Universo pequeno.** BTC tem 63% do volume (US$ 88M de US$ 139M), ETH 23%, HYPE 7%. As alts (PUMP, PENDLE, ZEC, LINK, AAVE, FARTCOIN, DOGE, XMR, XPL) são apostas pequenas e, juntas, dão prejuízo.

## 2. De onde vem o lucro

| | HYPE | BTC | ETH |
|---|---|---|---|
| viés (posição média × movimento) | +$72.7K | −$60.6K | −$2.7K |
| timing (aumentar/reduzir) | +$237.8K | +$256.1K | +$130.3K |
| trades intradiários | +$58.3K | +$120.8K | +$26.5K |
| funding + taxas | −$10.1K | −$49.0K | −$13.4K |

- O BTC caiu US$ 19,4k no período, com a carteira comprada em média (3,1 BTC), e mesmo assim deu lucro: reduz nos repiques e volta a comprar mais baixo.
- O HYPE subiu US$ 47 e a carteira esteve sempre comprada, mas 3/4 do lucro vêm de aumentar antes das pernas de alta (jan, mai e jun/2026) e reduzir depois delas.
- O funding pesa (−US$ 66k, −9% a.a. sobre o nocional long de BTC e HYPE) porque quase todo o tempo está comprada e paga funding.

## 3. Gestão de risco e de capital

- **Sem stop e sem liquidação.** O pior PnL aberto num episódio foi −US$ 71k (PUMP, set/2025), que fechou com −US$ 56k. A maior perda de BTC (−US$ 46k, 13–14/ago/2025) foi um long de 8 BTC comprado na máxima.
- **Saques depois de lucro:** em 90% dos 10 dias com saque, os 3 dias anteriores eram positivos. Os depósitos (US$ 432k) entraram todos em jun/2025; depois disso só saiu dinheiro (US$ 310k em saques, US$ 100k para a HyperEVM em set/2026).
- **Subconta `0xb840…6361`** ("Sub account 1"): recebeu e devolveu ~US$ 950k em 9 envios entre jun e ago/2026. Ali a carteira perdeu US$ 53k (volume de US$ 2,7M) e hoje a subconta está parada com US$ 46k em USDC.
- 1,07M de MAX chegaram por `spotTransfer` em 13/jun/2026 (valor em USD zero na API, provavelmente airdrop). Há 108 HYPE em staking, sem relação com o desconto de taxa.

## 4. Dá para copiar?

- **Cópia de cada fill:** com 30 min de atraso, +US$ 646k contra +US$ 770k da carteira (84%); 1h, 83%; 2h, 87%; 4h, 77%. HYPE perde menos (91%), BTC mais (81%). O custo vem das limites: a cópia a mercado perde a entrada abaixo e a saída acima do preço.
- **Espelhar a posição:** aguenta até 24h de atraso (HYPE +US$ 280k contra +US$ 335k sem atraso; BTC +US$ 200k contra +US$ 283k) e quebra com 72h (BTC −US$ 49k). A vantagem está num horizonte de horas a poucos dias.
- **Regras:** a regra padrão do relatório (short com filtro de tendência) não serve para uma carteira que só fica comprada no HYPE e perde US$ 116k no teste. O clone por regressão também falha (R² teste −0,02). A compra de força em HYPE/ETH tem p-valores baixos, mas com 37–52 sessões; o BTC é ruído.

**Veredito:** trader discricionário de porte médio, com bom controle de tamanho e execução por limites, cujo resultado é concentrado em HYPE e no timing de swing em BTC/ETH. Seguir a carteira com até 1–2h de atraso preservaria ~85% do resultado no passado, mas não há regra mecânica por trás, e 16 meses com 51% de dias positivos é pouco para garantir que a vantagem continue.
