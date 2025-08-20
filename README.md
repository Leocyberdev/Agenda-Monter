# AgendaMonter - Sistema de Agendamento de Reuniões

Sistema web para agendamento de reuniões desenvolvido em Flask com suporte a PostgreSQL para produção.

## Funcionalidades

- Sistema de autenticação de usuários
- Agendamento de reuniões em salas
- Notificações por email
- Painel administrativo
- Interface responsiva

## Tecnologias Utilizadas

- **Backend**: Flask, SQLAlchemy, Flask-Login, Flask-Mail
- **Banco de Dados**: SQLite (desenvolvimento) / PostgreSQL (produção)
- **Frontend**: HTML, CSS, JavaScript
- **Servidor**: Gunicorn

## Configuração Local

1. Clone o repositório:
```bash
git clone https://github.com/Leocyberdev/agendamonter.git
cd agendamonter
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Execute a aplicação:
```bash
cd src
python main.py
```

A aplicação estará disponível em `http://localhost:5000`

## Implantação no Render

### 1. Criar Banco de Dados PostgreSQL

1. Acesse [dashboard.render.com](https://dashboard.render.com)
2. Clique em **"+ New"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `agendamonter-db`
   - **Database**: `agendamonter`
   - **User**: `agendamonter_user`
   - **Region**: Escolha a região mais próxima
   - **PostgreSQL Version**: 16 (recomendado)
   - **Instance Type**: Free (para testes) ou Starter (para produção)

4. Clique em **"Create Database"**
5. Anote a **Internal Database URL** que será gerada

### 2. Criar Web Service

1. No dashboard do Render, clique em **"+ New"** → **"Web Service"**
2. Conecte seu repositório GitHub
3. Configure:
   - **Name**: `agendamonter`
   - **Region**: Mesma região do banco de dados
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd src && gunicorn main:app --bind 0.0.0.0:$PORT`

### 3. Configurar Variáveis de Ambiente

No painel do Web Service, vá para **"Environment"** e adicione:

```
DATABASE_URL=<sua_internal_database_url_aqui>
FLASK_ENV=production
SECRET_KEY=<gere_uma_chave_secreta_segura>
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<seu_email>
MAIL_PASSWORD=<sua_senha_de_app>
MAIL_DEFAULT_SENDER=<seu_email>
```

**Importante**: 
- Use a **Internal Database URL** do PostgreSQL criado
- Para o email, use uma senha de aplicativo do Gmail, não sua senha normal
- Gere uma SECRET_KEY segura (pode usar `python -c "import secrets; print(secrets.token_hex(32))"`)

### 4. Deploy

1. Clique em **"Create Web Service"**
2. O Render fará o deploy automaticamente
3. Aguarde o processo de build e deploy
4. Acesse sua aplicação pela URL fornecida pelo Render



## Estrutura do Projeto

```
agendamonter/
├── src/
│   ├── models/          # Modelos do banco de dados
│   ├── routes/          # Rotas da aplicação
│   ├── static/          # Arquivos estáticos (CSS, JS, imagens)
│   ├── templates/       # Templates HTML
│   ├── utils/           # Utilitários
│   ├── config.py        # Configurações da aplicação
│   └── main.py          # Arquivo principal
├── requirements.txt     # Dependências Python
├── Procfile            # Configuração para deploy
└── README.md           # Este arquivo
```

## Solução de Problemas

### Erro de Conexão com Banco de Dados
- Verifique se a variável `DATABASE_URL` está configurada corretamente
- Certifique-se de usar a **Internal Database URL** do Render
- Verifique se o banco de dados está na mesma região do web service

### Erro de Email
- Verifique as configurações de email nas variáveis de ambiente
- Use uma senha de aplicativo do Gmail, não a senha normal
- Certifique-se de que a autenticação em duas etapas está habilitada no Gmail

### Aplicação não Inicia
- Verifique os logs no dashboard do Render
- Certifique-se de que todas as dependências estão no `requirements.txt`
- Verifique se o `Procfile` está configurado corretamente

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## Suporte

Para suporte, entre em contato através do email: agendamontereletrica@gmail.com

