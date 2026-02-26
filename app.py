import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'segredo_do_lucao_lanches' # Necessário para login e sessões

DB_FILE = 'BISTAKA.db'
CARDAPIO_FILE = 'cardapio.json'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Tabela de Clientes (CRM)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                telefone TEXT PRIMARY KEY,
                nome TEXT,
                endereco TEXT,
                bairro TEXT,
                primeiro_pedido DATETIME,
                ultimo_pedido DATETIME,
                total_gasto REAL DEFAULT 0
            )
        ''')
        # Tabela de Vendas (Financeiro)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_telefone TEXT,
                itens TEXT,
                total REAL,
                data_pedido DATETIME,
                metodo_pagamento TEXT,
                FOREIGN KEY(cliente_telefone) REFERENCES clientes(telefone)
            )
        ''')
        try:
            cursor.execute("ALTER TABLE pedidos ADD COLUMN status TEXT DEFAULT 'producao'")
        except:
            pass 
        conn.commit()

# Inicializa o banco ao iniciar o app
init_db()

# --- FUNÇÕES AUXILIARES ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

def load_cardapio():
    if not os.path.exists(CARDAPIO_FILE): return []
    with open(CARDAPIO_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_cardapio(data):
    with open(CARDAPIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- ROTAS PÚBLICAS (CLIENTE) ---

# ROTA 1: Página Inicial (Cardápio)
@app.route('/')
def index():
    return render_template('index.html')

# ROTA 2: API que o site usa para carregar os lanches
@app.route('/api/cardapio')
def api_cardapio():
    itens = load_cardapio()
    itens_ativos = [item for item in itens if item.get('ativo', True)]
    return jsonify(itens_ativos)

# ROTA 3: Salvar Pedido no Banco antes de ir pro WhatsApp
@app.route('/api/salvar_pedido', methods=['POST'])
def salvar_pedido():
    dados = request.json
    
    telefone = dados.get('telefone')
    nome = dados.get('nome', 'Cliente Site')
    endereco = dados.get('endereco')
    bairro = dados.get('bairro')
    total = float(dados.get('total'))
    pagamento = dados.get('pagamento')
    itens_texto = dados.get('resumo_itens')
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Atualiza ou Cria Cliente
        cursor.execute('SELECT * FROM clientes WHERE telefone = ?', (telefone,))
        cliente_existente = cursor.fetchone()

        if cliente_existente:
            cursor.execute('''
                UPDATE clientes SET 
                    endereco = ?, bairro = ?, ultimo_pedido = ?, total_gasto = total_gasto + ?
                WHERE telefone = ?
            ''', (endereco, bairro, agora, total, telefone))
        else:
            cursor.execute('''
                INSERT INTO clientes (telefone, nome, endereco, bairro, primeiro_pedido, ultimo_pedido, total_gasto)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (telefone, nome, endereco, bairro, agora, agora, total))

        # 2. Registra o Pedido
        cursor.execute('''
            INSERT INTO pedidos (cliente_telefone, itens, total, data_pedido, metodo_pagamento)
            VALUES (?, ?, ?, ?, ?)
        ''', (telefone, itens_texto, total, agora, pagamento))

        conn.commit()
        conn.close()
        return jsonify({"status": "sucesso", "msg": "Pedido salvo!"})
    except Exception as e:
        print(f"Erro ao salvar pedido: {e}")
        return jsonify({"status": "erro", "msg": str(e)}), 500

# --- ROTAS ADMINISTRATIVAS ---

# ROTA 4: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Mude a senha aqui se quiser
        if request.form['username'] == 'admin' and request.form['password'] == '3357':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "Senha errada!"
    return '''
    <form method="post" style="text-align:center; margin-top:50px; font-family:sans-serif;">
        <h2>🔐 Área Restrita</h2>
        <input type="text" name="username" placeholder="Usuário" required style="padding:10px;"><br><br>
        <input type="password" name="password" placeholder="Senha" required style="padding:10px;"><br><br>
        <button type="submit" style="padding:10px 20px; background:red; color:white; border:none; cursor:pointer;">Entrar</button>
    </form>
    '''

# ROTA 5: Painel de Gerenciamento de Produtos
@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    return render_template('admin.html', itens=itens)

# ROTA 6: Adicionar Novo Produto
@app.route('/admin/add', methods=['POST'])
def add_item():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    itens = load_cardapio()
    novo_id = 1 if not itens else max(i['id'] for i in itens) + 1
    
    # --- LÓGICA DE IMAGEM ---
    imagem = request.files.get('img_file')
    img_path = "https://via.placeholder.com/150" 

    if imagem and imagem.filename != '':
        from werkzeug.utils import secure_filename
        filename = secure_filename(imagem.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagem.save(filepath)
        img_path = f"/static/uploads/{filename}"
    elif request.form.get('img_url'):
        img_path = request.form.get('img_url')

    # --- LÓGICA DE ADICIONAIS (NOVO) ---
    add_nomes = request.form.getlist('add_nome[]')
    add_precos = request.form.getlist('add_preco[]')
    
    lista_adicionais = []
    # Junta os nomes e preços digitados e salva numa lista
    for nome, preco in zip(add_nomes, add_precos):
        if nome.strip() and preco.strip():
            lista_adicionais.append({
                "nome": nome.strip(),
                "preco": float(preco.strip())
            })

    novo_item = {
        "id": novo_id,
        "categoria": request.form['categoria'],
        "nome": request.form['nome'],
        "desc": request.form['desc'],
        "preco": float(request.form['preco']),
        "img": img_path,
        "adicionais": lista_adicionais # Salva os adicionais no lanche
    }
    
    itens.append(novo_item)
    save_cardapio(itens)
    return redirect(url_for('admin'))


# ROTA: Ativar/Desativar Produto
@app.route('/admin/toggle/<int:id>')
def toggle_item(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    for item in itens:
        if item['id'] == id:
            # Inverte o status atual (Se é True vira False, se é False vira True)
            item['ativo'] = not item.get('ativo', True)
            break
    save_cardapio(itens)
    return redirect(url_for('admin'))

# ROTA: Mover Produto (Para cima ou Para baixo)
@app.route('/admin/move/<int:id>/<direcao>')
def move_item(id, direcao):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    
    for i, item in enumerate(itens):
        if item['id'] == id:
            if direcao == 'up' and i > 0:
                # Troca de lugar com o item de cima
                itens[i], itens[i-1] = itens[i-1], itens[i]
            elif direcao == 'down' and i < len(itens) - 1:
                # Troca de lugar com o item de baixo
                itens[i], itens[i+1] = itens[i+1], itens[i]
            break
            
    save_cardapio(itens)
    return redirect(url_for('admin'))

# ROTA 7: Deletar Produto
@app.route('/admin/delete/<int:id>')
def delete_item(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    itens = load_cardapio()
    itens = [i for i in itens if i['id'] != id]
    save_cardapio(itens)
    return redirect(url_for('admin'))


# --- ROTAS DA COZINHA/DASHBOARD ---

# ROTA 8: API para o Painel da Cozinha (Atualiza sozinho)
@app.route('/api/pedidos_hoje')
def api_pedidos_hoje():
    conn = get_db_connection()
    # Pega os últimos 20 pedidos de hoje
    pedidos = conn.execute('''
       SELECT p.*, c.endereco, c.bairro, c.nome
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_telefone = c.telefone
        WHERE date(p.data_pedido) = date('now', 'localtime')
        ORDER BY p.id DESC LIMIT 20
    ''').fetchall()
    conn.close()
    
    lista_pedidos = []
    for p in pedidos:
        lista_pedidos.append({
            "id": p["id"],
            "cliente": p["cliente_telefone"],
            "nome": p["nome"],
            "endereco": p["endereco"],
            "bairro": p["bairro"],
            "itens": p["itens"],
            "total": p["total"],
            "hora": p["data_pedido"][11:16],
            "pagamento": p["metodo_pagamento"],
            "status": p["status"],

        })
    return jsonify(lista_pedidos)

# ROTA 9: Tela do Dashboard (Impressão)
@app.route('/admin/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/mudar_status/<int:pedido_id>', methods=['POST'])
def mudar_status(pedido_id):
    if not session.get('logged_in'): return redirect(url_for('login'))

    dados = request.json
    novo_status = dados.get('status')
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        conn.commit()
        
    return jsonify({'status': 'sucesso'})

if __name__ == '__main__':
    # Roda acessível na rede local
    app.run(host='0.0.0.0', port=5000, debug=True)
