# Engenharia reversa: carteira `0xc7c3…1275`

`0xc7c37b0c7af5af560bf31b0bcbfec04b97361275` · [CoinGlass](https://www.coinglass.com/hyperliquid/0xc7c37b0c7af5af560bf31b0bcbfec04b97361275) · dados até 14/out/2026

Fonte: API pública da Hyperliquid. A conta é nova (primeiro trade em 15/jul/2026) e pequena: 621 fills, das quais 389 são fatias de TWAP, 3 eventos de ledger e 79 requisições no total. A API entrega o histórico inteiro: o PnL reconstruído a partir dos fills bate com o `portfolio` (US$ 22,0k contra US$ 22,2k). Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md). Os números por par de trades vêm de [`analise_extra.py`](analise_extra.py).

---

## Resumo

- **Quem é:** um trader **manual e pequeno**. Depositou **US$ 4 mil** e hoje tem US$ 19,6 mil, depois de sacar US$ 6,6 mil: **PnL de US$ 22,2 mil em 3 meses, ~5,5x o capital**. É esse retorno percentual que coloca a carteira em rankings. Opera pelo site, só em dias úteis, quase sempre às 7h ou 10h UTC.
- **O que faz:** começou com apostas direcionais curtas (ONDO, ETH, ouro) e, desde ago/2026, faz principalmente **trades de par neutros em dólar**: compra um ativo e vende outro no mesmo valor, apostando na **razão** entre eles. Foram 3 vezes BTC contra ouro, 1 vez ouro contra BTC e 2 vezes ETH contra BTC. As duas pernas são executadas com **duas TWAPs simultâneas** de 5 a 30 minutos.
- **Resultado:** 4 de 5 pares fechados deram lucro (+US$ 13,8 mil). As apostas de uma perna só renderam +US$ 10,2 mil. Taxas: −US$ 1,2 mil; funding: −US$ 0,2 mil.
- **Risco:** a alavancagem vem subindo junto com o tamanho: US$ 50 mil por perna em agosto, 100 mil em outubro e **250 mil no par aberto hoje**. Isso dá **25x sobre o patrimônio**. Cada 1% contra na razão ETH/BTC custa ~US$ 2,5 mil, ou 13% da conta.
- **Dá para replicar ou copiar?** **Não há base estatística.** São 6 pares e 5 apostas simples em 3 meses. A regra de entrada também não é consistente: nos pares BTC/ouro ele seguiu a tendência da razão, e nos dois últimos apostou na reversão. O que dá para aprender é a **forma de execução**: TWAP nas duas pernas, mesmo valor, pernas defasadas em ~20 segundos.

---

## 1. Quem é essa carteira

- **Manual, pelo site.** Não tem API wallet. Fez 79 requisições em US$ 2,2 milhões de volume. As ordens são `FrontendMarket` (a mercado, pela interface), TWAPs da interface e algumas ordens de gatilho:
  - um take-profit no ONDO;
  - take-profit e stop no fechamento do par de 26/ago.
- **Ordens "de desejo".** Deixa limites redondos longe do preço e depois cancela: compra de BTC a US$ 71.000 e 69.000, venda a US$ 87.500.
- **Horário.** Só opera em dias úteis, nenhum fim de semana. A maioria das execuções acontece às 7h e às 10h UTC, ou seja, 9h e 12h no horário de verão da Europa central. Isso combina com alguém operando na manhã europeia, mas é só uma estimativa.
- **Dinheiro:**
  - **Entrada de US$ 4.000 em 15/jul/2026** pela carteira de serviço `0x6b9e…0a24`. É a mesma *hot wallet* de exchange ou ponte que abasteceu a carteira [`0xfce0…`](../0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md). Ela atende centenas de usuários, então isso **não liga** as duas carteiras.
  - **Saídas:** US$ 4.910 para a HyperEVM (4/set) e um saque de US$ 1.679 (25/set). Desde então ele não depositou mais nada: o crescimento da conta é lucro reinvestido.

## 2. Os trades

**Apostas de uma perna só:**

| quando | trade | resultado |
|---|---|---|
| 15/jul | ONDO comprado duas vezes, por horas (55 mil e 50 mil ONDO) | +US$ 1.439 |
| 27/jul → 19/ago | 20 ETH comprados a US$ 1.966, vendidos a US$ 2.259 | +US$ 5.858 |
| 20 → 21/ago | 10 ouro (xyz:GOLD) comprados a US$ 4.488, vendidos a US$ 4.605 | +US$ 1.164 |
| 22 → 25/set | 1 BTC vendido a US$ 85.383, recomprado a US$ 83.643 | +US$ 1.740 |

**Pares** (o retorno da razão é medido como perna comprada ÷ perna vendida):

| par | comprado / vendido | tamanho por perna | execução | razão nos 30d antes | posição da razão no range de 30d | razão durante o trade | realizado |
|---|---|---|---|---|---|---|---|
| P1, 24 → 26/ago | ETH / BTC | ~US$ 50k | a mercado | +9,4% | 0,72 | −1,3% | −US$ 636 |
| P2, 26/ago → 2/set | BTC / ouro | US$ 50k | 2 TWAPs de 10 min | +6,6% | 0,86 | +4,9% | +US$ 2.116 |
| P3, 3 → 4/set | BTC / ouro | US$ 60k | a mercado | +12,4% | 0,89 | +2,8% | +US$ 1.738 |
| P4, 16 → 21/set | BTC / ouro | US$ 60k | a mercado | +21,3% | 0,77 | +12,1% | +US$ 7.143 |
| P5, 6 → 8/out | ouro / BTC | US$ 100k | 2 TWAPs de 6 min (saída: 2 de 5 min) | −12,9% | 0,04 | +3,3% | +US$ 3.465 |
| P6, 14/out → aberto | ETH / BTC | US$ 250k | 2 TWAPs de 30 min | −7,4% | 0,09 | −0,3% | aberto (~−US$ 0,4k) |

Como ler a tabela:

- **BTC contra ouro (P2–P4).** Entrou com a razão BTC/ouro subindo e perto do topo do range de 30 dias, e ela continuou subindo. É uma aposta **a favor da tendência** do "ouro digital" contra o ouro, e foi o melhor período da conta. O P4 sozinho rendeu US$ 7,1 mil: o BTC subiu 12% em cinco dias e o ouro ficou parado.
- **Ouro contra BTC (P5).** Virou o lado com a razão no fundo do range, depois de o BTC perder 13% contra o ouro em 30 dias. É uma aposta **na reversão**, e funcionou em dois dias.
- **ETH contra BTC (P1 e P6).** O P1 seguiu a tendência e perdeu. O P6 compra a razão no fundo do range (0,09) depois de cair 7% em 30 dias. É de novo uma aposta na reversão, agora **2,5 vezes maior** que qualquer trade anterior.
- **Execução.** As duas TWAPs começam com ~20 segundos de diferença e têm o mesmo valor em dólar (US$ 50k/50k, 100k/100k, 250k/250k). A conta fica neutra durante toda a montagem, sem ficar exposta a uma perna só. É o detalhe mais profissional da carteira.

## 3. Risco

- **Tamanho crescente.** A cada sequência de ganhos, o tamanho subiu: US$ 50k → 60k → 100k → 250k por perna. O patrimônio passou de ~US$ 10 mil para ~US$ 20 mil, mas a exposição bruta foi de ~US$ 100 mil para **US$ 495 mil (25x)**.
- **O par aberto.** São 99,8 ETH comprados contra 2,99 BTC vendidos. A API marca a liquidação em US$ 2.361 no ETH e US$ 86.520 no BTC, se uma perna andar sozinha. O risco real é a razão ETH/BTC: cada 1% contra custa ~US$ 2,5 mil, ou 13% do patrimônio. Uma queda de 5–6% na razão, que acontece algumas vezes por ano, apagaria a maior parte da conta.
- **Amostra.** O resultado vem de 5 pares fechados e 4 apostas simples, quase todos em 6 semanas. Um único trade (P4, +US$ 7,1 mil) responde por um terço do PnL.

## 4. O que esta carteira não é

- **Não é arbitragem.** Os pares são neutros em dólar, mas não em risco: BTC, ouro e ETH têm volatilidades muito diferentes, e a aposta é direcional na razão.
- **Não é bot.** São poucas ordens, todas pela interface, em horário comercial.
- **Não é uma estratégia com histórico.** Três meses de vida não permitem separar habilidade de sorte, nem testar a regra em outras moedas como foi feito com a [`0xfce0…`](../0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md).

## 5. Como monitorar

- **O par ETH/BTC aberto.** Vale ver se ele fecha em dias, como os anteriores (1 a 7 dias), e com que resultado. O tamanho de US$ 250 mil por perna é o teste real da estratégia.
- **TWAPs simultâneas em dois ativos** são a assinatura de um novo par. Aparecem em `userTwapSliceFills`.
- Rodar `python -m hlre.run 0xc7c37b0c7af5af560bf31b0bcbfec04b97361275` e depois o `analise_extra.py` atualiza a tabela de pares (os pares novos precisam ser acrescentados à lista `PAIRS` do script).

## 6. Limitações

- **Na seção 6 do relatório automático, as classificações por ordem** ("aumenta short", "reduz long") ficam distorcidas, porque fatias de TWAP de dois ativos se intercalam a cada poucos segundos. O resto do relatório (PnL, posições, episódios por ativo) não é afetado. Para esta carteira, a unidade certa é o par, e é isso que o `analise_extra.py` mostra.
- **Funding de ouro (HIP-3) e de BTC/ETH** foi pequeno no período (−US$ 187 líquido) e não muda nenhuma conclusão.
- **Nada aqui é recomendação de investimento.**
