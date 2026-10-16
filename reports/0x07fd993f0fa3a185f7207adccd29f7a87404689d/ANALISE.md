# Engenharia reversa: carteira `0x07fd…689d`

`0x07fd993f0fa3a185f7207adccd29f7a87404689d` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x07fd993f0fa3a185f7207adccd29f7a87404689d) · dados até 16/out/2026

Fonte: API pública da Hyperliquid. A conta é um **vault** (`userRole = vault`), ativa desde 29/jan/2025. Com US$ 1,02 bi de volume, a API só guarda 3 dias de fills (24.011 fills desde 13/out/2026). O PnL por moeda antes disso é **estimado** pelo histórico de funding. Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo

- **Quem é:** um **vault operado por bot de market making / livro neutro**. Todas as 1.304 ordens guardadas são limite `Alo` (post-only), 100% maker, 866 execuções por dia ativo, sem agente de API visível (o líder do vault envia as ordens). O depósito de criação veio de `0x3671…e963` (conta de US$ 6,2M com PnL all-time de +US$ 71,9M): é provavelmente o líder do vault (inferência).
- **Resultado:** **+US$ 275k all-time** em 21 meses, sobre uma conta de **US$ 9,11M** e **US$ 1,02 bi de volume**. Margem fina: ~2,7 bp do volume. Sem liquidações.
- **De onde vem:** do spread e dos rebates de maker (taxas de só −US$ 926 nos 3 dias de fills, ou seja, rebate quase zera a taxa), contra **−US$ 2,38M de funding pago**. O PnL de preço estimado por moeda é ruído grande dos dois lados (S −US$ 828k, NEAR −US$ 573k, MINA −US$ 569k; XMR +US$ 391k, HYPE +US$ 312k). É estimativa, não exato.
- **Estilo:** livro grande e diversificado (60 posições), **long em majors e "qualidade"** (ETH US$ 2,6M, XMR US$ 3,0M, AAVE US$ 1,9M, BTC, BNB, PENDLE, LDO, POL, PAXG) e **short em altcoins fracas** (TIA, ZRO, STRK, W, OP, FIL, ATOM, WLFI…). Exposição bruta de US$ 33,3M contra líquida de US$ 4,9M: perto de neutro.
- **Hoje:** US$ 33M de nocional, 3,2x de alavancagem mediana em out/2026 (era 1,7–2,3x no meio do ano). Maiores perdas abertas: PURR −US$ 339k, ZRO −US$ 318k, STRK −US$ 303k, TIA −US$ 252k.
- **Dá para copiar?** **Não.** O relatório barra a simulação: é padrão de market maker. O lucro é spread e rebate, que um copiador a mercado com atraso paga em vez de ganhar. A forma de "copiar" é depositar no vault.

---

## 1. Como opera

- **Bot, só post-only.** 1.304 de 1.304 ordens são `Limit Alo`, nenhuma a mercado, nenhum gatilho (sem stop). 100% do nocional é maker.
- **Cotação contínua em muitas moedas.** 4 sessões de mediana 410 ordens e 749 min; STBL (446 ordens), W (282), OP (262), FIL (202) são as mais giradas. Ordens abertas na hora da coleta mostram cotação dos dois lados (ex.: compra em FIL, venda em SOL).
- **Tempo em posição curto, mas com estoque.** Tempo mediano em posição de 1,6h e 28% do volume fechado em menos de 30 min; ao mesmo tempo carrega 60 posições direcionais de dias ou mais. Parece um market maker que **inclina o estoque** (long majors, short alts) em vez de zerar.
- **Escala:** equity de perp de US$ 315k (jan/2025) para US$ 13,5M (set/2026); exposição bruta de US$ 690k para US$ 33M.

## 2. De onde vem o lucro

- O PnL de +US$ 275k é pequeno para US$ 1 bi de volume. Com −US$ 2,38M de funding pago (longs em majors pagam funding positivo), o resultado de preço + spread + rebate tem que ser da ordem de +US$ 2,6M (inferência a partir do total).
- No período dos fills (3 dias) o PnL de preço exato é misto: XMR +US$ 41k; PURR −US$ 104k, POL −US$ 85k, LDO −US$ 77k. Episódios: BLUR short +US$ 48k (com −US$ 12k de funding); OP −US$ 21k, PENDLE −US$ 23k, TIA −US$ 17k.
- As tabelas de gatilho de entrada/saída (NEAR, MINA) não têm p-valor significativo; com um bot de MM não há gatilho discricionário para achar.
- O relatório marca 63 mudanças de posição sem fill visível (~US$ 128k, quase todo em W): provável TWAP ou transferência; afeta pouco.

## 3. Gestão de risco e de capital

- **Capital de terceiros:** 10.378 depósitos (US$ 63,3M) e 7.580 saques (US$ 54,7M) no vault. O equity varia com o fluxo de depositantes, não só com o PnL.
- **Livro quase neutro, mas não hedgeado moeda a moeda.** Long em majors e short em alts funciona como um *spread* "majors vs. alts". Um rali de alts (como TIA +30% em 7 dias antes da entrada) machuca os shorts; vários já estão no vermelho (ZRO, STRK, TIA, GRASS, WLD).
- Alavancagem por moeda de até 40x cross (BTC) e 25x (ETH), mas a alavancagem da conta fica em 2–3x. Liquidações dos shorts estão longe do preço atual. Nenhuma liquidação no histórico.
- Funding é o custo estrutural: −US$ 2,38M, mais de 8 vezes o PnL all-time.

## 4. Dá para copiar?

O teste de copiabilidade reprova: 866 execuções por dia ativo e 100% maker. Espelhar a posição das moedas principais com atraso dá resultados de poucos milhares de dólares, para cima e para baixo (NEAR +US$ 13k com 72h, MINA −US$ 5,6k com 24h). Ou seja, não há sinal direcional. A regra short-bias testada em S (+US$ 144k no teste) não tem nada a ver com o estilo da carteira (correlação 0,00 com a posição real), e o clone por regressão tem R² de teste −5,3.

**Veredito:** vault de market making com inclinação long-majors/short-alts, US$ 9M de conta e +US$ 275k em 21 meses, com o funding comendo quase todo o ganho de spread. **Não copiável.** Quem quiser essa exposição tem que depositar no vault, e o histórico (~3% sobre o capital médio em quase 2 anos) é fraco para o risco.
