import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect('academia.db')
    cursor = conn.cursor()
    # Tabela de Usuários 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT
        )
    ''')
    # Tabela de Histórico 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            peso REAL,
            altura REAL,
            imc REAL,
            classificacao TEXT,
            objetivo TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    dados = request.json
    nome = dados.get('nome', 'Usuário')
    email = dados.get('email')
    senha_hash = generate_password_hash(dados.get('senha')) #Segurança (Hash + Salt)
    try:
        conn = sqlite3.connect('academia.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha_hash))
        conn.commit()
        return jsonify({"message": "Cadastrado com sucesso!"}), 201
    except:
        return jsonify({"message": "Erro: Email já existe!"}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    dados = request.json
    conn = sqlite3.connect('academia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, senha FROM usuarios WHERE email = ?', (dados.get('email'),))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user[1], dados.get('senha')):
        return jsonify({"id": user[0], "message": "Sucesso"}), 200
    return jsonify({"message": "Email ou senha incorretos"}), 401

@app.route('/calcular-plano', methods=['POST'])
def calcular_plano():
    try:
        dados = request.json
        u_id = dados.get('usuario_id')
        # Garante que peso e altura virem números, mesmo que venham como string
        peso = float(str(dados.get('peso')).replace(',', '.'))
        altura = float(str(dados.get('altura')).replace(',', '.'))
        objetivo = dados.get('objetivo')

        if not u_id: return jsonify({"message": "Usuário não logado"}), 401

        #Cálculo de IMC
        imc = peso / (altura ** 2)
        
        # Regras de Negócio 
        if imc < 18.5: classificacao = "Abaixo do peso"
        elif 18.5 <= imc < 25: classificacao = "Normal"
        elif 25 <= imc < 30: classificacao = "Sobrepeso"
        else: classificacao = "Obesidade"

        # Manter Histórico 
        conn = sqlite3.connect('academia.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO historico (usuario_id, peso, altura, imc, classificacao, objetivo)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (u_id, peso, altura, round(imc, 2), classificacao, objetivo))
        conn.commit()
        conn.close()

        return jsonify({
            "imc": round(imc, 2),
            "classificacao": classificacao,
            "plano": {
                "treino": "Foco em Resistência" if objetivo == "Perda de Peso" else "Foco em Força",
                "dieta": "Déficit Calórico" if objetivo == "Perda de Peso" else "Superávit Calórico"
            }
        })
    except Exception as e:
        return jsonify({"message": f"Erro interno: {str(e)}"}), 500

@app.route('/historico/<int:usuario_id>', methods=['GET'])
def get_historico(usuario_id):
    conn = sqlite3.connect('academia.db')
    cursor = conn.cursor()
    cursor.execute('SELECT peso, imc, classificacao, data FROM historico WHERE usuario_id = ? ORDER BY data DESC', (usuario_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify(rows)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)