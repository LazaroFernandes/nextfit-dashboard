# Mídia Indoor · CT Ítalo Vieira

Aplicação Next.js para a programação das TVs do CT: playlist de patrocinadores, aniversariantes permanentes e boas-vindas em tempo real disparadas pela catraca.

## Recursos entregues

- `/tv?token=...`: tela pública protegida por token, responsiva em 1920×1080 e 1366×768.
- `/admin`: dashboard, upload/reordenação de mídia, aniversários, simulação e controle remoto.
- `/api/entry`: webhook genérico protegido por `X-Api-Key`, Zod, rate limit, fila FIFO e deduplicação.
- `/api/tv/events`: Server-Sent Events com reconexão automática e heartbeat.
- Cache local da última programação; fallback institucional quando não há conexão ou mídia.
- PostgreSQL + Prisma, login com bcrypt e cookie JWT `httpOnly`, auditoria administrativa.
- Sincronização manual e automática dos aniversariantes elegíveis com clientes/contratos do NextFit.

## Rodar localmente

1. Copie `.env.example` para `.env` e troque todos os segredos.
2. Inicie apenas o PostgreSQL: `docker compose up -d db`.
3. Instale: `npm install`.
4. Crie as tabelas: `npm run db:migrate`.
5. Carregue a demonstração: `npm run db:seed`.
6. Rode: `npm run dev` e abra `http://localhost:4000/admin`.

A URL da TV é `http://localhost:4000/tv?token=VALOR_DE_TV_DISPLAY_TOKEN`. Use F11 ou modo quiosque do navegador.

## Webhook da catraca

```bash
curl -X POST http://localhost:4000/api/entry \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: VALOR_DE_ENTRY_API_KEY" \
  -d '{"studentId":"12345","name":"Lázaro Fernandes","enteredAt":"2026-07-31T10:30:00-03:00","unitId":"ct-italo-vieira"}'
```

Respostas: `201 queued`, `202 duplicate`, `401` para chave inválida, `429` para rate limit e `503` para fila cheia.

## Primeiro administrador

O seed usa `INITIAL_ADMIN_EMAIL` e `INITIAL_ADMIN_PASSWORD`. Para criar outro:

```bash
npm run admin:create -- gestor@ct.com "Gestor" "uma-senha-segura"
```

## Coolify

1. Crie um recurso PostgreSQL e copie sua URL interna para `DATABASE_URL`.
2. Crie a aplicação apontando para o diretório `midia-indoor` e selecione build por Dockerfile.
3. Cadastre as variáveis do `.env.example`; gere `AUTH_SECRET`, `ENTRY_API_KEY` e `TV_DISPLAY_TOKEN` aleatórios.
4. Monte um volume persistente em `/app/public/uploads`.
5. Configure o health check em `/api/health` e exponha a porta `4000`.
6. Crie uma tarefa agendada diária (`5 8 * * *`) com o comando `curl -fsS -X POST http://localhost:4000/api/cron/birthdays -H "X-Api-Key: $ENTRY_API_KEY"`.

O container executa `prisma migrate deploy` antes de iniciar. Para múltiplas réplicas, substitua o barramento SSE em memória por Redis Pub/Sub; uma única réplica é a configuração indicada para a instalação inicial.

## Operação 24/7

- Vídeos são `muted` e `playsInline`, evitando bloqueio de autoplay.
- A TV tenta reconectar ao SSE a cada 3 segundos.
- A programação permanece no armazenamento local durante falhas de rede.
- Uploads precisam de volume persistente no servidor.
- A mídia aceita JPG/PNG/WEBP/MP4/WEBM; limite controlado por `UPLOAD_MAX_MB`.

## Verificação

```bash
npm test
npm run lint
npm run build
```
