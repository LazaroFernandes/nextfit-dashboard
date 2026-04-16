# NextFit → Google Sheets

Sincroniza os dados da API pública do NextFit para uma planilha do Google Sheets, criando uma aba por recurso (Clientes, Leads, Contratos, Vendas, Financeiro, Agenda, etc.).

- API: `https://integracao.nextfit.com.br`
- Autenticação: header `X-Api-Key`
- Documentação original: [docs/nextfit-openapi.json](docs/nextfit-openapi.json)

---

## 1. Instalar o Python (Windows)

1. Acesse **https://www.python.org/downloads/** e baixe o instalador mais recente (3.11 ou superior).
2. Ao executar o instalador, **marque a caixa "Add python.exe to PATH"** antes de clicar em *Install Now*. Isso é essencial.
3. Abra um **novo** terminal (PowerShell ou CMD) e confirme:
   ```bash
   python --version
   pip --version
   ```

## 2. Instalar as dependências

Na pasta do projeto, rode:

```bash
cd "c:\Users\lazar\Desktop\Projetos claude\Nextfit"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> O `.venv` é um ambiente isolado — todas as libs ficam só dentro do projeto, sem bagunçar o Python do sistema. Sempre que for rodar o script num terminal novo, rode `.venv\Scripts\activate` antes.

## 3. Criar a planilha no Google Sheets

1. Acesse **https://sheets.google.com** e crie uma planilha nova (pode deixar em branco — o script cria as abas).
2. Pegue o **ID da planilha** da URL: `https://docs.google.com/spreadsheets/d/`**`ESTE_PEDACO_AQUI`**`/edit`
3. Abra o arquivo `.env` e cole o ID em `GOOGLE_SHEET_ID=...`

## 4. Criar credenciais do Google Cloud (service account)

Para o script conseguir escrever na planilha, precisamos de uma "conta de serviço" do Google Cloud. Passo a passo:

1. Acesse **https://console.cloud.google.com/**
2. **Crie um projeto novo** (no seletor de projetos no topo, "Novo projeto"). Pode chamar de `nextfit-sync`.
3. Com o projeto selecionado, abra o menu lateral → **APIs e serviços** → **Biblioteca** e habilite **duas** APIs:
   - **Google Sheets API** (buscar, clicar, **Ativar**)
   - **Google Drive API** (buscar, clicar, **Ativar**)
4. Vá em **APIs e serviços** → **Credenciais** → **+ Criar credenciais** → **Conta de serviço**.
   - Nome: `nextfit-sync` (qualquer nome serve)
   - Pode pular os passos opcionais de permissão — clique em **Concluído**.
5. Na lista de contas de serviço, clique na que você acabou de criar → aba **Chaves** → **Adicionar chave** → **Criar nova chave** → tipo **JSON** → **Criar**.
6. Um arquivo `.json` será baixado. **Renomeie para `service-account.json`** e mova para a pasta [credentials/](credentials/) do projeto.
7. Abra o `.json`, copie o campo **`client_email`** (algo tipo `nextfit-sync@nextfit-sync.iam.gserviceaccount.com`).
8. Volte na planilha que você criou no passo 3, clique em **Compartilhar**, cole esse email e dê permissão de **Editor**. **Esse passo é obrigatório** — sem isso o script recebe erro de permissão.

## 5. Verificar o .env

Abra o arquivo `.env` na raiz e confira que estão preenchidos:

```
NEXTFIT_API_KEY=...         # já preenchido
NEXTFIT_BASE_URL=https://integracao.nextfit.com.br
NEXTFIT_API_VERSION=1
GOOGLE_SHEET_ID=...         # ID da planilha (passo 3)
GOOGLE_CREDENTIALS_FILE=credentials/service-account.json
```

## 6. Rodar a sincronização

```bash
python src\sync.py
```

Você verá a saída com cada recurso sendo sincronizado:

```
[info] conectando no NextFit em https://integracao.nextfit.com.br
[info] abrindo planilha 1AbC...
[sync] clientes -> aba 'Clientes' ...
  [ok] 342 registros lidos, 342 escritos (4.1s)
[sync] leads -> aba 'Leads' ...
...
```

### Sincronizar só alguns recursos

```bash
python src\sync.py clientes contratos_cliente
```

Nomes válidos: `clientes`, `leads`, `usuarios`, `contratos_base`, `contratos_cliente`, `vendas`, `contas_receber`, `movimentos_financeiros`, `oportunidades`, `agenda`.

---

## Estrutura do projeto

```
Nextfit/
├── .env                        # segredos (gitignored)
├── .env.example                # template
├── .gitignore
├── README.md
├── requirements.txt
├── credentials/
│   ├── README.md
│   └── service-account.json    # você adiciona (gitignored)
├── docs/
│   └── nextfit-openapi.json    # swagger baixado
└── src/
    ├── nextfit_client.py       # cliente HTTP da API NextFit
    ├── sheets_client.py        # escrita em Google Sheets
    └── sync.py                 # orquestrador (entrypoint)
```

## Problemas comuns

- **`403 The caller does not have permission`** ao escrever — você esqueceu de compartilhar a planilha com o `client_email` da service account (passo 4.8).
- **`401 Unauthorized`** da API NextFit — o token no `.env` está inválido ou expirou. Gere outro no painel NextFit.
- **`ModuleNotFoundError: gspread`** — você não ativou o `.venv` antes de rodar. Rode `.venv\Scripts\activate`.
- **API devolve poucos registros** — o `page_size` padrão é 500; a paginação é automática (`temProximaPagina`), então isso não deveria acontecer. Se acontecer, aumente `page_size` em [src/nextfit_client.py](src/nextfit_client.py).

## Automatizar depois

Quando a sincronização manual estiver funcionando, dá pra agendar pelo **Agendador de Tarefas do Windows** rodando `python src\sync.py` em intervalo fixo (diário, de hora em hora, etc.). Me fala quando chegar nessa etapa que eu monto.
