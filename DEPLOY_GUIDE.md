# Guia de Operação e Deploy em Nuvem (100% Gratuito)

Este documento contém o passo a passo para colocar o **Lufthansa Dispute Ops & Bot** em operação contínua 24/7 na nuvem sem custos, com domínio público HTTPS e agendador automático ativo.

---

## Opção 1: Deploy no Render (Recomendado - 1 Clique via GitHub)

O **Render** oferece hospedagem gratuita com suporte a Docker e subdomínio seguro automático (ex: `https://lufthansa-dispute-bot.onrender.com`).

### Passo 1: Subir o projeto para o seu GitHub
Se o repositório ainda não estiver no seu GitHub:
1. Crie um repositório privado ou público no [GitHub](https://github.com/new).
2. No seu terminal, faça o commit e push:
```bash
git add .
git commit -m "Lufthansa Dispute Bot with Cloud Docker Setup"
git remote add origin https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git
git push -u origin main
```

### Passo 2: Conectar no Render
1. Acesse **[render.com](https://render.com/)** e faça login com seu GitHub.
2. Clique no botão **"New +"** no canto superior direito e selecione **"Web Service"**.
3. Selecione o seu repositório do GitHub recém-criado.
4. O Render detectará automaticamente o arquivo `render.yaml` e o `Dockerfile`.
5. Preencha:
   - **Name**: `lufthansa-dispute-bot` (ou nome de sua preferência)
   - **Instance Type**: **Free** ($0/month)
6. Clique em **"Deploy Web Service"**.

Pronto! Em cerca de 2 a 3 minutos, sua aplicação estará no ar com URL pública gratuita HTTPS (ex: `https://lufthansa-dispute-bot.onrender.com`) e o agendador diário estará operando sozinho em segundo plano.

---

## Opção 2: Deploy no Fly.io (Região São Paulo - GRU)

O **Fly.io** tem datacenter em São Paulo (`gru`), oferecendo latência ultra-baixa e 1GB de RAM gratuito para a VM.

1. Instale o CLI do Fly.io no Windows (PowerShell):
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```
2. Faça login:
```powershell
fly auth login
```
3. Na pasta do projeto, execute:
```powershell
fly launch --now
```
4. O Fly criará sua aplicação com domínio gratuito (ex: `https://lufthansa-dispute-bot.fly.dev`).

---

## Como Funciona o Agendador na Nuvem

* O container roda o **FastAPI** junto com o **DailyScheduler** embutido via `lifespan`.
* Não é necessário criar um segundo serviço pago de worker ou cron externo.
* O agendador lê o horário configurado no banco SQLite (padrão `09:00`) e roda a submissão todos os dias automaticamente.
* Você pode acessar o portal pelo celular a qualquer momento para ver o status, alterar o horário ou disparar manualmente.
