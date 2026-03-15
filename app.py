from flask import Flask, redirect, url_for, session, request, send_from_directory
import io
import os
import sqlite3
import datetime as dt
import uuid
import hashlib
import pandas as pd

app = Flask(__name__)
app.secret_key = "dev-secret-change-later"

DB_PATH = "data.db"

# Split padrão (Rafa ganha mais)
LUCAS_SHARE = 0.40
RAFA_SHARE = 0.60

ALLOWED_PROFILES = {"Lucas", "Rafa"}
ALLOWED_TIPO = {"Saida", "Entrada"}

# "Responsabilidade" (no seu print ainda vem como "Dono")
ALLOWED_RESP = {"Casa", "Lucas", "Rafa"}

# Aceita variações no input, mas o banco guarda sempre canônico com underscore
RATEIO_CANON = {
    "60/40": "60_40",
    "60_40": "60_40",
    "50/50": "50_50",
    "50_50": "50_50",
    "100%_Meu": "100_meu",
    "100_meu": "100_meu",
    "100%_Outro": "100_outro",
    "100_outro": "100_outro",
}

# Sugestões (não trava)
SUGGESTED_CATEGORIES = [
    "Alimentação",
    "Assinaturas e Serviços Digitais",
    "Carro",
    "Combustível",
    "Compras Online Diversas",
    "Compras Pessoais",
    "Contas da Casa",
    "Pets",
    "Presentes",
    "Saúde",
    "Supermercado e Itens Domésticos",
    "Mercado",
    "Itens de Casa",
    "Transporte",
    "Viagens e Lazer",
    "Academia",
    "Lura",
    "Outros",
]

# Fixos (aparecem no topo apenas quando a lista do mês está aberta)
# Obs: responsabilidade Casa, rateio 60/40, e quem pagou de fato é "uploaded_by" (perfil que importou)
FIXOS = [
    {"key": "aluguel", "label": "Aluguel", "valor": 2541.00, "payer": "Rafa", "resp": "Casa", "rateio": "60_40", "categoria": "Contas da Casa"},
    {"key": "condominio", "label": "Condomínio", "valor": 1374.42, "payer": "Lucas", "resp": "Casa", "rateio": "60_40", "categoria": "Contas da Casa"},
    {"key": "internet", "label": "Internet", "valor": 115.00, "payer": "Lucas", "resp": "Casa", "rateio": "60_40", "categoria": "Contas da Casa"},
    {"key": "estacionamento", "label": "Estacionamento Amazon", "valor": 75.00, "payer": "Rafa", "resp": "Casa", "rateio": "60_40", "categoria": "Transporte"},
]

# Variáveis "sempre aparecem", mas ficam como pendentes até você preencher manualmente
PENDENTES = [
    {"key": "luz", "label": "Luz", "categoria": "Contas da Casa"},
    {"key": "gas", "label": "Gás", "categoria": "Contas da Casa"},
    {"key": "empregada", "label": "Empregada", "categoria": "Contas da Casa"},
]

BASE_CSS = """
<style>
  :root{
    --bg1:#f7f8ff;
    --bg2:#f6fffb;
    --card:#ffffff;
    --text:#0f172a;
    --muted:#64748b;
    --border: rgba(15,23,42,.08);
    --shadow: 0 14px 40px rgba(15,23,42,.08);
    --radius: 18px;
    --lucas1:#1d4ed8;
    --lucas2:#60a5fa;
    --rafa1:#16a34a;
    --rafa2:#86efac;
    --neutral1:#111827;
    --neutral2:#94a3b8;
  }

  *{box-sizing:border-box}
  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
    color:var(--text);
    background: radial-gradient(1200px 600px at 20% 0%, var(--bg1) 0%, rgba(255,255,255,0) 60%),
                radial-gradient(1200px 600px at 80% 0%, var(--bg2) 0%, rgba(255,255,255,0) 60%),
                linear-gradient(180deg, #ffffff 0%, #fbfbff 100%);
    min-height:100vh;
  }

  .topbar{
    position: sticky;
    top:0;
    z-index:5;
    backdrop-filter: blur(10px);
    background: rgba(255,255,255,.7);
    border-bottom: 1px solid var(--border);
  }

  .wrap{max-width:1100px; margin:0 auto; padding: 16px;}
  .row{display:flex; gap:12px; align-items:center; flex-wrap:wrap;}
  .space{justify-content:space-between;}
  .pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:6px 10px;
    border-radius:999px;
    border:1px solid var(--border);
    background: rgba(255,255,255,.7);
    font-size:12px;
    color:var(--muted);
  }
  .brand{
    display:flex;
    align-items:center;
    gap:10px;
  }
  .dot{
    width:10px; height:10px; border-radius:999px;
    background: linear-gradient(135deg, var(--neutral1), var(--neutral2));
    box-shadow: 0 0 0 4px rgba(15,23,42,.06);
  }
  .dot.lucas{background: linear-gradient(135deg, var(--lucas1), var(--lucas2));}
  .dot.rafa{background: linear-gradient(135deg, var(--rafa1), var(--rafa2));}

  .nav{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
  }

  .btn{
    appearance:none;
    border: 1px solid var(--border);
    background: rgba(255,255,255,.8);
    color: var(--text);
    padding: 10px 14px;
    border-radius: 14px;
    font-weight: 800;
    cursor:pointer;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    transition: transform .06s ease, box-shadow .12s ease, border-color .12s ease;
  }
  .btn:hover{border-color: rgba(15,23,42,.20); box-shadow: 0 10px 22px rgba(15,23,42,.08);}
  .btn:active{transform: translateY(1px);}

  .btnPrimary{
    border:0;
    color:white;
    box-shadow: 0 16px 32px rgba(29,78,216,.18);
    background: linear-gradient(135deg, var(--neutral1), var(--neutral2));
  }
  .btnLucas{ background: linear-gradient(135deg, var(--lucas1), var(--lucas2)); box-shadow: 0 16px 32px rgba(29,78,216,.18); }
  .btnRafa{ background: linear-gradient(135deg, var(--rafa1), var(--rafa2)); box-shadow: 0 16px 32px rgba(22,163,74,.18); }

  .btnGhost{
    background: rgba(255,255,255,.55);
  }

  .btnDanger{
    border:0;
    color:white;
    background: linear-gradient(135deg, #b91c1c, #fb7185);
  }

  .card{
    background: rgba(255,255,255,.85);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow);
    margin-top: 14px;
  }

  h1,h2,h3{margin:0 0 10px;}
  p{margin:0 0 10px; color: var(--muted);}

  label{font-weight:800; display:block; margin: 10px 0 6px;}
  input[type="text"], input[type="number"], input[type="file"], input[type="date"], select, textarea{
    width:100%;
    padding: 10px 12px;
    border-radius: 14px;
    border:1px solid var(--border);
    background: rgba(255,255,255,.9);
    outline:none;
  }
  textarea{min-height:90px; resize:vertical;}

  .grid2{display:grid; grid-template-columns: 1fr 1fr; gap:12px;}
  .grid3{display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px;}
  .grid4{display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:12px;}

  .kpi{display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:12px;}
  .kpi .box{
    border:1px solid var(--border);
    border-radius: 16px;
    background: rgba(255,255,255,.85);
    padding: 12px;
  }
  .kpi .label{font-size:12px; color: var(--muted); margin-bottom:6px;}
  .kpi .value{font-size:20px; font-weight:900;}

  .right{text-align:right}
  .mono{font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;}
  .small{font-size:12px; color: var(--muted);}

  .okBox{
    border:1px solid rgba(22,163,74,.25);
    background: rgba(22,163,74,.06);
    padding: 12px;
    border-radius: 14px;
  }
  .errorBox{
    border:1px solid rgba(185,28,28,.25);
    background: rgba(185,28,28,.06);
    padding: 12px;
    border-radius: 14px;
  }

  table{width:100%; border-collapse: collapse; margin-top:10px;}
  th,td{border-bottom:1px solid rgba(15,23,42,.06); padding: 10px 8px; vertical-align: top; font-size:13px;}
  th{color:#334155; background: rgba(248,250,252,.8); position: sticky; top: 58px; z-index:2;}
  details{
    border: 1px solid rgba(15,23,42,.06);
    background: rgba(255,255,255,.65);
    border-radius: 14px;
    padding: 10px 12px;
    margin-top: 10px;
  }
  summary{cursor:pointer; font-weight:900;}
  .tag{
    display:inline-flex; gap:8px; align-items:center;
    padding:6px 10px;
    border-radius:999px;
    border:1px solid rgba(15,23,42,.08);
    background: rgba(255,255,255,.6);
    font-size:12px;
    color: #334155;
  }

  @media (max-width: 900px){
    .grid4,.grid3,.grid2,.kpi{grid-template-columns: 1fr;}
    th{top: 118px;}
  }
</style>
"""

def brl(x: float) -> str:
    try:
        x = float(x or 0)
    except:
        x = 0.0
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def pct(x: float) -> str:
    try:
        return f"{x*100:.1f}%"
    except:
        return "0.0%"

def _normalize_str(x) -> str:
    if x is None:
        return ""
    return str(x).strip()

def current_year_month():
    today = dt.date.today()
    return today.year, today.month

def month_ref_from(year_str: str, month_str: str) -> str:
    return f"{year_str}{month_str}"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _col_exists(conn, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS imports (
      batch_id TEXT PRIMARY KEY,
      month_ref TEXT NOT NULL,
      uploaded_by TEXT NOT NULL,
      filename TEXT,
      row_count INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL
    )
    """)
    if not _col_exists(conn, "imports", "file_hash"):
        cur.execute("ALTER TABLE imports ADD COLUMN file_hash TEXT")
    if not _col_exists(conn, "imports", "source"):
        cur.execute("ALTER TABLE imports ADD COLUMN source TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id TEXT NOT NULL,
      month_ref TEXT NOT NULL,
      uploaded_by TEXT NOT NULL,
      dt_text TEXT,
      estabelecimento TEXT,
      categoria TEXT,
      valor REAL NOT NULL,
      tipo TEXT NOT NULL,
      dono TEXT NOT NULL,     -- aqui é "Responsabilidade"
      rateio TEXT NOT NULL,   -- canônico: 60_40, 50_50, 100_meu, 100_outro
      observacao TEXT,
      parcela TEXT,
      created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS incomes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month_ref TEXT NOT NULL,
      profile TEXT NOT NULL,
      salario_1 REAL NOT NULL DEFAULT 0,
      salario_2 REAL NOT NULL DEFAULT 0,
      extras REAL NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(month_ref, profile)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS investments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month_ref TEXT NOT NULL,
      profile TEXT NOT NULL,
      amount REAL NOT NULL DEFAULT 0,
      note TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(month_ref, profile)
    )
    """)

    # trava de mês por perfil (fechar mês)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS month_locks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month_ref TEXT NOT NULL,
      profile TEXT NOT NULL,
      locked INTEGER NOT NULL DEFAULT 0,
      locked_at TEXT,
      UNIQUE(month_ref, profile)
    )
    """)

    conn.commit()
    conn.close()

init_db()

def profile_dot(profile: str) -> str:
    if profile == "Lucas":
        return "lucas"
    if profile == "Rafa":
        return "rafa"
    return ""

def topbar_html(profile: str, active: str = "overview"):
    if not profile:
        return f"""
        <div class="topbar">
          <div class="wrap">
            <div class="row space">
              <div class="brand">
                <span class="dot"></span>
                <b>Casella</b>
              </div>
            </div>
          </div>
        </div>
        """

    def nav_btn(label, endpoint, key):
        klass = "btn btnPrimary" if key == active else "btn btnGhost"
        return f"<a class='{klass}' href='{endpoint}'>{label}</a>"

    nav = f"""
    <div class="nav">
      {nav_btn("Overview", url_for("overview"), "overview")}
      {nav_btn("Transações", url_for("transacoes"), "transacoes")}
      {nav_btn("Perfil", url_for("perfil"), "perfil")}
    </div>
    """

    return f"""
    <div class="topbar">
      <div class="wrap">
        <div class="row space">
          <div class="brand">
            <span class="dot {profile_dot(profile)}"></span>
            <div>
              <b>Casella</b><br/>
              <span class="small">Perfil: <b>{profile}</b></span>
            </div>
          </div>
          {nav}
        </div>
      </div>
    </div>
    """

def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

# ------------ IMPORT FLEXÍVEL (suporta seu input do print) ------------

_CANON = {
    "data": "Data",
    "dono": "Dono",
    "responsabilidade": "Dono",
    "categoria": "Categoria",
    "descrição": "Descricao",
    "descricao": "Descricao",
    "estabelecimento": "Estabelecimento",
    "valor": "Valor",
    "rateio": "Rateio",
    "tipo": "Tipo",
    "observacao": "Observacao",
    "observação": "Observacao",
    "parcela": "Parcela",
}

def _canon_col(c: str) -> str:
    c = _normalize_str(c)
    key = c.lower()
    return _CANON.get(key, c)

def _parse_money(v) -> float:
    """
    Aceita número/moeda do Excel, com/sem R$, com ponto/vírgula, negativo/positivo.
    """
    if v is None:
        return 0.0
    try:
        if pd.isna(v):
            return 0.0
    except:
        pass

    s = str(v).strip()
    s = s.replace("R$", "").replace("\u00a0", " ").strip()
    s = s.replace(" ", "")

    # Se tiver ambos, assume "." milhar e "," decimal
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # se só vírgula, vira decimal
        if "," in s and "." not in s:
            s = s.replace(",", ".")

    try:
        return float(s)
    except:
        return 0.0

def parse_num_br(v) -> float:
    try:
        v = str(v).replace("R$", "").replace(" ", "").strip()
        if "," in v and "." in v:
            v = v.replace(".", "").replace(",", ".")
        elif "," in v and "." not in v:
            v = v.replace(",", ".")
        return float(v) if v else 0.0
    except:
        return 0.0

def parse_value_expression(v) -> float:
    s = _normalize_str(v)
    if not s:
        return 0.0
    # Permite somas/subtrações simples: 100+130-20, com vírgula/ponto.
    safe = s.replace(" ", "")
    allowed = set("0123456789+-,.")
    if any(ch not in allowed for ch in safe):
        return parse_num_br(s)

    safe = safe.replace(",", ".")
    total = 0.0
    current = ""
    sign = 1.0

    try:
        for ch in safe:
            if ch in "+-":
                if current:
                    total += sign * float(current)
                    current = ""
                sign = 1.0 if ch == "+" else -1.0
            else:
                current += ch

        if current:
            total += sign * float(current)
        return total
    except:
        return parse_num_br(s)

def _canon_rateio(x: str) -> str:
    x = _normalize_str(x)
    if x in RATEIO_CANON:
        return RATEIO_CANON[x]
    return x  # deixa passar para erro de validação, se for algo desconhecido

def read_excel_from_bytes(raw: bytes) -> pd.DataFrame:
    buf = io.BytesIO(raw)

    # por padrão pega a primeira aba
    df = pd.read_excel(buf, engine="openpyxl")
    df = df.copy()

    # normaliza os headers se existirem
    df.columns = [_canon_col(c) for c in df.columns]

    # MODO CURTO: ordem do print (Data, Dono, Categoria, Descricao, Valor, Rateio)
    # Importante: você pediu para não travar header; então a regra é: se tiver 6+ colunas,
    # pegamos as 6 primeiras por posição e forçamos essa ordem.
    if len(df.columns) >= 6:
        df_short = df.iloc[:, :6].copy()
        df_short.columns = ["Data", "Dono", "Categoria", "Descricao", "Valor", "Rateio"]

        # Data: sem validação de formato
        df_short["Data"] = df_short["Data"].apply(lambda v: "" if pd.isna(v) else str(v))

        # Valor
        df_short["Valor"] = df_short["Valor"].apply(_parse_money)

        # Tipo inferido pelo sinal
        df_short["Tipo"] = df_short["Valor"].apply(lambda x: "Entrada" if float(x or 0) < 0 else "Saida")
        df_short["Valor"] = df_short["Valor"].apply(lambda x: abs(float(x or 0)))

        # Estabelecimento é a descrição
        df_short["Estabelecimento"] = df_short["Descricao"].apply(_normalize_str)

        # Observacao / Parcela vazios
        df_short["Observacao"] = ""
        df_short["Parcela"] = ""

        # strings
        df_short["Dono"] = df_short["Dono"].apply(_normalize_str)
        df_short["Categoria"] = df_short["Categoria"].apply(_normalize_str)
        df_short["Rateio"] = df_short["Rateio"].apply(_normalize_str)

        return df_short

    raise ValueError("Arquivo inválido: precisa ter pelo menos 6 colunas (Data, Dono, Categoria, Descrição, Valor, Rateio)")

def validate_transactions(df: pd.DataFrame):
    errors = []
    normalized_rows = []

    for idx, row in df.iterrows():
        line_number = idx + 2

        tipo = _normalize_str(row.get("Tipo"))
        resp = _normalize_str(row.get("Dono"))  # responsabilidade
        rateio_raw = _normalize_str(row.get("Rateio"))
        rateio = _canon_rateio(rateio_raw)

        valor = row.get("Valor")
        try:
            valor_f = float(valor)
        except:
            valor_f = 0.0

        if valor_f <= 0:
            errors.append(f"Linha {line_number}: Valor inválido, precisa ser maior que 0")

        if tipo not in ALLOWED_TIPO:
            errors.append(f"Linha {line_number}: Tipo inválido, use Saida ou Entrada")

        if resp not in ALLOWED_RESP:
            errors.append(f"Linha {line_number}: Responsabilidade inválida, use Casa, Lucas ou Rafa")

        if rateio not in {"60_40", "50_50", "100_meu", "100_outro"}:
            errors.append(f"Linha {line_number}: Rateio inválido (use 60/40, 50/50, 100%_Meu ou 100%_Outro)")

        # regras de coerência
        if resp == "Casa" and rateio not in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: Responsabilidade Casa só permite rateio 60/40 ou 50/50")

        if resp in {"Lucas", "Rafa"} and rateio in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: Rateio 60/40 ou 50/50 exige Responsabilidade Casa")

        normalized_rows.append(
            {
                "Data": _normalize_str(row.get("Data")),
                "Estabelecimento": _normalize_str(row.get("Estabelecimento")),
                "Categoria": _normalize_str(row.get("Categoria")),
                "Valor": valor_f,
                "Tipo": tipo,
                "Dono": resp,
                "Rateio": rateio,
                "Observacao": _normalize_str(row.get("Observacao")),
                "Parcela": _normalize_str(row.get("Parcela")),
            }
        )

    return errors, normalized_rows

# ------------ DB HELPERS ------------

def _insert_import(conn, batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO imports (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source))

def _insert_transaction(conn, batch_id, month_ref, uploaded_by, r, created_at):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO transactions
      (batch_id, month_ref, uploaded_by, dt_text, estabelecimento, categoria, valor, tipo, dono, rateio, observacao, parcela, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        batch_id,
        month_ref,
        uploaded_by,
        r.get("Data", ""),
        r.get("Estabelecimento", ""),
        r.get("Categoria", ""),
        float(r.get("Valor") or 0),
        r.get("Tipo", ""),
        r.get("Dono", ""),
        r.get("Rateio", ""),
        r.get("Observacao", ""),
        r.get("Parcela", ""),
        created_at
    ))

def is_duplicate_import(month_ref: str, uploaded_by: str, file_hash: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT 1
      FROM imports
      WHERE month_ref = ?
        AND uploaded_by = ?
        AND file_hash = ?
        AND status = 'imported'
      LIMIT 1
    """, (month_ref, uploaded_by, file_hash))
    hit = cur.fetchone() is not None
    conn.close()
    return hit

def create_preview_batch(month_ref: str, uploaded_by: str, filename: str, rows: list, file_hash: str) -> str:
    batch_id = uuid.uuid4().hex
    now = dt.datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db()
    _insert_import(conn, batch_id, month_ref, uploaded_by, filename, len(rows), "preview", now, file_hash, "excel")
    for r in rows:
        _insert_transaction(conn, batch_id, month_ref, uploaded_by, r, now)

    conn.commit()
    conn.close()
    return batch_id

def finalize_import(batch_id: str, profile: str) -> tuple[bool, str]:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM imports WHERE batch_id = ?", (batch_id,))
    imp = cur.fetchone()
    if not imp:
        conn.close()
        return False, "Importação não encontrada"

    if imp["uploaded_by"] != profile:
        conn.close()
        return False, "Você só pode importar batches criados no seu perfil"

    if imp["status"] == "imported":
        conn.close()
        return False, "Esse batch já foi importado"

    cur.execute("UPDATE imports SET status = 'imported' WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Importação concluída"

def delete_batch(batch_id: str, profile: str) -> tuple[bool, str]:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM imports WHERE batch_id = ?", (batch_id,))
    imp = cur.fetchone()
    if not imp:
        conn.close()
        return False, "Importação não encontrada"

    if imp["uploaded_by"] != profile:
        conn.close()
        return False, "Você só pode excluir imports feitos no seu perfil"

    cur.execute("DELETE FROM transactions WHERE batch_id = ?", (batch_id,))
    cur.execute("DELETE FROM imports WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Importação excluída"

def fetch_transaction_by_id(tx_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*, i.status
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.id = ?
      LIMIT 1
    """, (tx_id,))
    row = cur.fetchone()
    conn.close()
    return row

def delete_transaction(tx_id: int, profile: str) -> tuple[bool, str]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT uploaded_by FROM transactions WHERE id = ?", (tx_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Lançamento não encontrado"
    if row["uploaded_by"] != profile:
        conn.close()
        return False, "Você só pode excluir lançamentos do seu perfil"

    cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    return True, "Lançamento excluído"

def update_transaction(tx_id: int, profile: str, row: dict) -> tuple[bool, str]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT uploaded_by FROM transactions WHERE id = ?", (tx_id,))
    found = cur.fetchone()
    if not found:
        conn.close()
        return False, "Lançamento não encontrado"
    if found["uploaded_by"] != profile:
        conn.close()
        return False, "Você só pode editar lançamentos do seu perfil"

    cur.execute("""
      UPDATE transactions
      SET dt_text = ?, estabelecimento = ?, categoria = ?, valor = ?, tipo = ?, dono = ?, rateio = ?, observacao = ?, parcela = ?
      WHERE id = ?
    """, (
        row.get("Data", ""),
        row.get("Estabelecimento", ""),
        row.get("Categoria", ""),
        float(row.get("Valor") or 0),
        row.get("Tipo", ""),
        row.get("Dono", ""),
        row.get("Rateio", ""),
        row.get("Observacao", ""),
        row.get("Parcela", ""),
        tx_id,
    ))
    conn.commit()
    conn.close()
    return True, "Lançamento atualizado"

def fetch_imported_transactions(month_ref: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*, i.source, i.filename, i.status
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.month_ref = ?
        AND i.status = 'imported'
      ORDER BY t.id DESC
    """, (month_ref,))
    rows = cur.fetchall()
    conn.close()
    return rows

def fetch_house_transactions(month_ref: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.month_ref = ?
        AND i.status = 'imported'
        AND t.dono = 'Casa'
        AND t.rateio IN ('60_40','50_50')
      ORDER BY t.id ASC
    """, (month_ref,))
    rows = cur.fetchall()
    conn.close()
    return rows

def signed_value(tipo: str, valor: float) -> float:
    # Entrada reduz gasto (reembolso)
    if tipo == "Entrada":
        return -abs(valor)
    return abs(valor)

def share_for(profile: str, rateio: str) -> float:
    if rateio == "50_50":
        return 0.5
    if rateio == "60_40":
        return LUCAS_SHARE if profile == "Lucas" else RAFA_SHARE
    return 0.0

def compute_casa(month_ref: str):
    rows = fetch_house_transactions(month_ref)

    total_casa = 0.0
    paid_lucas = 0.0
    paid_rafa = 0.0
    expected_lucas = 0.0
    expected_rafa = 0.0
    by_category = {}

    for r in rows:
        val = signed_value(r["tipo"], r["valor"])
        total_casa += val

        cat = r["categoria"] or "Sem categoria"
        if cat not in by_category:
            by_category[cat] = {"total": 0.0, "lucas": 0.0, "rafa": 0.0, "items": []}
        by_category[cat]["total"] += val
        by_category[cat]["items"].append(r)

        # "quem pagou de fato" é uploaded_by
        if r["uploaded_by"] == "Lucas":
            paid_lucas += val
            by_category[cat]["lucas"] += val
        elif r["uploaded_by"] == "Rafa":
            paid_rafa += val
            by_category[cat]["rafa"] += val

        if r["rateio"] == "60_40":
            expected_lucas += val * LUCAS_SHARE
            expected_rafa += val * RAFA_SHARE
        elif r["rateio"] == "50_50":
            expected_lucas += val * 0.5
            expected_rafa += val * 0.5

    lucas_diff = paid_lucas - expected_lucas
    rafa_diff = paid_rafa - expected_rafa

    settlement_text = "Sem acerto necessário"
    settlement_value = 0.0
    if lucas_diff > 0.01:
        settlement_text = "Rafa deve passar para Lucas"
        settlement_value = lucas_diff
    elif rafa_diff > 0.01:
        settlement_text = "Lucas deve passar para Rafa"
        settlement_value = rafa_diff

    cats_sorted = sorted(by_category.items(), key=lambda x: x[1]["total"], reverse=True)

    return {
        "total_casa": total_casa,
        "paid_lucas": paid_lucas,
        "paid_rafa": paid_rafa,
        "expected_lucas": expected_lucas,
        "expected_rafa": expected_rafa,
        "settlement_text": settlement_text,
        "settlement_value": settlement_value,
        "cats_sorted": cats_sorted,
    }

def get_income(month_ref: str, profile: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT salario_1, salario_2, extras
      FROM incomes
      WHERE month_ref = ? AND profile = ?
    """, (month_ref, profile))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"salario_1": 0.0, "salario_2": 0.0, "extras": 0.0, "total": 0.0}
    s1 = float(row["salario_1"] or 0)
    s2 = float(row["salario_2"] or 0)
    ex = float(row["extras"] or 0)
    return {"salario_1": s1, "salario_2": s2, "extras": ex, "total": s1 + s2 + ex}

def upsert_income(month_ref: str, profile: str, salario_1: float, salario_2: float, extras: float):
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM incomes WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("""
          UPDATE incomes
          SET salario_1 = ?, salario_2 = ?, extras = ?, updated_at = ?
          WHERE month_ref = ? AND profile = ?
        """, (salario_1, salario_2, extras, now, month_ref, profile))
    else:
        cur.execute("""
          INSERT INTO incomes (month_ref, profile, salario_1, salario_2, extras, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (month_ref, profile, salario_1, salario_2, extras, now, now))

    conn.commit()
    conn.close()

def get_investment(month_ref: str, profile: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT amount, note
      FROM investments
      WHERE month_ref = ? AND profile = ?
    """, (month_ref, profile))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"amount": 0.0, "note": ""}
    return {"amount": float(row["amount"] or 0), "note": row["note"] or ""}

def upsert_investment(month_ref: str, profile: str, amount: float, note: str):
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM investments WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("""
          UPDATE investments
          SET amount = ?, note = ?, updated_at = ?
          WHERE month_ref = ? AND profile = ?
        """, (amount, note, now, month_ref, profile))
    else:
        cur.execute("""
          INSERT INTO investments (month_ref, profile, amount, note, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?)
        """, (month_ref, profile, amount, note, now, now))

    conn.commit()
    conn.close()

def compute_individual(month_ref: str, profile: str):
    rows = fetch_imported_transactions(month_ref)

    income_total = 0.0

    house_by_cat = {}
    house_total = 0.0

    my_personal_by_cat = {}
    my_personal_total = 0.0

    receivable_total = 0.0
    payable_total = 0.0

    for r in rows:
        if r["tipo"] == "Entrada" and r["uploaded_by"] == profile and r["dono"] == profile:
            income_total += abs(float(r["valor"] or 0))

        val = signed_value(r["tipo"], r["valor"])
        cat = r["categoria"] or "Sem categoria"

        # Responsabilidade Casa: entra no split
        if r["dono"] == "Casa" and r["rateio"] in ("60_40", "50_50"):
            sh = share_for(profile, r["rateio"])
            part = val * sh
            house_total += part
            house_by_cat[cat] = house_by_cat.get(cat, 0.0) + part
            continue

        # Responsabilidade do próprio profile e rateio 100_meu
        if r["rateio"] == "100_meu" and r["uploaded_by"] == profile and r["dono"] == profile:
            my_personal_total += val
            my_personal_by_cat[cat] = my_personal_by_cat.get(cat, 0.0) + val
            continue

        # 100_outro: fiz para o outro (eu paguei algo que era do outro)
        if r["rateio"] == "100_outro" and r["uploaded_by"] == profile and r["dono"] != "Casa" and r["dono"] != profile:
            receivable_total += val
            continue

        # 100_outro: o outro pagou algo que era meu (eu devo)
        if r["rateio"] == "100_outro" and r["uploaded_by"] != profile and r["dono"] == profile:
            payable_total += val
            continue

    income = {"salario_1": 0.0, "salario_2": 0.0, "extras": income_total, "total": income_total}
    inv = get_investment(month_ref, profile)
    invested = float(inv["amount"] or 0)

    expenses_effective = house_total + my_personal_total + payable_total
    saldo_pos_pagamentos = income["total"] - expenses_effective
    saldo_em_conta = saldo_pos_pagamentos - invested

    invested_pct = 0.0
    if income["total"] > 0:
        invested_pct = invested / income["total"]

    cats_house = sorted(house_by_cat.items(), key=lambda x: x[1], reverse=True)
    cats_personal = sorted(my_personal_by_cat.items(), key=lambda x: x[1], reverse=True)

    return {
        "income": income,
        "invested": invested,
        "invest_note": inv.get("note", ""),
        "invested_pct": invested_pct,
        "house_total": house_total,
        "my_personal_total": my_personal_total,
        "receivable_total": receivable_total,
        "payable_total": payable_total,
        "expenses_effective": expenses_effective,
        "saldo_pos_pagamentos": saldo_pos_pagamentos,
        "saldo_em_conta": saldo_em_conta,
        "cats_house": cats_house,
        "cats_personal": cats_personal,
    }

def create_manual_batch(month_ref: str, uploaded_by: str, row: dict) -> str:
    batch_id = uuid.uuid4().hex
    now = dt.datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db()
    _insert_import(conn, batch_id, month_ref, uploaded_by, "manual_entry", 1, "imported", now, None, "manual")
    _insert_transaction(conn, batch_id, month_ref, uploaded_by, row, now)

    conn.commit()
    conn.close()
    return batch_id

def get_lock(month_ref: str, profile: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT locked FROM month_locks WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return int(row["locked"] or 0) == 1

def set_lock(month_ref: str, profile: str, locked: bool):
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM month_locks WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    exists = cur.fetchone() is not None
    if exists:
        cur.execute("UPDATE month_locks SET locked = ?, locked_at = ? WHERE month_ref = ? AND profile = ?",
                    (1 if locked else 0, now if locked else None, month_ref, profile))
    else:
        cur.execute("INSERT INTO month_locks (month_ref, profile, locked, locked_at) VALUES (?, ?, ?, ?)",
                    (month_ref, profile, 1 if locked else 0, now if locked else None))
    conn.commit()
    conn.close()

def year_month_select_html(selected_year: str, selected_month: str):
    year_options = "".join([
        f"<option value='{y}' {'selected' if str(y)==str(selected_year) else ''}>{y}</option>"
        for y in range(2024, 2031)
    ])
    month_options = "".join([
        f"<option value='{m:02d}' {'selected' if f'{m:02d}'==str(selected_month) else ''}>{m:02d}</option>"
        for m in range(1, 13)
    ])
    return year_options, month_options

def month_selector_block(selected_year: str, selected_month: str, action_url: str):
    year_options, month_options = year_month_select_html(selected_year, selected_month)
    month_ref = month_ref_from(selected_year, selected_month)
    # auto-submit: sem botão Atualizar
    return f"""
      <form method="get" action="{action_url}" id="monthForm">
        <div class="grid2">
          <div>
            <label>Ano</label>
            <select name="Ano" onchange="document.getElementById('monthForm').submit()">{year_options}</select>
          </div>
          <div>
            <label>Mês</label>
            <select name="Mes" onchange="document.getElementById('monthForm').submit()">{month_options}</select>
          </div>
        </div>
        <div style="margin-top:10px;">
          <span class="pill">Mês de referência: <b>{month_ref}</b></span>
        </div>
      </form>
    """

def template_path():
    # template que você colocou no repo: /assets/Template_Financas_Casella.xlsx
    # (não precisa .keep; mas não tem problema ter)
    return os.path.join(os.path.dirname(__file__), "assets", "Template_Financas_Casella.xlsx")

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    profile = session.get("profile", "")
    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Casella</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h1>Casella</h1>
            <p>Escolha o perfil para entrar.</p>
            <div class="grid2" style="margin-top:14px;">
              <a class="btn btnPrimary btnLucas" style="padding:18px 16px; font-size:16px;" href="{url_for('set_profile', profile='Lucas')}">Entrar como Lucas</a>
              <a class="btn btnPrimary btnRafa" style="padding:18px 16px; font-size:16px;" href="{url_for('set_profile', profile='Rafa')}">Entrar como Rafa</a>
            </div>
            <p class="small" style="margin-top:12px;">Sem senha no MVP. Só para evitar confusão de perfil.</p>
          </div>
        </div>
      </body>
    </html>
    """
    return html

@app.route("/set_profile/<profile>")
def set_profile(profile: str):
    profile = profile.strip()
    if profile not in ALLOWED_PROFILES:
        return "Perfil inválido", 400
    session["profile"] = profile
    return redirect(url_for("overview"))

@app.route("/perfil")
def perfil():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Perfil</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile, "perfil")}
        <div class="wrap">
          <div class="card">
            <h2>Perfil</h2>
            <p>Trocar perfil.</p>
            <div class="grid2" style="margin-top:14px;">
              <a class="btn btnPrimary btnLucas" style="padding:16px;" href="{url_for('set_profile', profile='Lucas')}">Ir para Lucas</a>
              <a class="btn btnPrimary btnRafa" style="padding:16px;" href="{url_for('set_profile', profile='Rafa')}">Ir para Rafa</a>
            </div>
            <div class="row" style="margin-top:12px;">
              <a class="btn btnGhost" href="{url_for('logout')}">Sair</a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    return html

@app.route("/logout")
def logout():
    session.pop("profile", None)
    return redirect(url_for("home"))

@app.route("/download-template")
def download_template():
    # baixa o template do repo
    folder = os.path.join(os.path.dirname(__file__), "assets")
    filename = "Template_Financas_Casella.xlsx"
    if not os.path.exists(os.path.join(folder, filename)):
        return "Template não encontrado em /assets. Suba o arquivo com esse nome.", 404
    return send_from_directory(folder, filename, as_attachment=True)

@app.route("/overview")
def overview():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.args.get("Ano") or str(now_y)
    selected_month = request.args.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    mode = request.args.get("mode") or "casa"  # casa | individual

    casa = compute_casa(month_ref)
    ind = compute_individual(month_ref, profile)

    def category_details_html(cat, obj):
        # detalhes do que compõe aquela categoria (casa)
        rows = ""
        items = obj.get("items", [])
        for r in items[:500]:
            val = signed_value(r["tipo"], r["valor"])
            rows += f"""
              <tr>
                <td class="small">{_normalize_str(r['dt_text'])}</td>
                <td class="small">{_normalize_str(r['estabelecimento'])}</td>
                <td class="right">{brl(val)}</td>
                <td class="small">{r['tipo']}</td>
                <td class="small">{r['uploaded_by']}</td>
                <td class="small">{r['rateio']}</td>
              </tr>
            """
        if not rows:
            rows = "<tr><td colspan='6' class='small'>Sem itens</td></tr>"
        return f"""
        <details>
          <summary>{cat} <span class="tag" style="margin-left:10px;">Total {brl(obj['total'])}</span></summary>
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Descrição</th>
                <th class="right">Valor</th>
                <th>Tipo</th>
                <th>Pago por</th>
                <th>Rateio</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </details>
        """

    # Toggle
    toggle = f"""
    <div class="row" style="margin-top:10px;">
      <a class="btn {'btnPrimary' if mode=='casa' else 'btnGhost'}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&mode=casa">Casa</a>
      <a class="btn {'btnPrimary' if mode=='individual' else 'btnGhost'}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&mode=individual">Individual</a>
    </div>
    """

    # Casa view
    casa_block = ""
    if mode == "casa":
        cats_details = "".join([category_details_html(cat, obj) for cat, obj in casa["cats_sorted"]])
        settle_line = f"{casa['settlement_text']}: {brl(casa['settlement_value'])}"
        casa_block = f"""
          <div class="card">
            <h3>Resumo da Casa</h3>
            <div class="kpi">
              <div class="box">
                <div class="label">Total Casa</div>
                <div class="value">{brl(casa["total_casa"])}</div>
              </div>
              <div class="box">
                <div class="label">Pago Lucas</div>
                <div class="value">{brl(casa["paid_lucas"])}</div>
                <div class="small">Deveria: {brl(casa["expected_lucas"])}</div>
              </div>
              <div class="box">
                <div class="label">Pago Rafa</div>
                <div class="value">{brl(casa["paid_rafa"])}</div>
                <div class="small">Deveria: {brl(casa["expected_rafa"])}</div>
              </div>
              <div class="box">
                <div class="label">Acerto</div>
                <div class="value">{brl(casa["settlement_value"])}</div>
                <div class="small">{casa["settlement_text"]}</div>
              </div>
            </div>

            <div class="okBox" style="margin-top:12px;">
              <b>Acerto do mês</b><br/>{settle_line}
            </div>
          </div>

          <div class="card">
            <h3>Categorias (clique para ver os itens)</h3>
            {cats_details if cats_details else "<p class='small'>Sem itens de Casa importados para este mês.</p>"}
          </div>
        """

    # Individual view
    individual_block = ""
    if mode == "individual":
        personal_detail_map = {}
        for r in fetch_imported_transactions(month_ref):
            if r["uploaded_by"] == profile and r["dono"] == profile and r["rateio"] == "100_meu":
                cat = r["categoria"] or "Sem categoria"
                personal_detail_map.setdefault(cat, []).append(r)

        def cat_detail(cat, total, rows):
            lines = ""
            for r in rows[:200]:
                lines += f"<tr><td>{_normalize_str(r['dt_text'])}</td><td>{_normalize_str(r['estabelecimento'])}</td><td class='right'>{brl(signed_value(r['tipo'], r['valor']))}</td><td>{_normalize_str(r['tipo'])}</td></tr>"
            if not lines:
                lines = "<tr><td colspan='4' class='small'>Sem itens</td></tr>"
            return f"<details><summary>{cat} <span class='tag' style='margin-left:10px;'>Total {brl(total)}</span></summary><table><thead><tr><th>Data</th><th>Descrição</th><th class='right'>Valor</th><th>Tipo</th></tr></thead><tbody>{lines}</tbody></table></details>"

        def rows_from(items):
            out = ""
            for cat, val in items:
                out += f"<tr><td>{cat}</td><td class='right'>{brl(val)}</td></tr>"
            if not out:
                out = "<tr><td colspan='2' class='small'>Sem dados</td></tr>"
            return out

        individual_block = f"""
          <div class="card">
            <h3>Resumo Individual ({profile})</h3>
            <div class="kpi">
              <div class="box">
                <div class="label">Renda total</div>
                <div class="value">{brl(ind["income"]["total"])}</div>
              </div>
              <div class="box">
                <div class="label">Minha parte da casa</div>
                <div class="value">{brl(ind["house_total"])}</div>
              </div>
              <div class="box">
                <div class="label">Meu pessoal</div>
                <div class="value">{brl(ind["my_personal_total"])}</div>
              </div>
              <div class="box">
                <div class="label">A pagar para o outro</div>
                <div class="value">{brl(ind["payable_total"])}</div>
              </div>
            </div>

            <div class="kpi" style="margin-top:12px;">
              <div class="box">
                <div class="label">Gastos efetivos</div>
                <div class="value">{brl(ind["expenses_effective"])}</div>
                <div class="small">Casa + Pessoal + A pagar</div>
              </div>
              <div class="box">
                <div class="label">Saldo pós pagamentos</div>
                <div class="value">{brl(ind["saldo_pos_pagamentos"])}</div>
              </div>
              <div class="box">
                <div class="label">Investir</div>
                <div class="value">{brl(ind["invested"])}</div>
                <div class="small">{pct(ind["invested_pct"])} da renda</div>
              </div>
              <div class="box">
                <div class="label">Saldo em conta</div>
                <div class="value">{brl(ind["saldo_em_conta"])}</div>
              </div>
            </div>
          </div>

          <div class="card">
            <h3>Minha parte da casa por categoria</h3>
            <table>
              <thead><tr><th>Categoria</th><th class="right">Valor</th></tr></thead>
              <tbody>{rows_from(ind["cats_house"])}</tbody>
            </table>
          </div>

          <div class="card">
            <h3>Meu pessoal por categoria</h3>
            <table>
              <thead><tr><th>Categoria</th><th class="right">Valor</th></tr></thead>
              <tbody>{rows_from(ind["cats_personal"])}</tbody>
            </table>
            <h3 style="margin-top:14px;">Detalhes do pessoal (clique para abrir)</h3>
            {''.join([cat_detail(cat, val, personal_detail_map.get(cat, [])) for cat, val in ind["cats_personal"]]) or "<p class='small'>Sem detalhes.</p>"}
          </div>
        """

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Overview</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile, "overview")}
        <div class="wrap">
          <div class="card">
            <h2>Overview</h2>
            <p>Visão do mês (Casa e Individual).</p>
            {month_selector_block(selected_year, selected_month, url_for('overview'))}
            {toggle}
          </div>

          {casa_block}
          {individual_block}
        </div>
      </body>
    </html>
    """
    return html

@app.route("/entradas")
def entradas():
    # compatibilidade: tela unificada
    return redirect(url_for("transacoes", **request.args))

@app.route("/saidas")
def saidas():
    # compatibilidade: tela unificada
    return redirect(url_for("transacoes", **request.args))

@app.route("/transacoes", methods=["GET", "POST"])
def transacoes():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    lock = get_lock(month_ref, profile)
    action = request.form.get("action", "")

    errors = []
    info = ""
    info_ok = True

    preview_rows = []
    preview_batch_id = ""

    manual_defaults = {
        "Data": "",
        "Estabelecimento": "",
        "Categoria": "",
        "Valor": "",
        "Tipo": "Saida",
        "Dono": profile,
        "Rateio": "100_meu",
        "Observacao": "",
        "Parcela": "",
        "RepetirMeses": "1",
    }

    if request.method == "POST":
        if lock and action not in {"unlock"}:
            errors.append("Mês fechado para este perfil. Clique em 'Editar mês' para liberar.")
        else:
            if action == "lock_month":
                set_lock(month_ref, profile, True)
                info = "Mês fechado para este perfil."

            elif action == "unlock":
                set_lock(month_ref, profile, False)
                info = "Edição liberada para este mês."

            elif action == "delete_batch":
                batch_id = _normalize_str(request.form.get("batch_id"))
                ok, msg = delete_batch(batch_id, profile)
                info = msg
                info_ok = ok
                if not ok:
                    errors.append(msg)

            elif action == "delete_tx":
                tx_id = int(parse_num_br(request.form.get("tx_id")) or 0)
                ok, msg = delete_transaction(tx_id, profile)
                info = msg
                info_ok = ok
                if not ok:
                    errors.append(msg)

            elif action == "update_tx":
                tx_id = int(parse_num_br(request.form.get("tx_id")) or 0)
                valor = parse_value_expression(request.form.get("Valor"))
                tipo = _normalize_str(request.form.get("Tipo"))
                resp = _normalize_str(request.form.get("Dono"))
                rateio = _canon_rateio(_normalize_str(request.form.get("Rateio")))

                if valor <= 0:
                    errors.append("Valor precisa ser maior que 0")
                if tipo not in ALLOWED_TIPO:
                    errors.append("Tipo inválido")
                if resp not in ALLOWED_RESP:
                    errors.append("Responsabilidade inválida")
                if rateio not in {"60_40", "50_50", "100_meu", "100_outro"}:
                    errors.append("Rateio inválido")
                if resp == "Casa" and rateio not in {"60_40", "50_50"}:
                    errors.append("Casa só permite 60/40 ou 50/50")
                if resp in {"Lucas", "Rafa"} and rateio in {"60_40", "50_50"}:
                    errors.append("60/40 ou 50/50 exige Casa")

                if not errors:
                    row = {
                        "Data": _normalize_str(request.form.get("Data")),
                        "Estabelecimento": _normalize_str(request.form.get("Estabelecimento")),
                        "Categoria": _normalize_str(request.form.get("Categoria")),
                        "Valor": valor,
                        "Tipo": tipo,
                        "Dono": resp,
                        "Rateio": rateio,
                        "Observacao": _normalize_str(request.form.get("Observacao")),
                        "Parcela": _normalize_str(request.form.get("Parcela")),
                    }
                    ok, msg = update_transaction(tx_id, profile, row)
                    info = msg
                    info_ok = ok
                    if not ok:
                        errors.append(msg)

            elif action == "manual":
                form_data = dict(manual_defaults)
                for k in form_data.keys():
                    form_data[k] = _normalize_str(request.form.get(k))

                valor = parse_value_expression(form_data["Valor"])
                tipo = _normalize_str(form_data["Tipo"])
                resp = _normalize_str(form_data["Dono"])
                rateio = _canon_rateio(_normalize_str(form_data["Rateio"]))
                repetir_total = int(parse_num_br(form_data["RepetirMeses"]) or 1)
                repetir_total = min(max(repetir_total, 1), 36)

                if valor <= 0:
                    errors.append("Valor precisa ser maior que 0")
                if tipo not in ALLOWED_TIPO:
                    errors.append("Tipo inválido")
                if resp not in ALLOWED_RESP:
                    errors.append("Responsabilidade inválida")
                if rateio not in {"60_40", "50_50", "100_meu", "100_outro"}:
                    errors.append("Rateio inválido")
                if resp == "Casa" and rateio not in {"60_40", "50_50"}:
                    errors.append("Casa só permite 60/40 ou 50/50")
                if resp in {"Lucas", "Rafa"} and rateio in {"60_40", "50_50"}:
                    errors.append("60/40 ou 50/50 exige Casa")

                if not errors:
                    base_row = {
                        "Data": form_data["Data"],
                        "Estabelecimento": form_data["Estabelecimento"],
                        "Categoria": form_data["Categoria"],
                        "Valor": valor,
                        "Tipo": tipo,
                        "Dono": resp,
                        "Rateio": rateio,
                        "Observacao": form_data["Observacao"],
                        "Parcela": form_data["Parcela"],
                    }

                    year = int(selected_year)
                    month = int(selected_month)
                    for i in range(repetir_total):
                        y = year
                        m = month + i
                        while m > 12:
                            m -= 12
                            y += 1
                        create_manual_batch(f"{y}{m:02d}", profile, base_row)

                    info = f"Transação adicionada (repetida por {repetir_total} mês(es))"

            elif action == "excel_preview":
                file = request.files.get("file")
                if not file or file.filename.strip() == "":
                    errors.append("Arquivo obrigatório")
                else:
                    try:
                        raw = file.read()
                        file_hash = compute_file_hash(raw)
                        if is_duplicate_import(month_ref, profile, file_hash):
                            errors.append("Esse mesmo arquivo já foi importado neste mês para este perfil")
                        else:
                            df = read_excel_from_bytes(raw)
                            val_errors, preview_rows = validate_transactions(df)
                            if val_errors:
                                errors.extend(val_errors)
                            else:
                                preview_batch_id = create_preview_batch(month_ref, profile, file.filename, preview_rows, file_hash)
                                info = f"Preview pronto com {len(preview_rows)} linhas"
                    except Exception as e:
                        errors.append(f"Falha ao ler arquivo: {e}")

            elif action == "excel_confirm":
                preview_batch_id = _normalize_str(request.form.get("preview_batch_id"))
                ok, msg = finalize_import(preview_batch_id, profile)
                info = msg
                info_ok = ok
                if not ok:
                    errors.append(msg)

    imported_rows = fetch_imported_transactions(month_ref)
    edit_id = int(parse_num_br(request.args.get("edit_id")) or 0)
    edit_row = fetch_transaction_by_id(edit_id) if edit_id else None

    rows_html = ""
    for r in imported_rows:
        val = signed_value(r["tipo"], r["valor"])
        rows_html += f"""
        <tr>
            <td class="small">{_normalize_str(r["dt_text"])}</td>
            <td class="small">{_normalize_str(r["uploaded_by"])}</td>
            <td class="small">{_normalize_str(r["dono"])}</td>
            <td class="small">{_normalize_str(r["categoria"])}</td>
            <td>{_normalize_str(r["estabelecimento"])}</td>
            <td class="right">{brl(val)}</td>
            <td class="small">{_normalize_str(r["rateio"])}</td>
            <td class="small">{_normalize_str(r["tipo"])}</td>
            <td>
              <a class="btn btnGhost" href="{url_for('transacoes')}?Ano={selected_year}&Mes={selected_month}&edit_id={r['id']}">Editar</a>
              <form method="post" style="display:inline-block; margin-left:6px;" onsubmit="return confirm('Excluir este lançamento?');">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="action" value="delete_tx">
                <input type="hidden" name="tx_id" value="{r['id']}">
                <button class="btn btnDanger" type="submit" {'disabled' if lock else ''}>Excluir</button>
              </form>
            </td>
        </tr>
        """

    if not rows_html:
        rows_html = "<tr><td colspan='9' class='small'>Sem transações importadas</td></tr>"

    cat_datalist = "".join([f"<option value='{c}'></option>" for c in SUGGESTED_CATEGORIES])
    rateio_opts = "".join([f"<option value='{k}'>{k}</option>" for k in ["60/40", "50/50", "100%_Meu", "100%_Outro"]])
    resp_opts = "".join([f"<option value='{r}' {'selected' if r==profile else ''}>{r}</option>" for r in ["Casa", "Lucas", "Rafa"]])
    tipo_opts = "".join([
        f"<option value='Saida'>Despesa</option>",
        f"<option value='Entrada'>Receita</option>",
    ])

    err_block = f"<div class='card'><div class='errorBox'>{'<br/>'.join(errors)}</div></div>" if errors else ""
    info_block = f"<div class='card'><div class='{'okBox' if info_ok else 'errorBox'}'><b>{info}</b></div></div>" if info else ""

    preview_table = ""
    if preview_rows and preview_batch_id:
        table_rows = ""
        for r in preview_rows:
            table_rows += f"<tr><td>{_normalize_str(r['Data'])}</td><td>{_normalize_str(r['Dono'])}</td><td>{_normalize_str(r['Categoria'])}</td><td>{_normalize_str(r['Estabelecimento'])}</td><td class='right'>{brl(signed_value(r['Tipo'], r['Valor']))}</td><td>{r['Rateio']}</td><td>{r['Tipo']}</td></tr>"
        preview_table = f"""
        <div class='card'>
          <h3>Preview do Excel</h3>
          <table><thead><tr><th>Data</th><th>Resp.</th><th>Categoria</th><th>Descrição</th><th class='right'>Valor</th><th>Rateio</th><th>Tipo</th></tr></thead><tbody>{table_rows}</tbody></table>
          <form method='post' style='margin-top:12px;'>
            <input type='hidden' name='Ano' value='{selected_year}'>
            <input type='hidden' name='Mes' value='{selected_month}'>
            <input type='hidden' name='action' value='excel_confirm'>
            <input type='hidden' name='preview_batch_id' value='{preview_batch_id}'>
            <button class='btn btnPrimary' type='submit'>Confirmar importação</button>
          </form>
        </div>
        """

    edit_form = ""
    if edit_row:
        edit_form = f"""
        <div class='card'>
          <h3>Editar lançamento #{edit_row['id']}</h3>
          <form method='post'>
            <input type='hidden' name='Ano' value='{selected_year}'>
            <input type='hidden' name='Mes' value='{selected_month}'>
            <input type='hidden' name='action' value='update_tx'>
            <input type='hidden' name='tx_id' value='{edit_row['id']}'>
            <div class='grid3'>
              <div><label>Data</label><input type='text' name='Data' value='{_normalize_str(edit_row['dt_text'])}'></div>
              <div><label>Descrição</label><input type='text' name='Estabelecimento' value='{_normalize_str(edit_row['estabelecimento'])}'></div>
              <div><label>Categoria</label><input type='text' name='Categoria' value='{_normalize_str(edit_row['categoria'])}'></div>
            </div>
            <div class='grid3'>
              <div><label>Valor</label><input type='text' name='Valor' value='{float(edit_row['valor'] or 0):.2f}'></div>
              <div><label>Tipo</label><select name='Tipo'><option value='Saida' {'selected' if edit_row['tipo']=='Saida' else ''}>Despesa</option><option value='Entrada' {'selected' if edit_row['tipo']=='Entrada' else ''}>Receita</option></select></div>
              <div><label>Responsabilidade</label><select name='Dono'><option value='Casa' {'selected' if edit_row['dono']=='Casa' else ''}>Casa</option><option value='Lucas' {'selected' if edit_row['dono']=='Lucas' else ''}>Lucas</option><option value='Rafa' {'selected' if edit_row['dono']=='Rafa' else ''}>Rafa</option></select></div>
            </div>
            <div class='grid3'>
              <div><label>Rateio</label><select name='Rateio'><option value='60/40' {'selected' if edit_row['rateio']=='60_40' else ''}>60/40</option><option value='50/50' {'selected' if edit_row['rateio']=='50_50' else ''}>50/50</option><option value='100%_Meu' {'selected' if edit_row['rateio']=='100_meu' else ''}>100%_Meu</option><option value='100%_Outro' {'selected' if edit_row['rateio']=='100_outro' else ''}>100%_Outro</option></select></div>
              <div><label>Parcela</label><input type='text' name='Parcela' value='{_normalize_str(edit_row['parcela'])}'></div>
              <div><label>Observação</label><input type='text' name='Observacao' value='{_normalize_str(edit_row['observacao'])}'></div>
            </div>
            <div class='row' style='margin-top:12px;'>
              <button class='btn btnPrimary' type='submit'>Salvar edição</button>
              <a class='btn btnGhost' href='{url_for('transacoes')}?Ano={selected_year}&Mes={selected_month}'>Cancelar</a>
            </div>
          </form>
        </div>
        """

    lock_banner = f"<span class='pill'>Mês {'FECHADO' if lock else 'ABERTO'} para {profile}</span>"
    lock_controls = (
        f"<form method='post'><input type='hidden' name='Ano' value='{selected_year}'><input type='hidden' name='Mes' value='{selected_month}'><input type='hidden' name='action' value='unlock'><button class='btn btnGhost' type='submit'>Editar mês</button></form>"
        if lock else
        f"<form method='post'><input type='hidden' name='Ano' value='{selected_year}'><input type='hidden' name='Mes' value='{selected_month}'><input type='hidden' name='action' value='lock_month'><button class='btn btnPrimary' type='submit'>Fechar mês</button></form>"
    )

    html = f"""
    <!doctype html>
    <html lang='pt-br'>
      <head>
        <meta charset='utf-8'>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>Transações</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile, 'transacoes')}
        <div class='wrap'>
          <div class='card'>
            <div class='row space'>
              <div>
                <h2>Transações</h2>
                <p>Entradas e saídas em um único lugar (Receita/Despesa).</p>
              </div>
              <div class='row'>{lock_banner}{lock_controls}</div>
            </div>
            {month_selector_block(selected_year, selected_month, url_for('transacoes'))}
          </div>

          {err_block}
          {info_block}

          <div class='card'>
            <h3>Upload do mês (Excel)</h3>
            <form id='excelForm' method='post' enctype='multipart/form-data' style='margin-top:12px;'>
              <input type='hidden' name='Ano' value='{selected_year}'>
              <input type='hidden' name='Mes' value='{selected_month}'>
              <input type='hidden' name='action' value='excel_preview'>
              <label>Arquivo Excel</label>
              <input id='fileInput' type='file' name='file' accept='.xlsx,.xls' {'disabled' if lock else ''}/>
            </form>
          </div>

          {preview_table}

          <div class='card'>
            <h3>Adicionar manual</h3>
            <p class='small'>No campo valor você pode usar calculadora simples, ex.: 100+130+250.</p>
            <form method='post'>
              <input type='hidden' name='Ano' value='{selected_year}'>
              <input type='hidden' name='Mes' value='{selected_month}'>
              <input type='hidden' name='action' value='manual'>
              <div class='grid2'>
                <div><label>Data</label><input type='date' name='Data' {'disabled' if lock else ''}/></div>
                <div><label>Valor</label><input type='text' name='Valor' placeholder='ex: 100+130+250' {'disabled' if lock else ''}/></div>
              </div>
              <div class='grid2'>
                <div><label>Descrição</label><input type='text' name='Estabelecimento' {'disabled' if lock else ''}/></div>
                <div><label>Categoria</label><input list='cats' type='text' name='Categoria' {'disabled' if lock else ''}/><datalist id='cats'>{cat_datalist}</datalist></div>
              </div>
              <div class='grid3'>
                <div><label>Tipo</label><select name='Tipo' {'disabled' if lock else ''}>{tipo_opts}</select></div>
                <div><label>Responsabilidade</label><select name='Dono' {'disabled' if lock else ''}>{resp_opts}</select></div>
                <div><label>Rateio</label><select name='Rateio' {'disabled' if lock else ''}>{rateio_opts}</select></div>
              </div>
              <div class='grid3'>
                <div><label>Repetir por quantos meses</label><input type='number' name='RepetirMeses' value='1' min='1' max='36' {'disabled' if lock else ''}/></div>
                <div><label>Parcela</label><input type='text' name='Parcela' {'disabled' if lock else ''}/></div>
                <div><label>Observação</label><input type='text' name='Observacao' {'disabled' if lock else ''}/></div>
              </div>
              <div class='row' style='margin-top:12px;'><button class='btn btnPrimary' type='submit' {'disabled' if lock else ''}>Salvar transação</button></div>
            </form>
          </div>

          {edit_form}

          <div class='card'>
            <h3>Lista do mês</h3>
            <table>
              <thead>
                <tr><th>Data</th><th>Pago por</th><th>Resp.</th><th>Categoria</th><th>Descrição</th><th class='right'>Valor</th><th>Rateio</th><th>Tipo</th><th>Ações</th></tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>
        <script>
          const fileInput = document.getElementById('fileInput');
          const form = document.getElementById('excelForm');
          if (fileInput && form) {{
            fileInput.addEventListener('change', () => {{
              if (fileInput.files && fileInput.files.length > 0) {{
                form.submit();
              }}
            }});
          }}
        </script>
      </body>
    </html>
    """
    return html


# --------- Observação importante sobre assets/.keep ----------
# Não tem problema nenhum o /assets estar "no topo" do repositório.
# É exatamente isso que a gente quer: app.py e a pasta assets no mesmo nível.

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
