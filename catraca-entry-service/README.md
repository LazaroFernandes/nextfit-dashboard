# Catraca Entry Service

Microsserviço independente que consulta as presenças do NextFit, aceita somente eventos do tipo `Acesso`, deduplica as passagens e oferece uma API para outras aplicações.

## Contrato da API

- `GET /health`: estado da integração, sem dados sensíveis.
- `GET /v1/entries?after=0&limit=100`: entradas em ordem crescente.
- `GET /v1/entries/latest`: última entrada detectada.

Os endpoints `/v1/*` exigem o header `X-Api-Key`.

Resposta de listagem:

```json
{
  "items": [
    {
      "id": 42,
      "student_id": "12345",
      "student_name": "Nome do aluno",
      "entered_at": "2026-08-01T10:30:00-03:00",
      "received_at": "2026-08-01T10:30:08-03:00"
    }
  ],
  "next_cursor": 42,
  "has_more": false
}
```

A aplicação consumidora salva `next_cursor` e o envia como `after` na próxima consulta. Assim, cada evento é processado apenas uma vez pelo consumidor.

## Subir com Docker

```bash
cp .env.example .env
# preencha as chaves no .env
docker compose up -d --build
curl http://localhost:8010/health
```

Por segurança, o Compose publica a porta apenas em `127.0.0.1`. Use o proxy reverso da VPS para HTTPS e limite o acesso ao domínio ou à rede que consumirá a API.

Exemplo de consumo:

```bash
curl "https://catraca.seudominio.com/v1/entries?after=0" \
  -H "X-Api-Key: SUA_CHAVE"
```

O banco SQLite e os tokens renovados ficam no volume Docker nomeado `catraca-entry-data`. Se o access token expirar, o serviço tenta renová-lo e persiste a rotação do refresh token nesse volume.

No Coolify, use exclusivamente **Volume Mount** com destino `/app/data`. Deixe `Source Path`/`Host Path` vazio; nunca monte `/` ou outro diretório da VPS. O container inicia diretamente como o usuário não-root `appuser` e não executa `chown` em tempo de inicialização.
