# Guia de Suporte - IntegradorOpsRamp-O (Integrador HPE)

[[_TOC_]]

## 1. O que e a aplicacao

O **Integrador HPE (IntegradorOpsRamp-O)** e o servico que **liga o OpsRamp ao TopDesk**.

Quando um alerta/incidente nasce ou muda no OpsRamp, o OpsRamp chama este integrador. O integrador:

1. recebe o ticket;
2. decide se precisa **criar**, **atualizar** ou **encerrar** o incidente no TopDesk;
3. guarda o **vinculo** entre o ID do OpsRamp e o ID/numero do TopDesk;
4. registra cada passo (sucesso ou falha) para o suporte consultar depois.

Em resumo: **OpsRamp avisa -> Integrador processa -> TopDesk fica sincronizado**.

## 2. Conceitos-chave (glossario rapido)

<table>
<thead>
<tr><th>Termo</th><th>O que e</th></tr>
</thead>
<tbody>
<tr><td><b>OpsRamp</b></td><td>Plataforma de monitoramento que gera os alertas/incidentes.</td></tr>
<tr><td><b>TopDesk</b></td><td>Sistema de chamados onde o incidente e aberto para a equipe atender.</td></tr>
<tr><td><code>incident_id</code></td><td>ID do ticket no OpsRamp. E a chave principal do integrador.</td></tr>
<tr><td><code>topdesk_id</code></td><td>ID interno (UUID) do incidente no TopDesk.</td></tr>
<tr><td><code>topdesk_number</code></td><td>Numero "humano" do incidente no TopDesk (ex.: I 2607 001).</td></tr>
<tr><td>Tabela <code>control</code></td><td>O vinculo OpsRamp x TopDesk. Se o <code>incident_id</code> ja esta aqui, o ticket <b>ja existe</b>.</td></tr>
<tr><td>Tabela <code>tickets</code></td><td>Ultima "foto" do ticket recebida do OpsRamp. Serve para comparar e detectar mudanca.</td></tr>
<tr><td>Catalogo (<code>category_catalog</code>)</td><td>De/para que decide categoria e subcategoria no TopDesk a partir do assunto/descricao.</td></tr>
<tr><td><b>Severidade</b></td><td>CRITICAL / WARNING / OK / INFO. Define impacto, urgencia e prioridade no TopDesk.</td></tr>
<tr><td><code>operation_events</code></td><td>Trilha de auditoria: cada passo do processamento (sucesso ou falha).</td></tr>
<tr><td>Passo (<code>step</code>)</td><td>Etapa do fluxo (ex.: <code>topdesk_create</code>, <code>opsramp_writeback</code>).</td></tr>
<tr><td>Resultado (<code>outcome</code>)</td><td><code>success</code> ou <code>failure</code>.</td></tr>
<tr><td><code>root_path</code></td><td>Prefixo opcional na URL publica (vem do <code>.env</code>). Pode mudar o caminho externo.</td></tr>
</tbody>
</table>

## 3. Como acessar

- A documentacao interativa (Swagger) fica em `/docs`.
- A especificacao OpenAPI fica em `/openapi.json`.
- Todas as rotas de API ficam sob o prefixo `/api`.
- Pode existir um **prefixo extra** (`root_path` no `.env`). Exemplo: se `root_path=/integrador`, a URL publica fica `/integrador/api/...`.

> **Aviso operacional:** esta API **nao exige autenticacao** (sem chave, sem token). Qualquer cliente que alcancar a URL pode chamar as rotas. O CORS tambem aceita qualquer origem.

## 4. Todas as rotas (referencia rapida)

### Integracao OpsRamp (`/api/opsramp`)

<table>
<thead>
<tr><th>Metodo</th><th>Caminho</th><th>O que faz</th><th>Observacao</th></tr>
</thead>
<tbody>
<tr><td>POST</td><td><code>/api/opsramp/ticket</code></td><td><b>Rota principal.</b> Recebe o ticket do OpsRamp e cria/atualiza/encerra no TopDesk.</td><td>Usada no dia a dia. Retorna 201 em sucesso e 500 em falha.</td></tr>
</tbody>
</table>

### TopDesk (`/api/topdesk`)

<table>
<thead>
<tr><th>Metodo</th><th>Caminho</th><th>O que faz</th><th>Observacao</th></tr>
</thead>
<tbody>
<tr><td>GET</td><td><code>/api/topdesk/close</code></td><td>Responde "Ticket closed successfully".</td><td><b>Sem efeito real. Nao usar.</b></td></tr>
<tr><td>POST</td><td><code>/api/topdesk/ticket</code></td><td>Responde "Ticket created successfully".</td><td><b>Sem efeito real. Nao usar.</b></td></tr>
</tbody>
</table>

### Monitoramento (`/api/monitoring`)

<table>
<thead>
<tr><th>Metodo</th><th>Caminho</th><th>O que faz</th><th>Observacao</th></tr>
</thead>
<tbody>
<tr><td>GET</td><td><code>/api/monitoring/summary</code></td><td>Resumo do dia (sucessos, falhas, tickets criados/atualizados/fechados).</td><td>Parametro <code>date=YYYY-MM-DD</code> (padrao: hoje).</td></tr>
<tr><td>GET</td><td><code>/api/monitoring/failures</code></td><td>Lista as falhas do dia, com links para OpsRamp e TopDesk.</td><td>Filtros: <code>date</code>, <code>step</code>, <code>limit</code>, <code>offset</code>, <code>verbose</code>.</td></tr>
<tr><td>GET</td><td><code>/api/monitoring/ticket/{opsramp_id}</code></td><td>Linha do tempo completa de um ticket.</td><td>Use o <code>incident_id</code> do OpsRamp.</td></tr>
</tbody>
</table>

### Saude e documentacao

<table>
<thead>
<tr><th>Metodo</th><th>Caminho</th><th>O que faz</th><th>Observacao</th></tr>
</thead>
<tbody>
<tr><td>GET</td><td><code>/health</code></td><td>Testa banco, TopDesk e OpsRamp.</td><td>200 = ok; 503 = degradado.</td></tr>
<tr><td>GET</td><td><code>/docs</code></td><td>Documentacao interativa (Swagger).</td><td>Util para explorar a API.</td></tr>
<tr><td>GET</td><td><code>/openapi.json</code></td><td>Especificacao OpenAPI.</td><td>Uso tecnico / ferramentas.</td></tr>
</tbody>
</table>

## 5. FOCO ESPECIAL: Monitorar e Corrigir

Esta e a parte mais usada no dia a dia do suporte.

> **Importante:** este projeto **nao tem** rota de reprocessamento tipo `/ingest/{raw_id}/retry-failed` (isso e do Coletor IURD). Aqui, a correcao pratica e **reenviar o mesmo ticket** via `POST /api/opsramp/ticket` (o OpsRamp faz isso ao atualizar o alerta). O integrador detecta que o ticket ja existe pela tabela `control` e segue para comparar/atualizar - **nao cria duplicata** se o vinculo estiver correto.

### Conceitos primeiro

- Cada processamento grava um ou mais registros em `operation_events` (um por passo).
- O monitoramento le **somente** essa tabela.
- A janela de um dia e **local**: das 00:00 ate 00:00 do dia seguinte (`date=YYYY-MM-DD`).

### A) Monitoramento - `GET /api/monitoring/summary`

E o "painel" do dia. Passo a passo:

1. Recebe `date` (ou usa o dia de hoje).
2. Conta os eventos daquele dia.
3. Devolve um JSON com:

<table>
<thead>
<tr><th>Campo</th><th>O que significa</th></tr>
</thead>
<tbody>
<tr><td><code>totals.events</code></td><td>Total de eventos (passos) registrados.</td></tr>
<tr><td><code>totals.success</code> / <code>totals.failure</code></td><td>Quantos deram certo / errado.</td></tr>
<tr><td><code>totals.success_rate</code></td><td>Taxa de sucesso (0 a 1).</td></tr>
<tr><td><code>tickets.created</code></td><td>Tickets distintos criados no TopDesk (<code>step=topdesk_create</code>).</td></tr>
<tr><td><code>tickets.updated</code></td><td>Tickets distintos atualizados (<code>step=topdesk_update</code>).</td></tr>
<tr><td><code>tickets.closed</code></td><td>Tickets distintos encerrados (<code>step=topdesk_close</code>).</td></tr>
<tr><td><code>tickets.no_change</code></td><td>Tickets que chegaram de novo, mas sem diferenca.</td></tr>
<tr><td><code>tickets.distinct_affected</code></td><td>Quantos <code>opsramp_id</code> distintos apareceram no dia.</td></tr>
<tr><td><code>failures.total</code></td><td>Total de eventos com falha.</td></tr>
<tr><td><code>failures.distinct_tickets</code></td><td>Quantos tickets distintos falharam.</td></tr>
<tr><td><code>failures.by_step</code></td><td>Falhas agrupadas por passo (onde quebrou).</td></tr>
<tr><td><code>by_step</code></td><td>Sucesso e falha por passo.</td></tr>
<tr><td><code>first_event_at</code> / <code>last_event_at</code></td><td>Primeiro e ultimo evento do dia.</td></tr>
</tbody>
</table>

**Como o suporte usa:**

1. Abrir o summary do dia.
2. Se `totals.failure` > 0, olhar `failures.by_step` para saber **onde** esta quebrando.
3. Ir para `/api/monitoring/failures` para ver os tickets afetados.

### B) Lista de falhas - `GET /api/monitoring/failures`

Lista as falhas do dia, ja com chaves de busca.

Parametros uteis:

<table>
<thead>
<tr><th>Parametro</th><th>Padrao</th><th>O que faz</th></tr>
</thead>
<tbody>
<tr><td><code>date</code></td><td>hoje</td><td>Dia a consultar (<code>YYYY-MM-DD</code>).</td></tr>
<tr><td><code>step</code></td><td>(todos)</td><td>Filtra por passo (ex.: <code>topdesk_create</code>).</td></tr>
<tr><td><code>limit</code></td><td>100</td><td>Quantas falhas retornar (1 a 1000).</td></tr>
<tr><td><code>offset</code></td><td>0</td><td>Paginacao.</td></tr>
<tr><td><code>verbose</code></td><td>false</td><td>Se <code>true</code>, mostra a mensagem de erro completa; se <code>false</code>, corta em 500 caracteres.</td></tr>
</tbody>
</table>

Cada item da lista traz, entre outros:

- `opsramp_id`, `opsramp_url`
- `topdesk_id`, `topdesk_number`, `topdesk_url`
- `subject`, `client_name`
- `step`, `outcome`, `error_type`, `error_message`
- `http_status`, `duration_ms`, `occurred_at`

**Como o suporte usa:**

1. Pegar o `opsramp_id` de uma falha.
2. Abrir o ticket no OpsRamp (`opsramp_url`) e, se existir, no TopDesk (`topdesk_url`).
3. Consultar a linha do tempo: `GET /api/monitoring/ticket/{opsramp_id}`.

### C) Linha do tempo - `GET /api/monitoring/ticket/{opsramp_id}`

Mostra **todos** os eventos daquele ticket, do mais antigo ao mais novo.

Serve para responder:

- O ticket chegou?
- Em qual passo falhou?
- Ja foi criado no TopDesk antes?
- O writeback do numero falhou?

### Tabela de passos (`step`) - o que cada falha significa

<table>
<thead>
<tr><th>Passo (<code>step</code>)</th><th>Operacao tipica</th><th>O que e</th><th>Se falhar, o que fazer</th></tr>
</thead>
<tbody>
<tr><td><code>catalog_resolve</code></td><td>create / update / close</td><td>Monta o payload TopDesk (categoria, prioridade, etc.).</td><td>Verificar assunto/descricao e o catalogo. Reenviar o ticket.</td></tr>
<tr><td><code>topdesk_create</code></td><td>create</td><td>Criar o incidente no TopDesk.</td><td>Ver <code>/health</code> (TopDesk). Ler <code>error_message</code>. Reenviar.</td></tr>
<tr><td><code>opsramp_writeback</code></td><td>create</td><td>Gravar o numero do TopDesk de volta no OpsRamp.</td><td><b>Atencao:</b> o incidente <b>ja foi criado</b> no TopDesk. Nao criar outro. Conferir o campo customizado no OpsRamp e o vinculo em <code>control</code>.</td></tr>
<tr><td><code>db_save</code></td><td>create / update</td><td>Salvar a "foto" do ticket na tabela <code>tickets</code>.</td><td>O TopDesk ja pode estar ok. Verificar banco e reenviar se necessario.</td></tr>
<tr><td><code>topdesk_update</code></td><td>update</td><td>Atualizar o incidente existente no TopDesk.</td><td>Ver se o <code>topdesk_id</code> existe. Reenviar.</td></tr>
<tr><td><code>topdesk_close</code></td><td>close</td><td>Encerrar o incidente no TopDesk (status Resolvido).</td><td>Ver TopDesk e o status no OpsRamp (<code>Closed</code> / <code>Resolved</code>). Reenviar.</td></tr>
<tr><td><code>no_change</code></td><td>skip</td><td>Ticket ja existia e nao havia diferenca.</td><td>Nao e erro. E sucesso esperado.</td></tr>
<tr><td><code>unhandled</code></td><td>create</td><td>Erro nao tratado na rota (caiu no <code>except</code> geral).</td><td>Ver logs e a mensagem. Corrigir causa e reenviar.</td></tr>
</tbody>
</table>

### Como corrigir (passo a passo)

1. Conferir `GET /health` - banco, TopDesk e OpsRamp precisam estar `ok`.
2. Abrir `GET /api/monitoring/summary` e `GET /api/monitoring/failures`.
3. Identificar o `step` da falha.
4. Abrir `GET /api/monitoring/ticket/{opsramp_id}` para o historico.
5. **Reenviar** o ticket pelo OpsRamp (`POST /api/opsramp/ticket` com o mesmo `incident_id`).
6. Se a falha for `opsramp_writeback`: **nao** tente "criar de novo". O TopDesk ja tem o incidente; o problema e so devolver o numero ao OpsRamp.

::: mermaid
graph TD
    M["Monitorar: GET /api/monitoring/summary"] --> S{"Ha falhas no dia?"}
    S -->|Nao| OK[Tudo certo]
    S -->|Sim| F["Listar falhas: GET /api/monitoring/failures"]
    F --> T["Linha do tempo: GET /api/monitoring/ticket/opsramp_id"]
    T --> H{"Passo da falha?"}
    H -->|opsramp_writeback| W["Incidente ja existe no TopDesk. Nao duplicar. Ajustar writeback / campo no OpsRamp."]
    H -->|outros| R["Reenviar ticket: POST /api/opsramp/ticket"]
    R --> Check["Conferir de novo: summary / ticket"]
    W --> Check
:::

## 6. Fluxo ponta a ponta (OpsRamp -> TopDesk)

Tudo comeca em `POST /api/opsramp/ticket`. O metodo principal e `TicketModel.add()`.

### Em linguagem simples

1. O OpsRamp envia o ticket (com `incident_id`, assunto, descricao, status, etc.).
2. O integrador pergunta: **esse `incident_id` ja esta na tabela `control`?**
3. **Nao** -> cria no TopDesk, grava o vinculo, tenta devolver o numero ao OpsRamp e salva a foto do ticket.
4. **Sim** -> compara a foto antiga (`tickets`) com a nova:
   - se ha diferencas -> atualiza o TopDesk e salva a nova foto;
   - se nao ha diferencas -> registra `no_change` (sucesso, sem acao).
5. Se o status no OpsRamp for `Closed` ou `Resolved` -> encerra o incidente no TopDesk.

::: mermaid
graph TD
    A["OpsRamp envia ticket POST /api/opsramp/ticket"] --> B{"Existe em control?"}
    B -->|Nao| C["Resolver catalogo categoria/prioridade"]
    C --> D["Criar incidente no TopDesk"]
    D --> E["Atualizar control topdesk_id e number"]
    E --> F["Writeback do numero no OpsRamp"]
    F --> G["Salvar foto em tickets"]
    B -->|Sim| H{"Tem topdesk_id?"}
    H -->|Nao| C
    H -->|Sim| I{"Ha diferencas na foto?"}
    I -->|Sim| J["Atualizar TopDesk e salvar foto"]
    I -->|Nao| K["Registrar no_change"]
    G --> L{"Status Closed ou Resolved?"}
    J --> L
    K --> L
    L -->|Sim| M["Encerrar no TopDesk"]
    L -->|Nao| N[Fim]
    M --> N
:::

### O que e gravado em cada caminho

<table>
<thead>
<tr><th>Caminho</th><th>Passos tipicos registrados</th></tr>
</thead>
<tbody>
<tr><td>Criacao</td><td><code>catalog_resolve</code> -&gt; <code>topdesk_create</code> -&gt; <code>opsramp_writeback</code> -&gt; <code>db_save</code> (+ <code>topdesk_close</code> se Closed/Resolved)</td></tr>
<tr><td>Atualizacao</td><td><code>catalog_resolve</code> -&gt; <code>topdesk_update</code> -&gt; <code>db_save</code> (+ <code>topdesk_close</code> se Closed/Resolved)</td></tr>
<tr><td>Sem mudanca</td><td><code>no_change</code> (+ <code>topdesk_close</code> se Closed/Resolved)</td></tr>
</tbody>
</table>

## 7. Como a categoria, a subcategoria e a prioridade sao decididas

Antes de criar/atualizar no TopDesk, o integrador monta o payload. A logica principal:

### Categoria e subcategoria

1. Junta `subject` + `description` do ticket.
2. Procura no `category_catalog`:
   - primeiro por `metric_name` (mais especifico);
   - depois por `monitor_name`.
3. Se achar, usa `category_id` e `subcategory_id` da linha.
4. Se o texto falar de **gateway** (ou "SSL Certificate is missing") e nao houver match, aplica o atalho **HPE SUZANO - GATEWAY / SERVICE.STATUS**.
5. Se nada bater, usa categoria/subcategoria **padrao** (infraestrutura generica).

### Severidade e prioridade

1. Tenta extrair a severidade da descricao (usando o template `alert_body` do catalogo, ou o campo `Severity:`).
2. Se a categoria for **HPE SUZANO - GATEWAY**, forca severidade **CRITICAL**.
3. Converte a severidade:

<table>
<thead>
<tr><th>Severidade</th><th>Impacto</th><th>Urgencia</th><th>Prioridade</th></tr>
</thead>
<tbody>
<tr><td>CRITICAL</td><td>GRANDE</td><td>ALTO</td><td>PRIORIDADE 1</td></tr>
<tr><td>WARNING</td><td>MEDIO</td><td>MEDIO</td><td>PRIORIDADE 2</td></tr>
<tr><td>OK</td><td>PEQUENO</td><td>BAIXO</td><td>PRIORIDADE 3</td></tr>
<tr><td>INFO</td><td>PEQUENO</td><td>BAIXO</td><td>PRIORIDADE 4</td></tr>
<tr><td>(nao encontrada)</td><td>PEQUENO</td><td>BAIXO</td><td>PRIORIDADE 4</td></tr>
</tbody>
</table>

::: mermaid
graph TD
    T["Ticket OpsRamp subject + description"] --> Cat{"Match no category_catalog?"}
    Cat -->|metric_name ou monitor_name| Use["Usa category_id e subcategory_id"]
    Cat -->|Nao| Gw{"Texto tem gateway ou SSL Certificate is missing?"}
    Gw -->|Sim| Gate["Forca GATEWAY / SERVICE.STATUS"]
    Gw -->|Nao| Def["Categoria/subcategoria padrao"]
    Use --> Sev["Extrair severidade"]
    Gate --> SevForce["Severidade = CRITICAL"]
    Def --> Sev
    Sev --> Map["Mapear para impacto urgencia e prioridade"]
    SevForce --> Map
    Map --> TDPayload["Payload TopDesk"]
:::

## 8. Banco de dados (visao simples)

O integrador usa quatro tabelas principais:

<table>
<thead>
<tr><th>Tabela</th><th>Para que serve</th></tr>
</thead>
<tbody>
<tr><td><code>control</code></td><td>Vinculo OpsRamp x TopDesk (<code>opsramp_id</code>, <code>topdesk_id</code>, <code>topdesk_number</code>, <code>status</code>).</td></tr>
<tr><td><code>tickets</code></td><td>Ultima foto completa do ticket (para detectar mudancas).</td></tr>
<tr><td><code>category_catalog</code></td><td>De/para de monitores/metricas para categoria/subcategoria do TopDesk. Carregado de <code>app/data/catalog.csv</code> na subida se a tabela estiver vazia.</td></tr>
<tr><td><code>operation_events</code></td><td>Trilha de auditoria (alimenta <code>/api/monitoring/*</code>).</td></tr>
</tbody>
</table>

### Modelo mental em uma linha

`control` diz **se o ticket ja existe**; `tickets` diz **o que mudou**; `category_catalog` diz **como classificar**; `operation_events` diz **o que aconteceu**.

::: mermaid
graph LR
    OR[OpsRamp incident_id] --> CTRL[control]
    CTRL --> TD[TopDesk topdesk_id / number]
    OR --> TKT[tickets foto]
    OR --> EVT[operation_events]
    CAT[category_catalog] --> TD
:::

## 9. Verificacao de saude (`GET /health`)

O endpoint testa **tres** dependencias em paralelo (timeout de 5 segundos cada):

<table>
<thead>
<tr><th>Servico</th><th>O que testa</th><th>Ok quando</th></tr>
</thead>
<tbody>
<tr><td><code>database</code></td><td>Conexao com o banco (<code>SELECT 1</code>).</td><td>Resposta sem erro.</td></tr>
<tr><td><code>topdesk</code></td><td>Chamada autenticada a lista de call types.</td><td>HTTP 200.</td></tr>
<tr><td><code>opsramp</code></td><td>Pedido de token OAuth (client credentials).</td><td>HTTP 200.</td></tr>
</tbody>
</table>

Resposta:

- **200** + `"status": "ok"` - tudo bem.
- **503** + `"status": "degraded"` - um ou mais servicos `down` (veja `services.*.detail`).
- **500** - erro inesperado no proprio health check.

**O que o suporte faz:**

1. Se `database` down -> checar conexao/credenciais/rede do banco.
2. Se `topdesk` down -> checar URL, usuario/senha e disponibilidade do TopDesk.
3. Se `opsramp` down -> checar URL, client id/secret e disponibilidade do OpsRamp.
4. Enquanto estiver degradado, novos tickets podem falhar nos passos correspondentes.

## 10. FAQ (perguntas frequentes do suporte)

### O alerta virou incidente no TopDesk?

1. Pegue o `incident_id` no OpsRamp.
2. Chame `GET /api/monitoring/ticket/{opsramp_id}`.
3. Procure um evento `topdesk_create` com `outcome=success`.
4. Use `topdesk_number` / `topdesk_url` da resposta (ou da tabela `control`).

Se nao houver evento, o ticket pode nao ter chegado ao integrador (checar webhook/configuracao no OpsRamp e logs).

### O incidente foi criado, mas o numero nao aparece no OpsRamp

Isso costuma ser falha em `opsramp_writeback`.

- O TopDesk **ja tem** o incidente.
- O writeback do numero (campo customizado) falhou.
- **Nao** force uma nova criacao.
- Reenvie o ticket (o fluxo de update/writeback pode tentar de novo) e confira o campo no OpsRamp.

### O incidente caiu na categoria errada

- O de/para vem do `category_catalog` (arquivo `app/data/catalog.csv`).
- Se o assunto/descricao nao bater com `metric_name` / `monitor_name`, cai no padrao (ou no atalho de gateway).
- Acione o time tecnico para ajustar o catalogo e regenerar com `scripts/build_catalog.py` se necessario.

### A prioridade saiu como PRIORIDADE 4

- Severidade nao encontrada (ou veio como INFO).
- Padrao do sistema: PEQUENO / BAIXO / PRIORIDADE 4.
- Confira se a descricao traz `Severity:` (ou o placeholder `${severity}` no template do catalogo).

### O mesmo alerta gerou incidente duplicado?

Em condicao normal, **nao**: a tabela `control` impede nova criacao se o `opsramp_id` ja existe.

Duplicata pode acontecer se:

- o primeiro envio criou no TopDesk, mas **nao** gravou o vinculo em `control` (falha entre create e update do control);
- alguem criou manualmente no TopDesk fora do integrador.

Use `GET /api/monitoring/ticket/{opsramp_id}` e a tabela `control` para investigar.

### O incidente nao encerrou no TopDesk

O encerramento so roda se o status no OpsRamp for `Closed` ou `Resolved`.

1. Confirme o status no OpsRamp.
2. Veja se ha `topdesk_close` na linha do tempo.
3. Se falhou, leia `error_message` e reenvie apos o TopDesk estar saudavel.

### Vi 500 ao enviar o ticket - e para reenviar?

Sim, em geral **e seguro reenviar** o mesmo `incident_id`:

- se ainda nao existir em `control`, tenta criar;
- se ja existir, compara e atualiza (ou registra `no_change`).

Excecao: se a falha for so `opsramp_writeback`, o TopDesk ja tem o chamado - trate como writeback, nao como "criar de novo".

### As rotas `/api/topdesk/close` e `/api/topdesk/ticket` nao funcionam

Correto. Elas **nao fazem nada de verdade** (so devolvem mensagem de sucesso). A integracao real passa por `POST /api/opsramp/ticket`.

### Onde estao os logs?

- O caminho do arquivo vem de `log_file` no `.env` (em geral sob a pasta `logs/`).
- Rotacao a cada 10 MB; guarda ate 10 arquivos; arquivos antigos sao zipados.
- Em modo `debug=true`, tambem imprime no console.

### O `/health` esta degradado

1. Leia `services.database`, `services.topdesk` e `services.opsramp`.
2. Corrija o(s) item(ns) `down`.
3. So depois cobre o reenvio dos tickets que falharam nesse periodo.

### Nao existe rota de "retry-failed" aqui?

Correto. Diferente do Coletor IURD, este integrador **nao** tem `/ingest/failed-rows/summary` nem `/ingest/{raw_id}/retry-failed`.

Aqui o fluxo de suporte e:

1. `summary` / `failures` / `ticket/{opsramp_id}` para diagnosticar;
2. reenvio do ticket pelo OpsRamp para corrigir.
