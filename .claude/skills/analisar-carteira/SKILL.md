---
name: analisar-carteira
description: Engenharia reversa de uma carteira da Hyperliquid neste repositório. Use quando o usuário pedir para "analisar", "investigar" ou fazer engenharia reversa de um endereço 0x… (ou colar só o endereço). Roda o pipeline hlre, interpreta o relatório automático, escreve o ANALISE.md, atualiza a tabela do README e faz commit/push.
---

# Analisar uma carteira da Hyperliquid

Entrada: um endereço `0x…` (40 hex). Normalize para minúsculas. Tudo é escrito em **português**, no estilo dos `ANALISE.md` existentes.

## 1. Preparar

```bash
cd <raiz do repo>
git checkout -B <branch designado> -q   # se houver branch designado na sessão
pip install -q -r requirements.txt
```

Se `reports/<endereço>/ANALISE.md` já existir, é uma **atualização**: rode o pipeline de novo (o coletor faz merge) e reescreva os números, sem começar do zero.

## 2. Rodar o pipeline

```bash
python -m hlre.run 0xENDERECO > <scratchpad>/run.log 2>&1; echo $?; tail -20 <scratchpad>/run.log
```

- Use `timeout` de 600000 ms no Bash. Carteiras com muitos fills podem passar de 10 min: nesse caso rode com `run_in_background` e espere a notificação.
- Saída: `reports/<endereço>/relatorio_auto.md`, `metrics.json`, `img/`; dados brutos em `data/<endereço>/`.
- Se falhar, leia o traceback no log, corrija em `hlre/` só se for bug real e rode de novo.

## 3. Ler o relatório e os dados brutos

```bash
grep -v '^!\[' reports/<endereço>/relatorio_auto.md
```

Confira também, em `data/<endereço>/`:
- `ledger.json.gz`: depósitos, saques, `send` para subcontas, `spotTransfer` (airdrops), ponte para a HyperEVM (`0x2000…`).
- `snapshot.json`: posições abertas, **saldo spot** (USDC no spot serve de margem: equity de perp pequeno com muito USDC spot faz a "alavancagem" do relatório parecer alta, mas não é), `subAccounts`, `extraAgents`, `delegatorSummary` (staking), `referral`.

Pontos a verificar no relatório:
- Os fills cobrem todo o histórico? (PnL exato vs. aproximado)
- Bot, market maker ou manual? (tipos de ordem, % maker, execuções por dia, `FrontendMarket`, `cloid`, agentes)
- De onde vem o PnL: por ativo e por viés × timing × intradiário × funding × taxas.
- Gatilhos de entrada e saída (tabelas por sessão, olhar os p-valores), preço médio, stops, liquidações.
- Fluxo de capital e carteiras ligadas (hedge? subconta?).
- Copiabilidade: o resultado com 30 min e 4h de atraso, limite vs. mercado, espelho de posição; regra/clone fora da amostra (se a regra testada não combina com o estilo da carteira, diga isso).

Se precisar de um número que o relatório não traz, calcule com um script em Python e, se ele entrar no texto, salve como `reports/<endereço>/analise_extra.py`.

## 4. Escrever `reports/<endereço>/ANALISE.md`

Siga o formato de `reports/0x95da8596c44dd09f4b8becce87ad3b7894fb2328/ANALISE.md`:

```
# Engenharia reversa: carteira `0xABCD…WXYZ`

`<endereço completo>` · [CoinGlass](https://www.coinglass.com/hyperliquid/<endereço>) · dados até <data>

Fonte: … (desde quando há fills; PnL exato ou estimado). Tabelas e gráficos: [`relatorio_auto.md`](relatorio_auto.md).

---

## Resumo
- **Quem é:** …
- **Resultado:** …
- **De onde vem:** …
- **Estilo:** …
- **Hoje:** posições abertas e risco
- **Dá para copiar?** …

---

## 1. Como opera
## 2. De onde vem o lucro
## 3. Gestão de risco e de capital
## 4. Dá para copiar?

**Veredito:** …
```

Regras de texto: números em formato brasileiro (US$ 1,26M, +US$ 355k, 0,8x), datas como 5/jul/2026, frases curtas, todo número tirado do relatório ou dos dados (nada inventado), e diga quando algo é inferência.

## 5. Atualizar o README

Na tabela "Carteiras analisadas" do `README.md`, adicione uma linha no fim (ou substitua a existente, se for atualização):

```
| `<endereço>` | **<rótulo em negrito>**: veredito curto de 3 a 6 frases com os números principais. | [ANALISE.md](reports/<endereço>/ANALISE.md) · [relatório automático](reports/<endereço>/relatorio_auto.md) |
```

## 6. Commit e push

```bash
git add -A
git commit -m "Análise da carteira 0xABCD…WXYZ" (+ linhas de atribuição da sessão)
git push -u origin <branch>
```

Não abra PR, a não ser que o usuário peça.

## 7. Responder ao usuário

Resumo em português: quem é a carteira, o resultado e de onde ele vem, o risco, se dá para copiar, e os caminhos do `ANALISE.md` e do `relatorio_auto.md`.
