# Bistaka Delivery - Sistema de Gerenciamento para Lanchonetes

Bistaka Delivery é um sistema web completo para gerenciamento de lanchonetes e pequenos restaurantes, desenvolvido em Python com o microframework Flask. A aplicação oferece uma vitrine online para os clientes e um painel administrativo robusto para o gerenciamento de cardápio, pedidos, clientes e finanças.

## Funcionalidades

### Para Clientes
- **Vitrine Online:** Uma página inicial onde os clientes podem visualizar o cardápio completo, com descrições, fotos e preços.
- **Status da Loja:** Informa automaticamente se a loja está aberta ou fechada com base nos horários configurados.
- **Envio de Pedidos:** Os clientes podem montar seu pedido e enviá-lo diretamente para o sistema, preenchendo informações de contato e endereço.

### Para Administradores (Área Restrita)
- **Login Seguro:** Acesso à área de administração protegido por senha.
- **Dashboard de Pedidos:** Uma tela em tempo real que mostra os pedidos do dia conforme eles chegam, com atualização automática. Permite marcar os pedidos como "em produção", "saiu para entrega" ou "finalizado".
- **Gerenciamento de Cardápio (CRUD):**
    - Adicionar, editar e remover itens do cardápio.
    - Suporte para fotos, categorias, descrição, preço e itens adicionais.
    - Ativar e desativar produtos sem precisar excluí-los.
    - Reordenar os itens no cardápio.
- **Configurações da Loja:**
    - Abrir ou fechar a loja manualmente.
    - Definir o horário de funcionamento automático.
    - Configurar os dias da semana em que a loja não abre.
- **Relatórios Financeiros:**
    - **Relatório do Dia:** Mostra o total de vendas do dia, quantidade de pedidos e o total recebido por forma de pagamento (Pix, Cartão, Dinheiro).
    - **Relatório Mensal:** Visão consolidada das vendas do mês atual.
- **CRM de Clientes:**
    - Lista todos os clientes que já fizeram pedidos.
    - Armazena informações de contato e endereço.
    - Rastreia o total gasto por cada cliente, ajudando a identificar os mais fiéis.

## Arquitetura e Tecnologias

O projeto é construído como uma aplicação monolítica utilizando **Python** e **Flask**.

- **Backend:**
    - **Flask:** Microframework web utilizado para criar as rotas da API, renderizar as páginas e controlar toda a lógica de negócio.
    - **SQLite:** Banco de dados relacional leve para armazenar dados persistentes como **pedidos** e **clientes**. O arquivo do banco é o `BISTAKA.db`.
    - **Arquivos JSON:** Utilizados como um "banco de dados" simples para informações que mudam com menos frequência:
        - `cardapio.json`: Armazena todos os itens do cardápio.
        - `config_loja.json`: Guarda as configurações de funcionamento da loja.

- **Frontend:**
    - **HTML / CSS / JavaScript:** As páginas são renderizadas no lado do servidor pelo Flask usando templates (`/templates`).
    - **JavaScript (vanilla):** Utilizado para interatividade no lado do cliente, como consumir as APIs do sistema para atualizar o status da loja, buscar o cardápio e atualizar o dashboard de pedidos em tempo real.
    - **Framework CSS:** (Opcional, se utilizado) - Ex: Bootstrap.

## Como Executar o Projeto

1.  **Pré-requisitos:**
    - Ter o Python 3 instalado.

2.  **Clone o repositório:**
    ```bash
    git clone https://github.com/seu-usuario/Bistaka_delivery-main.git
    cd Bistaka_delivery-main
    ```

3.  **Crie e ative um ambiente virtual (Recomendado):**
    ```bash
    # Criar ambiente virtual
    python3 -m venv venv

    # Ativar no Linux/macOS
    source venv/bin/activate

    # Ativar no Windows
    .\\venv\\Scripts\\activate
    ```

4.  **Instale as dependências:**
    ```bash
    pip install Flask
    ```
    *(Nota: Se houver um arquivo `requirements.txt`, use `pip install -r requirements.txt`)*

5.  **Execute a aplicação:**
    ```bash
    python app.py
    ```

6.  **Acesse o sistema:**
    - **Vitrine do Cliente:** Abra o navegador e acesse `http://127.0.0.1:5000/`
    - **Painel Administrativo:** Acesse `http://127.0.0.1:5000/login`
        - **Usuário:** admin
        - **Senha:** 3357 (pode ser alterada no arquivo `app.py`)
