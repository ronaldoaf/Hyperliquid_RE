# Engenharia reversa: carteira `0xa844…e802`

`0xa844d7ac9fa3424c4fd38a25baa23e460ec3e802` · [CoinGlass](https://www.coinglass.com/hyperliquid/0xa844d7ac9fa3424c4fd38a25baa23e460ec3e802) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. Os fills cobrem o histórico inteiro: são 26.779, desde 19/jan/2025, e a conta começou em 22/jan/2025. Por isso o PnL por ativo é **exato**. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo
- **Quem é:** um **vault** da Hyperliquid (`userRole = vault`). Teve 1.913 depósitos e 1.269 saques de cotistas, que somam cerca de US$ 3,5M em cada direção. Não tem agentes de API nem subcontas.
- **Resultado:** +US$ 172,5k de PnL all-time em perps, sobre US$ 125M de volume. O valor atual da conta é US$ 374k.
- **De onde vem:** de **shorts de altcoins** carregados por dias (ADA +US$ 40,9k, XRP +US$ 31,7k, SEI, ONDO), de SOL e PAXG comprados e de ETH. BTC, que é 58% do volume, termina com **−US$ 14,6k**, e HYPE com −US$ 42k. As taxas comeram US$ 48,4k e o funding mais US$ 13,9k.
- **Estilo:** discricionário e **manual**. 66% das ordens são `FrontendMarket` (enviadas pela interface web), 94% do nocional é taker, a mediana é de 2 ordens por sessão e quase não há stops (6 ordens de gatilho em 954).
- **Hoje:** a conta está **zerada**: nenhuma posição aberta, tudo em USDC (US$ 374k sacáveis). Não há risco aberto.
- **Dá para copiar?** Em parte. Com 30 min de atraso, a cópia fica com 88% do resultado. Com 2h, só com 40%. A parte boa (shorts de alts, ordens limite) sobrevive ao atraso. Os trades rápidos em BTC, ETH e HYPE, que não dão lucro, pioram com o atraso.

---

## 1. Como opera

- **Manual, pela interface.** Das últimas 954 ordens, 628 são a mercado via frontend e 281 são limite `Gtc`. A carteira opera em 349 dos 630 dias, com mais atividade em dias úteis (sábado e domingo somam 15%). Faz cerca de 15 execuções por dia ativo e só 6% do nocional é maker. Não é bot nem market maker.
- **Dois modos bem diferentes:**
  1. **Scalping direcional em BTC, ETH e HYPE.** BTC e ETH somam US$ 101M dos US$ 125M de volume. Em ETH, os 127 episódios têm duração mediana de 0,2 dia. Os longs entram depois de alta (sessões de "aumenta long" com +1,6% nas 24h anteriores e no topo do range de 7 dias, 0,82, p<1e-4). Ou seja, ele **compra rompimento**. Esse modo não dá lucro: BTC −US$ 14,6k, HYPE −US$ 42k, e ETH só +US$ 14,7k antes de US$ 11,5k de taxas.
  2. **Shorts de swing em altcoins**, por dias ou semanas. Em ADA, os shorts são abertos com o preço alto no range (0,67, p=0,001) e reduzidos depois de queda forte (−10% em 7 dias, p=0,02). Em XRP, a redução acontece no fundo do range (0,13, p<0,001). 83% das reduções em ADA e 68% em XRP saem com lucro. O melhor exemplo é o short conjunto em ADA, XRP e ETH de 20/out a 5/nov/2025, logo depois do crash de 10/out: +US$ 30,6k em ADA e +US$ 15,7k em XRP.
- **Preço médio:** em ADA, 64% dos aumentos foram feitos com a posição no prejuízo, ou seja, ele faz preço médio contra o movimento. Em ETH e XRP isso é neutro.

## 2. De onde vem o lucro

| fonte | PnL |
|---|---|
| ADA + XRP + SEI + ONDO + ZEC + INJ (shorts de alt, na maioria) | ≈ +US$ 112k |
| SOL + PAXG (longs) | +US$ 43,8k |
| ETH (preço, antes das taxas) | +US$ 14,7k |
| HYPE | −US$ 8,5k em preço (−US$ 42k na simulação, que inclui as taxas) |
| BTC | −US$ 14,6k |
| funding | −US$ 13,9k |
| taxas | −US$ 48,4k |

- **Ordens limite × mercado:** os fills maker (US$ 7,6M de volume) geram +US$ 326k. Os taker (US$ 116M) geram **−US$ 145k**. O lucro todo está nas ordens pacientes. As ordens a mercado, que são quase todo o volume, destroem valor. Isso é inferência a partir da tabela por tipo de execução, já que os dois modos se misturam.
- **Funding:** os longs pagaram −US$ 21k (cerca de −11% ao ano sobre o nocional) e os shorts receberam +US$ 7k.
- **Concentração:** o melhor episódio de ADA responde por 52% dos ganhos de ADA. Os grandes ganhos (ETH long jul/2025 +US$ 38,6k, HYPE long ago/2025 +US$ 42,9k) se alternam com grandes perdas (BTC long out/2025 −US$ 50,8k, HYPE long nov/2025 −US$ 44,8k).

## 3. Gestão de risco e de capital

- **Alavancagem baixa:** a mediana mensal ficou entre 0,0x e 1,5x. A exposição bruta máxima mensal foi de US$ 578k (out/2025), contra um equity de US$ 880k.
- **Nenhuma liquidação.** Os 5 fills especiais são 2 ADLs a favor (XPL +US$ 5,6k, INJ +US$ 12,3k no crash de 10/out/2025) e o fechamento de XPL.
- **Stops quase inexistentes.** Os prejuízos são aceitos depois de longos períodos contra (ADA short jun–ago/2025: preço +64% contra, −US$ 13,2k).
- **Capital do vault:** o equity subiu de US$ 80k para US$ 888k (nov/2025) com aportes de cotistas e depois caiu para US$ 222k–260k em 2026 com saques. Desde fev/2026 a exposição é mínima (0,0–0,2x), com um pico de 1,0x em set/2026.

## 4. Dá para copiar?

- A carteira passa no teste de copiabilidade: 19% do volume fica aberto menos de 30 min e o tempo mediano em posição é de 4,6h.
- Copiando cada fill a mercado: 30 min de atraso → 88% (+US$ 158,6k); 1h → 74%; 2h → 40%; 4h → 38%. O drawdown da cópia (cerca de −US$ 100k a −US$ 124k) é igual ou maior que o da própria carteira (−US$ 96,8k).
- **Por ativo:** ADA, XRP, SOL, PAXG, ONDO e SEI ficam com 95% a 110% mesmo com atraso. Espelhar a posição em ADA com 24h de atraso ainda dá +US$ 39,9k. Já BTC piora de −US$ 14,6k para −US$ 80k com 4h de atraso, e ETH vira negativo com 1h de atraso.
- **Regra fora da amostra:** a regra testada em ETH (short-bias com filtro de tendência) não tem a ver com o estilo da carteira, que em ETH faz scalping comprado. A correlação com a posição real é de 0,05 e o clone tem R² de teste de −0,81. Não serve como descrição da carteira.
- A forma mais sensata de copiar é seletiva: seguir **só os shorts de altcoins de vários dias e os longs de PAXG/SOL**, e ignorar BTC, ETH e HYPE. Isso é inferência a partir das tabelas por ativo e não foi simulado como estratégia separada.

**Veredito:** vault discricionário que ganha com shorts pacientes em altcoins e perde com scalping a mercado em BTC, ETH e HYPE. O lucro de US$ 172k é real, mas modesto para US$ 125M de volume, e é muito consumido por taxas. Hoje a conta está parada em caixa. Como vault, dá para simplesmente depositar nele, mas a atividade recente é baixa. Copiar tudo só funciona com atraso curto. A parte que vale a pena seguir é a dos swings em alts.
