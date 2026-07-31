# Progresso

- [x] Estrutura Next.js App Router, TypeScript e Tailwind
- [x] PostgreSQL, modelos Prisma e migration inicial
- [x] Tela de TV 16:9 e fallback institucional
- [x] Playlist de imagens e vídeos sem interrupção pelas boas-vindas
- [x] Painel fixo e alternância de aniversariantes
- [x] Webhook, fila FIFO, expiração e proteção contra duplicidade
- [x] Server-Sent Events, reconexão, heartbeat e comandos remotos
- [x] Painel administrativo, upload, reordenação e preview
- [x] Login, sessão segura, validação, rate limit e auditoria
- [x] Cache local e fallback offline
- [x] Adaptador de sincronização dos aniversariantes NextFit
- [x] Seed demonstrativo, Docker, Coolify, health check e testes

## Validação final

- [x] `npm test` — 6 testes aprovados
- [x] `npm run lint` — sem erros
- [x] `npm run build` — build de produção aprovado
- [ ] Teste visual em 1920×1080 e 1366×768 com PostgreSQL ativo

O teste visual conectado ao banco ficou pendente no ambiente local porque o Docker Desktop está instalado, mas seu serviço não está disponível nesta sessão. O compose foi validado com `docker compose config`.
