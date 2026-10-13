# Engenharia reversa: carteira `0x0748…d4b2`

`0x0748e296e5a350ec36c8487a1cea406e1b57d4b2` · [CoinGlass](https://www.coinglass.com/hyperliquid/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2) · dados até 13/out/2026

Fonte: API pública da Hyperliquid. A conta existe desde jun/2024. A API entrega o **histórico de funding completo** (8.353 registros desde 8/jun/2024, que trazem o tamanho de cada posição dia a dia), o ledger completo (200 eventos), as últimas 1.897 ordens e **só os fills de 2/jun/2026 em diante** (32.695). Além disso, esta carteira usa muito a ordem **TWAP** nativa. As fatias de TWAP **não aparecem em `userFills`**, e o endpoint próprio delas só guarda as 2.000 mais recentes (1 → 12/out/2026). Por isso há execuções que não se vê: a posição "salta" sem fill visível em 17 pontos (~US$ 7,6M de nocional) desde jun/2026. A consequência é que **o PnL desta carteira é medido pelas posições diárias (funding) e pelo `portfolio`, e não pelos fills**. Tabelas e gráficos automáticos: [`relatorio_auto.md`](relatorio_auto.md). Os números deste texto que não estão lá são recalculados por [`analise_extra.py`](analise_extra.py), que também gera `img/livros.png`.

---

## Resumo

- **Quem opera:** uma pessoa, **manualmente**, pela interface (ou por uma interface de terceiros). São 4.189 requisições para US$ 952M de volume acumulado, sem API wallet. Usa ordens a mercado (`FrontendMarket`), limites, **TWAP nativo** (10–30 min, US$ 25k–430k cada) e, duas vezes, uma ordem *chase* (ALO reposta no topo do livro a cada ~2,5 s) para montar US$ 0,7M de LDO e US$ 0,6M de JTO sem pagar taxa de taker. Foi indicada pelo código de referral **`LIMINAL`** e tem uma subconta chamada "Liminal 1".
- **O que faz:** um **livro long/short de altcoins por fundamentos**, com viés comprado.
  - **Long:** tokens com receita ou recompra. DeFi "blue chip" (AAVE, UNI, LDO, PENDLE, MKR, ENA, JUP, AERO, JTO, RUNE), HYPE e PUMP (recompra com receita do protocolo), ZEC e, às vezes, BTC/ETH/SOL.
  - **Short:** L1s sem receita de taxa (ADA, XLM, XRP, SUI, AVAX, APT, HBAR, TON, INJ, MON, XPL), tokens de VC recém-lançados com desbloqueios (IP, WLD, LAYER, BERA, KAITO) e tokens de celebridade/política (WLFI, TRUMP).
  - Tem 7 a 12 posições abertas ao mesmo tempo, com exposição bruta de **1–2x o patrimônio**. Cada posição dura 6 dias na mediana (p90 de 30 dias).
- **Quanto ganhou:** **+US$ 12,4M all-time**. Perps somam +US$ 7,29M: preço +US$ 8,18M, funding −US$ 0,89M (a carteira paga por estar comprada). O resto (~US$ 5,1M) vem do spot: o airdrop de 11.429 HYPE, HYPE em carteira e em staking, e um trade de **PUMP spot** (300M comprados a US$ 0,0015 no fundo de jun/2026, somados ao estoque que já tinha, e vendidos aos poucos a US$ 0,0039–0,0062: +US$ 1,37M realizados, com 200M ainda em carteira). Começou com ~US$ 100k em jun/2024. **Sacou US$ 7,1M a mais do que depositou** e tem US$ 5,0M na conta hoje.
- **De onde vem o lucro:**
  - **O livro long** responde pela maior parte, mas é **beta**. Ele se move 1,38x o BTC, e o alfa sobre o BTC e sobre a média das altcoins não é significativo.
  - **O livro short** tem alfa estatístico: as moedas shortadas caíram ~190% ao ano mais que a média das alts (t = 2,6). Em dólares, porém, rendeu pouco (+US$ 0,8M de carry, US$ 0,65M disso num único dia: o colapso do OM). Funciona sobretudo como **hedge**: a correlação diária entre os dois livros é de −0,64.
  - **Mais da metade do lucro de preço vem do que acontece dentro do dia.** Carregar a posição média do dia anterior renderia US$ 3,0M. O real foi US$ 8,2M. A diferença (~US$ 5,2M) vem de aumentar e cortar enquanto o movimento acontece: reduziu antes do crash de 10/out/2025 e comprou no dia seguinte, e shortou OM na véspera do colapso.
- **A tese funciona fora da amostra?** Mais ou menos. Cestas fixas montadas só com os nomes do 1º ano (jun/2024–jun/2025) renderam **long−short +71% ao ano** de jul/2025 a out/2026 (Sharpe 1,38). Mas o IC 95% vai de −4% a +139%. O lado short (lançamentos de VC) fez quase todo o trabalho.
- **Risco:** sem stop de verdade. Os TP/SL ligados à posição ficam muito longe: alvos de −40% a −60% nos shorts e um stop de XLM a +155%. Foi liquidada uma vez: um long de LIT de US$ 1,0M em 24/jul/2026 (−US$ 99k). O maior drawdown foi de **−US$ 3,58M** (29/out/2025 → 21/jan/2026). Saca o lucro com frequência (em USDC, SOL, BTC, PUMP e HYPE).
- **Dá para copiar?** Só em tempo real. Espelhando a posição do dia anterior, sobram US$ 3,0M dos US$ 8,2M. Com 2 dias de atraso, US$ 1,3M. Com 3 dias, **zero**: o livro short vira prejuízo. O spot (PUMP, HYPE) e as TWAPs em andamento não aparecem no CoinGlass.
- **Agora:** livro **neutro**. São US$ 3,7M long (PUMP, ZRO, JUP, AAVE, AERO) contra US$ 3,9M short (ADA, XLM, SUI, XRP, INJ, MON), com PnL aberto de −US$ 0,23M. No spot: US$ 2,3M em USDC, 200M de UPUMP e 190M de MAX.

---

## 1. Quem é essa carteira

**Manual, com ferramentas de execução.**

| como executa | ordens (últimas 1.897) | uso |
|---|---|---|
| Limite GTC | 761 | entradas e saídas com preço definido |
| ALO com `cloid` (*chase*) | 746 | **só 2 vezes**: 2M LDO (16/jul/2026, US$ 0,74M) e 1M JTO (21/jul/2026, US$ 0,62M). A ordem é cancelada e reposta no melhor bid a cada ~2,5 s até encher, e o `cloid` codifica o tamanho restante |
| `FrontendMarket` | 353 | ordens a mercado da interface. Considerando todas as ordens executadas desde jun/2026, a mediana é de US$ 250k por ordem e o máximo, US$ 4,3M |
| TWAP nativo | (fora de `historicalOrders`) | 5 TWAPs de 1 a 12/out/2026 (JUP, ZRO ×2, UNI, AERO; 10–30 min). Antes disso, os saltos de posição sem fill (HYPE, LDO, UNI, JUP, NEAR, ADA, AAVE, AERO…) mostram o mesmo hábito |
| TP/SL e gatilhos | 35 | quase todos ligados à posição e muito longe do preço |

- **Não é bot.** Não há API wallet, são só 4.189 requisições para US$ 952M, e as ordens se concentram entre 11h e 15h UTC, em dias úteis.
- **Liminal.** A carteira entrou com o código de referral `LIMINAL` e criou uma subconta "Liminal 1". Nela fez **um único teste de cash-and-carry**: de 30/jul a 2/ago/2025, US$ 250k em spot (HYPE, BTC, ETH, SOL) contra short no perp. O resultado foi praticamente zero (o spot perdeu US$ 14k e o perp ganhou US$ 14k), e nunca mais usou a subconta.
- **Usuário antigo da Hyperliquid.** Recebeu 11.429 HYPE no airdrop de genesis (29/nov/2024), além de WOW, LICKO, KNTQ e MAX. Movimenta dezenas de milhares de HYPE entre o spot e o staking (hoje são 15,7k delegados), o que lhe dá 20% de desconto na taxa.
- **Uma liquidação.** Long de LIT de US$ 1,0M em 24/jul/2026 (−US$ 99k). Os outros 5 fills marcados como liquidação são a carteira **pegando o outro lado** de liquidações de terceiros (NEAR, AVAX, VVV). Nesses casos não foi ela a liquidada.

**O dinheiro.** Entraram US$ 6,5M em depósitos de USDC (28 vezes, de US$ 8k a US$ 1M), US$ 3,5M em HYPE vindo da HyperEVM e US$ 0,3M em FART. Saíram **US$ 17,8M**: US$ 5,9M em saques de USDC, US$ 2,75M de USDC para a HyperEVM, US$ 3,2M em HYPE, US$ 2,5M em SOL e US$ 1,5M em BTC (comprados no spot e retirados pela Unit logo em seguida) e US$ 1,9M em PUMP. O padrão é **sacar o lucro continuamente**: 63% dos 35 dias com saque vêm depois de 3 dias de PnL positivo (mediana de +US$ 66k), contra 55% na base. Além disso, desde jul/2025 a conta oscila entre US$ 3,2M e US$ 7,8M, apesar de +US$ 8,4M de PnL no período.

## 2. O livro e como ele mudou

![Livros](img/livros.png)

Maiores posições, em média diária por trimestre:

| trimestre | long | short |
|---|---|---|
| 3T24 | LDO, PENDLE, UNI, MKR, RUNE, AAVE | WLD |
| 4T24 | PENDLE, UNI, LDO, RUNE, JTO | — |
| 1T25 | BTC, JTO, AAVE, ENA, MKR, SOL | — |
| 2T25 | BTC, LDO, SOL, AAVE, JUP, ETH, ENA | IP, BERA, LAYER, WLD |
| 3T25 | **ETH (US$ 1,8M)**, BTC, AAVE, HYPE, ENA, PUMP | IP, HBAR, XLM, WLD, XRP, APT, SUI |
| 4T25 | **HYPE (US$ 1,8M)**, PUMP, AAVE, ZEC, BTC, PENDLE | **ADA**, XLM, APT, TON, TRUMP |
| 1T26 | **PUMP (US$ 2,2M)**, HYPE, SOL, AAVE, BTC, TAO | ADA, AVAX, XLM, MON, XPL |
| 2T26 | **BTC (US$ 4,0M)**, AAVE, HYPE, PUMP, ZEC, LDO | ADA, AVAX, WLFI, SUI, WLD |
| 3T26 | **AAVE (US$ 2,0M)**, BTC, ZEC, JUP, HYPE, LDO, SOL | ADA, SUI, AVAX, INJ, XLM, WLFI, XRP |
| out/26 | JUP, AAVE, ZRO, BTC, AERO, UNI, PUMP | ADA, XLM, SUI, XRP, MON, INJ |

- **2024: só DeFi comprado.** Um livro long de protocolos com receita (LDO, PENDLE, UNI, MKR, RUNE, AAVE), com 2–2,4x o patrimônio e sem hedge.
- **A partir de abr/2025 aparece o lado short.** Primeiro em lançamentos de VC (IP, BERA, LAYER, WLD, KAITO). Desde jul/2025, também nas "L1 velhas" (ADA, XLM, XRP, HBAR, APT, SUI, AVAX). O short cobre de 3% a 100% do long (tipicamente 35–60%, em medianas trimestrais). Em out/2026 o livro está neutro.
- **Os longs giram com as narrativas de receita:** ETH no verão de 2025, HYPE e PUMP (recompras) no fim de 2025, BTC no fundo de 2026, AAVE e ZEC no 3T26, e agora JUP, ZRO e AERO.
- **ADA é o short permanente.** Está vendido em 353 dias, nunca comprado, e hoje com 5M de ADA (US$ 1,2M).

## 3. O playbook

### 3.1 Comprar receita, vender narrativa sem receita

A tese é fundamentalista. Fica comprado em tokens com fluxo de caixa ou recompra e vendido em tokens que dependem de narrativa ou que têm oferta nova entrando (desbloqueios). Hedge e tese aparecem no mesmo livro:

| livro | retorno anual | beta ao BTC | alfa anual (IC 95%) | leitura |
|---|---|---|---|---|
| long (pesado pelo nocional) | +13% | **1,38** | +1% (−91% a +90%) | beta alavancado, sem alfa |
| long − média das alts | +16% | 0,0 | +16% (−51% a +85%) | escolha dos longs: não significativa |
| short (ganho quando cai) | +189% | −1,40 | **+181% (+36% a +359%)** | as moedas shortadas caíram muito mais |
| média das alts − short | +189% | 0,0 | **+188% (+65% a +341%)**, t = 2,6 | o alfa da carteira está **no lado short** |

*(Retornos diários com a posição média do dia anterior, de jun/2024 a out/2026, nos dias com cada livro acima de US$ 200k.)*

Em dólares, a história é outra. O carry do short soma só **+US$ 0,82M**, e **+US$ 0,65M** disso vêm de um dia: OM, em 13/abr/2025 (o short de US$ 0,74M foi aberto em 11–12/abr, na véspera da queda de −84%, e fechado no mesmo dia). Sem OM, o short empata (+US$ 0,16M). A explicação é que o short é **maior quando as alts sobem**: perdeu US$ 1,4M no 3T25 e US$ 1,6M no 3T26, quando os longs ganharam US$ 2,0M e US$ 4,1M. Ele ganha nos trimestres ruins: +US$ 1,5M no 4T25 e +US$ 0,9M no 2T26. É um hedge que se pagou e que, no meio do caminho, pegou alguns colapsos.

**Os melhores e piores nomes** (carry, jun/2024 → out/2026):

| | ganhou | perdeu |
|---|---|---|
| long | ETH +1,02M, AAVE +0,99M, BTC +0,79M, ZEC +0,65M, SOL +0,38M, TAO +0,30M | kBONK −0,42M, HYPE −0,28M, RUNE −0,27M, PUMP −0,27M (o perp; o spot de PUMP ganhou), JTO −0,19M |
| short | ADA +0,69M, OM +0,65M, WLFI +0,33M, XLM +0,32M, LAYER +0,19M, HBAR +0,18M | WLD −0,47M, XRP −0,46M, SUI −0,39M, IP −0,38M, SOL −0,23M |

### 3.2 Quando aumenta e quando corta

Contexto de cada moeda nos dias em que a posição mudou mais de US$ 100k, comparado com todos os dias de todas as moedas da carteira (medianas):

| decisão | n | retorno 7d antes | retorno 30d antes | distância da máxima de 30d | retorno 7d depois |
|---|---|---|---|---|---|
| aumenta long | 511 | **+1,3%** (p<0,001) | **+3,7%** (p<0,001) | −12,6% (p<0,001) | −1,6% |
| reduz long | 506 | +0,4% | **+9,0%** (p<0,001) | −11,7% | −2,0% |
| aumenta short | 200 | **+1,6%** (p=0,001) | −4,5% | −13,7% (p=0,006) | **−3,7%** (p=0,03) |
| reduz short | 218 | −1,6% | −2,7% | −14,2% | −0,3% |
| base | | −1,3% | −4,5% | −16,2% | −1,3% |

- **Longs: momentum.** Compra os nomes "bons" quando já estão subindo e perto da máxima de 30 dias. Realiza depois de +9% em 30 dias. O retorno depois da compra é igual ao da base, ou seja, o timing dos longs não acrescenta nada além da exposição.
- **Shorts: vende o repique numa tendência de baixa.** Aumenta o short depois de +1,6% em 7 dias em moedas que caíram 4,5% em 30 dias. Nos 7 dias seguintes elas caem 3,7%, contra −1,3% da base. **Esse é o timing que funciona.**
- **Gira dentro do dia.** O PnL de preço real nos perps foi de **US$ 8,18M** (`portfolio` menos funding). Carregar a posição média do dia anterior renderia **US$ 3,0M**. Os ~US$ 5,2M de diferença vêm de mudar a posição enquanto o mercado se move. Em 10/out/2025, o livro caiu de US$ 2,7M long e 1,9M short para ~US$ 1,0M e 0,6M, e no dia 11 ele comprou US$ 3,4M (HYPE, ZEC, AAVE, SOL, PUMP) e cobriu os shorts. Nesse trimestre o carry perderia US$ 1,29M, e o real empatou (+US$ 0,05M). No 1T25 foi o mesmo: o carry perderia US$ 1,08M e o real ganhou US$ 0,53M. Esse ganho dentro do dia aparece do 1T25 ao 1T26 (+US$ 1,0M a +1,6M por trimestre) e **some em 2026**: zero no 3T26 e −US$ 0,24M em out/2026. Pode ser fase de mercado ou perda da vantagem; só dá para saber com mais tempo de dados.

### 3.3 Spot: PUMP, HYPE e saída do lucro

- **PUMP spot.** Em 5/jun/2026 comprou **300M de UPUMP a US$ 0,0015**, perto da mínima histórica do token, e somou ao estoque que já tinha. Vendeu 200M em 15–17/jun quase no zero a zero (−US$ 51k), 300M a US$ 0,0047 em 22/ago (+US$ 859k), 100M a US$ 0,0039 em 6/set (+US$ 211k, recomprados no dia seguinte a US$ 0,0044) e 100M a US$ 0,0062 em 7/out (+US$ 352k). Ainda tem 200M no spot **e** 200M long no perp (US$ 1,0M cada). Também retirou PUMP para outras carteiras várias vezes (US$ 1,9M desde nov/2025). Somando perp e spot, PUMP é uma das maiores apostas da carteira: convicção alta e tamanho grande.
- **HYPE.** É usuário antigo (airdrop de genesis), põe em staking e move HYPE entre o HyperCore e a HyperEVM: entraram 59k HYPE (US$ 3,5M) e saíram 82k (US$ 3,2M). No perp, HYPE foi o maior long do 4T25 (US$ 1,8M de média).
- **SOL e BTC no spot são só a porta de saída.** Compra USOL ou UBTC com USDC e, no mesmo minuto, envia para fora pela Unit. Foram US$ 2,5M em SOL (desde mai/2025) e US$ 1,5M em BTC (ago/2026). Não é posição.

### 3.4 Gestão de risco

- **Alavancagem moderada.** A exposição bruta fica em 1–2x o patrimônio desde 2025 (foi 2–4x em 2024, com a conta pequena). A exposição líquida vai de −0,0x (hoje) a 1,4x (1T26).
- **Sem stop.** Os TP/SL ligados às posições atuais estão longe demais para servir de stop: TP de ADA a US$ 0,12 (−41% sobre a entrada), XLM a US$ 0,11 (−44%), SUI a US$ 0,55 (−47%), INJ a US$ 3,0 (−58%), e stop de XLM a US$ 0,50 (+155%). Esses alvos mostram onde ele acha que essas moedas vão parar. O risco é gerido reduzindo o livro inteiro de uma vez, à mão, como em 10/out/2025.
- **Drawdowns.** A conta perdeu US$ 3,58M entre 29/out/2025 e 21/jan/2026: o livro long de HYPE, PUMP e SOL caiu mais que o short. No 2T26 (−US$ 0,19M no total) o long perdeu US$ 1,7M de carry e o short devolveu US$ 0,9M.
- **Funding.** Pagou US$ 0,89M em 28 meses (US$ 0,81M nos longs). É o custo de carregar o viés comprado em perp.

## 4. De onde veio o dinheiro

| componente | resultado |
|---|---|
| Perps, preço | +US$ 8,18M |
| ↳ carregar a posição do dia anterior | +US$ 3,01M (long +2,19M, short +0,82M) |
| ↳ mudanças dentro do dia | ~+US$ 5,2M |
| Perps, funding | −US$ 0,89M |
| **Perps, total (`portfolio`)** | **+US$ 7,29M** |
| Spot (PUMP, HYPE de genesis e em carteira, airdrops) | ~+US$ 5,1M |
| **Total all-time** | **+US$ 12,40M** |

Por trimestre (PnL total): +0,34M (3T24), +0,64M (4T24), −0,28M (1T25), **+3,24M** (2T25), +1,82M (3T25), −1,07M (4T25), **+3,04M** (1T26), −0,19M (2T26), **+5,09M** (3T26), −0,26M (out/26).

## 5. Dá para copiar?

Espelhando a posição de perp com atraso (carry, sem custos):

| atraso | total | livro long | livro short |
|---|---|---|---|
| 1 dia | +US$ 3,01M | +2,19M | +0,82M |
| 2 dias | +US$ 1,32M | +1,33M | −0,01M |
| 3 dias | +US$ 0,15M | +1,57M | −1,41M |
| 7 dias | +US$ 0,26M | +1,48M | −1,22M |

- **O lado long sobrevive ao atraso, e o short não.** Na marcação horária do período com fills, os três maiores longs mantêm o resultado mesmo com 7 dias de atraso: AAVE +US$ 1,67M sem atraso e +1,92M com 168h, ZEC +1,08M e +1,37M, BTC +0,61M e +0,49M (seção 9 do relatório automático). O short depende de vender o repique e cobrir na queda, ambos em poucos dias. Copiado com 3 dias de atraso, perde US$ 1,4M.
- **O real (US$ 8,2M) fica bem acima do que um copiador de 1 dia pegaria (US$ 3,0M).** O que dá dinheiro é a reação dentro do dia.
- **Pontos cegos do CoinGlass:** o PUMP spot (o melhor trade de 2026) não aparece como posição, e uma TWAP em andamento só aparece aos poucos.

## 6. Dá para replicar com regras?

**Em parte, como tese de cestas, e não como cópia do timing.**

- **Cesta fixa com os nomes que ele carregou** (13 longs, 17 shorts, peso igual, jun/2024 → out/2026): long−short **+45% ao ano, Sharpe 1,11**, mas com −41% em 2024, +40% em 2025 e +114% em 2026. Com o mesmo nocional long/short da carteira, a cesta fixa renderia **+US$ 5,0M de carry**, contra +US$ 3,0M do carry real. Ou seja, a troca de moedas no dia a dia **não** melhorou o resultado de carregar a cesta. *(Viés: os nomes foram escolhidos olhando a carteira inteira.)*
- **Fora da amostra:** com só os nomes do 1º ano (long: AAVE, BTC, ENA, ETH, JTO, JUP, LDO, MKR, PENDLE, RUNE, SOL, UNI; short: BERA, IP, KAITO, LAYER, WLD), testados de jul/2025 a out/2026, a cesta faz long **+4%** ao ano, short **−67%** ao ano, BTC −11%. Long−short dá **+71% ao ano** (IC 95% de −4% a +139%, bootstrap por semanas) e Sharpe 1,38. **O sinal está no short de lançamentos de VC com desbloqueio.** O long de DeFi só acompanhou o mercado.
- **O que a regra não pega:** a parte dentro do dia (~US$ 5,2M), que depende de ler o mercado e reagir (crash de 10/out/2025, OM), e os trades de convicção no spot (PUMP no fundo).
- **Próximo passo para uma regra de verdade:** trocar a lista feita à mão por critérios objetivos medidos antes, como receita/FDV (DefiLlama), calendário de desbloqueios e idade do token, e testar no universo inteiro de perps com `hlre.universe`.

## 7. Conclusão

É um **gestor discricionário de long/short em altcoins, de orientação fundamentalista**: compra protocolos que geram receita ou recompram o token e vende L1s sem receita e tokens de VC com oferta nova chegando. O resultado (+US$ 12,4M em 28 meses, saindo de ~US$ 100k) tem três motores:

1. **Beta comprado com hedge**, a parte maior e menos especial.
2. **Shorts em lançamentos de VC e "L1 zumbis"**, onde está o alfa estatístico, incluindo colapsos como o de OM.
3. **Reação rápida dentro do dia** (cortar antes de crashes e comprar o pânico), que soma mais da metade do lucro de preço e é o que não se copia.

Além disso, acerta trades grandes de convicção no spot (PUMP). Os pontos fracos são a ausência de stop, o funding pago para ficar comprado e drawdowns de até US$ 3,6M quando os longs de narrativa (HYPE, PUMP, SOL) caem juntos. Para acompanhar, observe o livro inteiro (o lado short e o líquido, não só a maior posição), as TWAPs em andamento e o saldo spot de UPUMP.

*Nada aqui é recomendação de investimento.*
