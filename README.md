# Hyperliquid RE: engenharia reversa de carteiras lucrativas

Ferramentas e relatórios para entender **o que** carteiras lucrativas da Hyperliquid fazem, **como** executam, **de onde** vem o lucro e **se** dá para replicar ou copiar.

Tudo é feito com dados públicos: a API `POST https://api.hyperliquid.xyz/info` (não precisa de chave) e, para preços horários antigos, o arquivo público de klines da Binance.

## Carteiras analisadas

| carteira | veredito curto | análise |
|---|---|---|
| `0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8` | Trader **discricionário manual**, viés **vendido** concentrado em BTC perp; vende força, carrega a tendência. Lucro concentrado num short de 158 dias (out/2025 → mar/2026, +US$ 3,07M), mais US$ 1,03M de funding. Alavancagem de 5–17x, sem stop, uma liquidação de US$ 4,2M. O short de HYPE é hedge de ~91k HYPE em staking em carteiras ligadas. | [ANALISE.md](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/ANALISE.md) · [relatório automático](reports/0xcac1f1c3e4599e044dc2a9d38a9b6ef1af1bdae8/relatorio_auto.md) |
| `0xfce053a5e461683454bf37ad66d20344c0e3f4c0` | Trader **manual (app de celular)** e **só vendido**, com dois livros: (1) short de memecoins com compradores lotados (funding alto, moeda já fora do topo), segurado por semanas, +US$ 3,4M; (2) short macro de BTC/ETH a partir do topo de out/2025, aumentado depois da quebra de nov/2025 (até US$ 27M), +US$ 6,3M. Sem stop; margem trazida de fora quando precisa e lucro sacado em seguida. US$ 10,8M em 22 meses, mas −US$ 1,06M nos últimos 4 meses. O padrão das alts tem vantagem no universo inteiro da Hyperliquid; o macro não vira regra. | [ANALISE.md](reports/0xfce053a5e461683454bf37ad66d20344c0e3f4c0/ANALISE.md) · [relatório automático](reports/0xfce053a5e461683454bf37ad66d20344c0e3f4c0/relatorio_auto.md) |
| `0x16bf84af3f85f8c8a97597bf2be549dfe0dee637` | **Swing trader manual de BTC nos dois lados**, contra o movimento curto: vende repiques no topo do range de 7 dias e compra quedas no fundo, entra com escadas de limites (ordem *Scale* da interface) e sai com blocos agressivos de 50–250 BTC. Longs de prazo maior ficam no **spot UBTC** (sem funding nem liquidação), trocados com o perp no mesmo minuto. Aporte único de 27 BTC (US$ 3,0M) em out/2025 → US$ 9,09M, +US$ 6,09M em 12 meses, sem saques. Extras: prata HIP-3 depois do crash (+US$ 1,54M) e um short de ZEC parabólico (−US$ 0,58M). Alavancagem de 1–3x, sem stop. A regra mecânica equivalente não tem vantagem. | [ANALISE.md](reports/0x16bf84af3f85f8c8a97597bf2be549dfe0dee637/ANALISE.md) · [relatório automático](reports/0x16bf84af3f85f8c8a97597bf2be549dfe0dee637/relatorio_auto.md) |
| `0x0748e296e5a350ec36c8487a1cea406e1b57d4b2` | **Long/short discricionário de altcoins por fundamentos**: comprado em tokens com receita ou recompra (AAVE, UNI, LDO, PENDLE, JUP, HYPE, PUMP, ZEC), vendido em L1s sem receita e lançamentos de VC com desbloqueio (ADA, XLM, XRP, SUI, AVAX, IP, WLD, WLFI). Exposição bruta de 1–2x, execução manual com TWAP nativo e *chase*. +US$ 12,4M em 28 meses a partir de ~US$ 100k (perps +US$ 7,3M, PUMP spot e HYPE o resto), US$ 7,1M sacados. O livro long é beta; o alfa está no short (lançamentos de VC) e em reagir dentro do dia (~US$ 5,2M dos US$ 8,2M de preço). A cesta da tese, fora da amostra, dá +71% a.a. long−short, com IC que encosta no zero. | [ANALISE.md](reports/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2/ANALISE.md) · [relatório automático](reports/0x0748e296e5a350ec36c8487a1cea406e1b57d4b2/relatorio_auto.md) |
| `0x8bae3527e5a33fa0cf184f37bc112d071463ab6d` | **Não é estratégia de mercado: transferência de valor em livros ilíquidos.** São 50 "eventos" em 30 altcoins pouco negociadas (GAS, NEO, CELO, IOTA, FTT, RSR, kNEIRO, BSV…). Em cada um, a carteira compra US$ 1–2M **~10% abaixo do preço justo**, num preço que **nunca existiu na Binance**. Em 2025 a ordem limite dela é atingida por um vendedor **0,1–0,5 s depois** de entrar no livro; em 2026 ela compra uma venda barata que já está à espera. Desconto embutido: US$ 7,6M. Total de +US$ 12,0M em 15 meses sobre US$ 0,5M depositados. A carteira que a indicou (`0x9458…ec04`, código com um único indicado) fez o mesmo de fev a nov/2025 (+US$ 11,1M) e passou o dinheiro para esta no mesmo dia. Ao lado disso há um livro legítimo de ações HIP-3 (+US$ 2,4M, Intel +1,4M). A hipótese mais provável é dreno de contas de terceiros (chaves de API vazadas); confirmar pelos hashes dos fills. Não copiável. | [ANALISE.md](reports/0x8bae3527e5a33fa0cf184f37bc112d071463ab6d/ANALISE.md) · [relatório automático](reports/0x8bae3527e5a33fa0cf184f37bc112d071463ab6d/relatorio_auto.md) |

## Como usar

```bash
pip install -r requirements.txt

# pipeline completo: baixa dados da carteira e de mercado, gera o relatório
python -m hlre.run 0xENDERECO

# ou etapa por etapa
python -m hlre.collect 0xENDERECO                    # fills, funding, ledger, ordens, snapshot, carteiras ligadas
python -m hlre.market BTC HYPE --intervals 1h 4h 1d  # candles + histórico de funding (Hyperliquid)
python -m hlre.binance BTCUSDT --start 2025-01       # 1h antigos (arquivo público Binance)
python -m hlre.report 0xENDERECO --coins BTC HYPE    # gera reports/<carteira>/relatorio_auto.md

# testes de regras no universo inteiro de perps (para validar um padrão de entrada)
python -m hlre.universe fetch                        # candles diários de todos os perps, inclusive deslistados
python -m hlre.universe study --start 2024-12-16 --funding-a POPCAT TRUMP --funding-b APT WIF
                                                     # gera reports/estudos/regras_short.md
```

Saída em `reports/<carteira>/`:

- `relatorio_auto.md`: números, tabelas e gráficos gerados automaticamente;
- `img/*.png`: os gráficos;
- `metrics.json`: os números principais, para comparar carteiras;
- `ANALISE.md`: a interpretação da estratégia, escrita à mão a partir do relatório;
- `analise_extra.py` (quando existe): recalcula os números do `ANALISE.md` que não estão no relatório automático.

**Rode o coletor periodicamente.** A API só serve os fills mais recentes (aqui, os de mai/2025 em diante) e as últimas 2.000 ordens. O coletor faz merge com o que já existe em `data/`, então o histórico local cresce a cada execução.

## Método

| pergunta | como é respondida |
|---|---|
| Quanto ganhou e quando? | `portfolio` (curvas de PnL e equity all-time, perp e total) |
| Em que ativos, com que tamanho? | posição exata a partir dos fills (`startPosition` + tamanho); **antes dos fills**, a posição diária vem do histórico de **funding**, que traz o tamanho da posição (`szi`) desde a abertura da conta |
| De onde vem o PnL? | marcação diária exata (posição carregada × movimento + fills marcados no fechamento), dividida em viés, timing do tamanho, trades intradiários, funding e taxas |
| Bot, market maker ou manual? | `historicalOrders` (tipo e TIF: `FrontendMarket` = interface web), `extraAgents` (API wallets), % maker/taker, tamanhos de lote, ritmo das sessões |
| O que dispara entradas e saídas? | contexto de mercado em cada ordem (retornos de 1h a 7d, posição no range de 7d, retorno futuro) vs. a base de todas as horas, com teste de Mann-Whitney por sessão |
| Como gere risco? | aumentos com a posição no prejuízo (preço médio), taxa de acerto das reduções, alavancagem (exposição / equity), ordens de gatilho, liquidações e ADL |
| É hedge de algo? | carteiras ligadas: conta de staking vinculada para desconto de taxa, contrapartes de transferências, airdrops idênticos |
| Dá para replicar com regras? | busca em grade de regras (tendência + fade do range) com treino e teste separados, mais um clone por regressão; compara a correlação com a posição real e o PnL |
| Dá para copiar? | PnL de espelhar a posição com 0 a 168h de atraso |
| Cada trade, por dentro | episódios de zerado a zerado em todas as moedas: contexto antes da 1ª ordem (retornos, distância da máxima de 30 dias, funding), preço médio vs. 1ª ordem, excursão contra, pior PnL aberto, quanto capturou |
| Como usa o dinheiro? | depósitos e saques contra o PnL dos dias anteriores e contra a variação da exposição (margem sob demanda) |
| É long/short de cestas? | posição diária em US$ por moeda (funding), livro long × livro short, beta ao BTC e alfa com bootstrap, comparação com cestas fixas e teste fora da amostra (`analise_extra.py` da `0x0748`) |
| O padrão vale fora das moedas que ele escolheu? | `hlre.universe`: estudo de eventos em todos os perps (inclusive deslistados) contra a base de "shortar qualquer alt", funding por faixas numa amostra aleatória, regras de média móvel em BTC/ETH desde 2020; intervalos por bootstrap de semanas |

## Estrutura

```
hlre/
  api.py        cliente da Info API (throttle, retry, paginação por tempo)
  collect.py    download e merge incremental dos dados da carteira + carteiras ligadas
  market.py     candles e histórico de funding da Hyperliquid; série horária costurada
  binance.py    klines horários do arquivo público da Binance (contexto antigo)
  analyze.py    execuções, episódios, posições, PnL exato e aproximado, contexto, cópia com atraso
  replicate.py  backtest diário, regras replicantes, clone comportamental
  universe.py   testes de regras no universo inteiro de perps (eventos, funding, médias móveis)
  charts.py     gráficos estáticos (sem eixo duplo; azul = long/ganho, vermelho = short/perda)
  report.py     relatório automático em markdown
  run.py        pipeline completo
data/           dados brutos (json.gz/csv.gz) de carteiras e de mercado
reports/        relatórios por carteira; reports/estudos/ guarda os testes de universo
```

## Limitações

- Quando os fills cobrem todo o histórico (carteiras com menos de ~10 mil fills), o PnL diário é exato e bate com o `portfolio`; o relatório avisa quando é o caso.
- O PnL por ativo **antes** do período com fills é aproximado (posição média diária × movimento do dia) e não captura day trade. No período com fills, a correlação diária com o valor exato foi 0,95.
- Fatias de **TWAP** não aparecem em `userFills` e o endpoint delas só guarda as 2.000 mais recentes. O `Wallet` junta as que existem e `position_gaps` aponta saltos de posição sem fill. Quando há saltos, o relatório avisa e o PnL "exato" deixa de ser exato.
- Intenção (aposta ou hedge) é inferência: a API não mostra CEXs nem outras chains.
- Nada aqui é recomendação de investimento.
