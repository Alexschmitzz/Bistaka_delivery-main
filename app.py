import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
import time
from datetime import datetime
import json
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'segredo_do_lucao_lanches' # Necessário para login e sessões

DB_FILE = 'BISTAKA.db'
CARDAPIO_FILE = 'cardapio.json'
CONFIG_FILE = 'config_loja.json'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
# ==========================================
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

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# 2. FUNÇÕES DE ARQUIVOS (CARDÁPIO E CONFIG)
# ==========================================
def load_cardapio():
    if not os.path.exists(CARDAPIO_FILE): return []
    with open(CARDAPIO_FILE, 'r', encoding='utf-8') as f: return json.load(f)

def save_cardapio(data):
    with open(CARDAPIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_config():
    if not os.path.exists(CONFIG_FILE): 
        return {
            "status_manual": "automatico", 
            "hora_abertura": "19:00", 
            "hora_fechamento": "23:59", 
            "dias_fechados": [0]
        }
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def is_loja_aberta():
    config = load_config()
    
    if config['status_manual'] == 'aberto': return True, "Loja aberta manualmente!"
    if config['status_manual'] == 'fechado': return False, "Estamos fechados por motivo de força maior."
    
    agora = datetime.now()
    dia_semana = agora.weekday()
    hora_atual = agora.strftime('%H:%M')
    
    if dia_semana in config.get('dias_fechados', []):
        return False, "Hoje é nosso dia de descanso!"
        
    if hora_atual < config['hora_abertura'] or hora_atual > config['hora_fechamento']:
        return False, f"Abrimos das {config['hora_abertura']} às {config['hora_fechamento']}."
        
    return True, "Loja Aberta"

# ==========================================
# 3. ROTAS DO CLIENTE (FRONT-END)
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/cardapio')
def api_cardapio():
    itens = load_cardapio()
    itens_ativos = [item for item in itens if item.get('ativo', True)]
    return jsonify(itens_ativos)

@app.route('/api/status_loja')
def api_status_loja():
    aberto, msg = is_loja_aberta()
    return jsonify({"aberto": aberto, "mensagem": msg})

@app.route('/api/salvar_pedido', methods=['POST'])
def salvar_pedido():
    dados = request.json
    
    # Trava de Segurança
    aberto, msg = is_loja_aberta()
    if not aberto:
        return jsonify({"status": "erro", "msg": msg}), 403
        
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

        # Atualiza ou Cria Cliente
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

        # Registra o Pedido
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

# ==========================================
# 4. ROTAS DO ADMINISTRADOR E LOGIN
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
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
        <button type="submit" style="padding:10px 20px; background:#2c3e50; color:white; border:none; border-radius:5px; cursor:pointer;">Entrar</button>
    </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    config = load_config()
    
    if request.method == 'POST':
        config['status_manual'] = request.form['status_manual']
        config['hora_abertura'] = request.form['hora_abertura']
        config['hora_fechamento'] = request.form['hora_fechamento']
        dias = request.form.getlist('dias_fechados')
        config['dias_fechados'] = [int(d) for d in dias]
        save_config(config)
        return redirect(url_for('configuracoes'))
        
    return render_template('configuracoes.html', config=config)

@app.route('/admin')
def admin():
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    return render_template('admin.html', itens=itens)

@app.route('/admin/add', methods=['POST'])
def add_item():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    itens = load_cardapio()
    novo_id = 1 if not itens else max(i['id'] for i in itens) + 1
    
    imagem = request.files.get('img_file')
    img_path = "https://via.placeholder.com/150" 

    if imagem and imagem.filename != '':
        filename = secure_filename(imagem.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagem.save(filepath)
        img_path = f"/static/uploads/{filename}"
    elif request.form.get('img_url'):
        img_path = request.form.get('img_url')

    add_nomes = request.form.getlist('add_nome[]')
    add_precos = request.form.getlist('add_preco[]')
    lista_adicionais = [{"nome": n.strip(), "preco": float(p.strip())} for n, p in zip(add_nomes, add_precos) if n.strip() and p.strip()]

    novo_item = {
        "id": novo_id,
        "categoria": request.form['categoria'],
        "nome": request.form['nome'],
        "desc": request.form['desc'],
        "preco": float(request.form['preco']),
        "img": img_path,
        "adicionais": lista_adicionais
    }
    
    itens.append(novo_item)
    save_cardapio(itens)
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    item_para_editar = next((item for item in itens if item['id'] == id), None)
    
    if not item_para_editar: return "Item não encontrado!", 404

    if request.method == 'POST':
        imagem = request.files.get('img_file')
        img_path = item_para_editar.get('img', "https://via.placeholder.com/150")

        if imagem and imagem.filename != '':
            filename = secure_filename(imagem.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagem.save(filepath)
            img_path = f"/static/uploads/{filename}"
        elif request.form.get('img_url'):
            img_path = request.form.get('img_url')

        add_nomes = request.form.getlist('add_nome[]')
        add_precos = request.form.getlist('add_preco[]')
        lista_adicionais = [{"nome": n.strip(), "preco": float(p.strip())} for n, p in zip(add_nomes, add_precos) if n.strip() and p.strip()]

        item_para_editar['categoria'] = request.form['categoria']
        item_para_editar['nome'] = request.form['nome']
        item_para_editar['desc'] = request.form['desc']
        item_para_editar['preco'] = float(request.form['preco'])
        item_para_editar['img'] = img_path
        item_para_editar['adicionais'] = lista_adicionais

        save_cardapio(itens)
        return redirect(url_for('admin'))

    return render_template('edit.html', item=item_para_editar)

@app.route('/admin/toggle/<int:id>')
def toggle_item(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    for item in itens:
        if item['id'] == id:
            item['ativo'] = not item.get('ativo', True)
            break
    save_cardapio(itens)
    return redirect(url_for('admin'))

@app.route('/admin/move/<int:id>/<direcao>')
def move_item(id, direcao):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    for i, item in enumerate(itens):
        if item['id'] == id:
            if direcao == 'up' and i > 0:
                itens[i], itens[i-1] = itens[i-1], itens[i]
            elif direcao == 'down' and i < len(itens) - 1:
                itens[i], itens[i+1] = itens[i+1], itens[i]
            break
    save_cardapio(itens)
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:id>')
def delete_item(id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    itens = load_cardapio()
    itens = [i for i in itens if i['id'] != id]
    save_cardapio(itens)
    return redirect(url_for('admin'))

# ==========================================
# 5. ROTAS DA COZINHA E RELATÓRIOS
# ==========================================
@app.route('/admin/dashboard')
def dashboard():
    if not session.get('logged_in'): return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/api/pedidos_hoje')
def api_pedidos_hoje():
    conn = get_db_connection()
    pedidos = conn.execute('''
       SELECT p.*, c.endereco, c.bairro, c.nome
        FROM pedidos p
        LEFT JOIN clientes c ON p.cliente_telefone = c.telefone
        WHERE date(p.data_pedido) = date('now', 'localtime')
        ORDER BY p.id DESC LIMIT 30
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
            "status": p["status"]
        })
    return jsonify(lista_pedidos)

@app.route('/api/stream_pedidos')
def stream_pedidos():
    def event_stream():
        ultimo_id_conhecido = 0
        while True:
            conn = get_db_connection()
            cursor = conn.execute('SELECT MAX(id) FROM pedidos')
            max_id = cursor.fetchone()[0] or 0
            conn.close()

            if max_id > ultimo_id_conhecido:
                ultimo_id_conhecido = max_id
                yield f"data: novo_pedido\n\n"
            
            time.sleep(2)

    return Response(event_stream(), mimetype="text/event-stream", headers={
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no'
    })

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

@app.route('/admin/relatorio')
def relatorio_caixa():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.execute('''
        SELECT total, metodo_pagamento FROM pedidos
        WHERE date(data_pedido) = date('now', 'localtime')
        AND status = 'finalizado'
    ''')
    pedidos_hoje = cursor.fetchall()
    conn.close()

    qtd_pedidos = len(pedidos_hoje)
    total_bruto = sum(p['total'] for p in pedidos_hoje)
    total_pix = sum(p['total'] for p in pedidos_hoje if 'Pix' in p['metodo_pagamento'] or 'pix' in p['metodo_pagamento'])
    total_cartao = sum(p['total'] for p in pedidos_hoje if 'Cartão' in p['metodo_pagamento'] or 'cartao' in p['metodo_pagamento'])
    total_dinheiro = sum(p['total'] for p in pedidos_hoje if 'Dinheiro' in p['metodo_pagamento'] or 'dinheiro' in p['metodo_pagamento'])

    return render_template('relatorio.html', qtd=qtd_pedidos, bruto=total_bruto, pix=total_pix, cartao=total_cartao, dinheiro=total_dinheiro)

@app.route('/admin/relatorio_mensal')
def relatorio_mensal():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    mes_atual = datetime.now().strftime('%Y-%m')
    cursor = conn.execute('''
        SELECT total, metodo_pagamento FROM pedidos
        WHERE strftime('%Y-%m', data_pedido) = ?
        AND status = 'finalizado'
    ''', (mes_atual,))
    pedidos_mes = cursor.fetchall()
    conn.close()

    qtd_pedidos = len(pedidos_mes)
    total_bruto = sum(p['total'] for p in pedidos_mes)
    total_pix = sum(p['total'] for p in pedidos_mes if 'Pix' in p['metodo_pagamento'] or 'pix' in p['metodo_pagamento'])
    total_cartao = sum(p['total'] for p in pedidos_mes if 'Cartão' in p['metodo_pagamento'] or 'cartao' in p['metodo_pagamento'])
    total_dinheiro = sum(p['total'] for p in pedidos_mes if 'Dinheiro' in p['metodo_pagamento'] or 'dinheiro' in p['metodo_pagamento'])

    return render_template('relatorio_mensal.html', mes=datetime.now().strftime('%m/%Y'), qtd=qtd_pedidos, bruto=total_bruto, pix=total_pix, cartao=total_cartao, dinheiro=total_dinheiro)

@app.route('/admin/clientes')
def lista_clientes():
    if not session.get('logged_in'): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM clientes ORDER BY total_gasto DESC')
    clientes = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)