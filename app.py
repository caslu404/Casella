from flask import Flask, redirect, url_for, session, request, send_from_directory
import io
import os
import sqlite3
import datetime as dt
import uuid
import hashlib
import json
import pandas as pd

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-later")

# =========================================================
# PATHS BASE
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# Render persistent disk
# =========================================================
# IMPORTANTE:
# No Render, deixe o disk montado em /var/data
# e crie a env var:
# RENDER_DISK_PATH=/var/data
DISK_PATH = os.getenv("RENDER_DISK_PATH", "/var/data")
DB_PATH = os.getenv("DB_PATH", os.path.join(DISK_PATH, "casella.db"))

# =========================================================
# CONFIG GERAL
# =========================================================
LUCAS_SHARE = 0.40
RAFA_SHARE = 0.60

ALLOWED_PROFILES = {"Lucas", "Rafa"}
ALLOWED_TIPO = {"Saida", "Entrada"}
ALLOWED_RESP = {"Casa", "Lucas", "Rafa"}

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

SUGGESTED_CATEGORIES = [
    "Água",
    "Aluguel",
    "Assinaturas e Serviços Digitais",
    "Associados Amazon",
    "Bônus / PLR",
    "Cashback",
    "Combustível",
    "Compras Online Diversas",
    "Compras Pessoais",
    "Condomínio",
    "Contas da Casa",
    "Delivery",
    "Diarista",
    "Estacionamento",
    "Exames",
    "Farmácia",
    "Freelance / Serviços",
    "Gás",
    "Internet",
    "IPVA",
    "Itens Domésticos",
    "Lazer",
    "Licenciamento",
    "Lura",
    "Luz",
    "Manutenção da Casa",
    "Manutenção do Carro",
    "Outros",
    "Pedágio",
    "Pets Areia / Higiene",
    "Pets Brinquedos e Acessórios",
    "Pets Comida",
    "Pets Farmácia",
    "Pets Outros",
    "Pets Pet Shop",
    "Pets Plano de Saúde",
    "Pets Veterinário",
    "Plano de Saúde",
    "Presentes",
    "Psicólogo",
    "Reembolso",
    "Restaurantes",
    "Salário",
    "Seguro do Carro",
    "Streaming",
    "Supermercado",
    "Transporte",
    "Venda de itens",
    "Viagens",
]

# =========================================================
# CSS BASE
# =========================================================
BASE_CSS = """
<style>
  :root{
    --bg1:#07101f;
    --bg2:#101a33;
    --card:rgba(15,23,42,.50);
    --text:#e6edf8;
    --muted:#a4b4cf;
    --border: rgba(148,163,184,.22);
    --shadow: 0 18px 42px rgba(2,8,23,.45);
    --radius: 18px;

    /* cores mais óbvias por perfil */
    --lucas1:#4a1020;   /* vinho escuro */
    --lucas2:#6b1830;

    --rafa1:#26382c;    /* verde militar escuro */
    --rafa2:#395342;

    --neutral1:#2563eb;
    --neutral2:#1d4ed8;
  }

  *{box-sizing:border-box}

  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
    color:var(--text);
    background:
      radial-gradient(1200px 700px at 20% 0%, rgba(37,99,235,.20) 0%, rgba(11,16,32,0) 58%),
      radial-gradient(1000px 640px at 85% 0%, rgba(20,184,166,.10) 0%, rgba(11,16,32,0) 55%),
      linear-gradient(180deg, #070b16 0%, #0d1427 100%);
    min-height:100vh;
  }

  /* bloco principal agora ocupa bem mais da tela */
  .wrap{
    width:min(96vw, 1700px);
    margin:0 auto;
    padding:16px;
  }

  .topbar{
    position:sticky;
    top:0;
    z-index:5;
    backdrop-filter: blur(10px);
    border-bottom:1px solid var(--border);
  }

  /* fundo do header por perfil */
  .topbar.default{
    background: rgba(7,11,22,.72);
  }

  .topbar.lucas{
    background:
      linear-gradient(90deg, rgba(74,16,32,.96) 0%, rgba(58,12,26,.96) 55%, rgba(30,10,16,.96) 100%);
  }

  .topbar.rafa{
    background:
      linear-gradient(90deg, rgba(38,56,44,.96) 0%, rgba(31,47,36,.96) 55%, rgba(20,28,22,.96) 100%);
  }

  .row{display:flex; gap:12px; align-items:center; flex-wrap:wrap;}
  .space{justify-content:space-between;}

  .pill{
    display:inline-flex;
    align-items:center;
    gap:8px;
    padding:6px 10px;
    border-radius:999px;
    border:1px solid var(--border);
    background: rgba(15,23,42,.58);
    font-size:12px;
    color:var(--muted);
  }

  .pillProfileLucas{
    background: rgba(74,16,32,.35);
    border:1px solid rgba(255,255,255,.15);
    color:#f8d7df;
  }

  .pillProfileRafa{
    background: rgba(38,56,44,.35);
    border:1px solid rgba(255,255,255,.15);
    color:#d9eadf;
  }

  .brand{
    display:flex;
    align-items:center;
    gap:10px;
  }

  .dot{
    width:10px; height:10px; border-radius:999px;
    background: linear-gradient(135deg, var(--neutral1), var(--neutral2));
    box-shadow: 0 0 0 4px rgba(37,99,235,.18);
  }

  .dot.lucas{
    background: linear-gradient(135deg, var(--lucas1), var(--lucas2));
    box-shadow: 0 0 0 4px rgba(107,24,48,.22);
  }

  .dot.rafa{
    background: linear-gradient(135deg, var(--rafa1), var(--rafa2));
    box-shadow: 0 0 0 4px rgba(57,83,66,.22);
  }

  .nav{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
  }

  .btn{
    appearance:none;
    border:1px solid var(--border);
    background: rgba(15,23,42,.66);
    color: var(--text);
    padding: 10px 14px;
    border-radius: 14px;
    font-weight: 800;
    font-size: 15px;
    cursor:pointer;
    text-decoration:none;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap:8px;
    transition: transform .06s ease, box-shadow .12s ease, border-color .12s ease;
  }

  .btn:hover{
    border-color: rgba(96,165,250,.52);
    box-shadow: 0 10px 26px rgba(59,130,246,.25);
  }

  .btn:active{transform: translateY(1px);}

  .btnPrimary{
    border:0;
    color:white;
    box-shadow: 0 16px 30px rgba(37,99,235,.34);
    background: linear-gradient(135deg, var(--neutral1), var(--neutral2));
  }

  /* botões principais por perfil */
  .btnLucas{
    border:0;
    background: linear-gradient(135deg, var(--lucas1), var(--lucas2));
    box-shadow: 0 16px 30px rgba(74,16,32,.35);
    color:white;
  }

  .btnRafa{
    border:0;
    background: linear-gradient(135deg, var(--rafa1), var(--rafa2));
    box-shadow: 0 16px 30px rgba(38,56,44,.32);
    color:white;
  }

  .btnGhost{
    background: rgba(15,23,42,.46);
  }

  .btnDanger{
    border:0;
    color:white;
    background: linear-gradient(135deg, #b91c1c, #fb7185);
  }

  .btnIncome{
    border:0;
    color:white;
    background: linear-gradient(135deg,#10b981,#34d399);
  }

  .btnExpense{
    border:0;
    color:white;
    background: linear-gradient(135deg,#ef4444,#f43f5e);
  }

  .card{
    background: rgba(15,23,42,.5);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    box-shadow: var(--shadow);
    margin-top: 14px;
  }

  h1{margin:0 0 10px; font-size:30px; line-height:1.15;}
  h2{margin:0 0 10px; font-size:26px; line-height:1.2;}
  h3{margin:0 0 10px; font-size:22px; line-height:1.2;}
  h4{margin:0 0 8px; font-size:18px; line-height:1.25;}
  p{margin:0 0 10px; color: var(--muted);}

  label{
    font-weight:800;
    display:block;
    margin: 10px 0 6px;
    font-size:14px;
  }

  input[type="text"], input[type="number"], input[type="file"], input[type="date"], select, textarea{
    width:100%;
    padding: 10px 12px;
    border-radius: 14px;
    border:1px solid var(--border);
    background: rgba(2,6,23,.46);
    color: var(--text);
    font-size:14px;
    outline:none;
  }

  /* dropdown aberto com fundo branco e texto preto */
  select option{
    background:#ffffff !important;
    color:#000000 !important;
  }

  select optgroup{
    background:#ffffff !important;
    color:#000000 !important;
  }

  textarea{min-height:90px; resize:vertical;}

  .grid2{display:grid; grid-template-columns: 1fr 1fr; gap:12px;}
  .grid3{display:grid; grid-template-columns: 1fr 1fr 1fr; gap:12px;}
  .grid4{display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:12px;}

  .kpi{display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap:12px;}
  .kpi .box{
    border:1px solid var(--border);
    border-radius: 16px;
    background: rgba(15,23,42,.42);
    padding: 12px;
  }
  .kpi .label{font-size:12px; color: var(--muted); margin-bottom:6px;}
  .kpi .value{font-size:20px; font-weight:900;}

  .right{text-align:right}
  .small{font-size:13px; color: var(--muted);}

  .okBox{
    border:1px solid rgba(22,163,74,.25);
    background: rgba(22,163,74,.16);
    padding: 12px;
    border-radius: 14px;
  }

  .errorBox{
    border:1px solid rgba(185,28,28,.25);
    background: rgba(185,28,28,.18);
    padding: 12px;
    border-radius: 14px;
  }

  table{width:100%; border-collapse: collapse; margin-top:10px;}
  th,td{
    border-bottom:1px solid rgba(148,163,184,.16);
    padding: 10px 8px;
    vertical-align: top;
    font-size:14px;
  }
  th{
    color:#cbd5e1;
    background: rgba(15,23,42,.88);
    position: sticky;
    top: 58px;
    z-index:2;
  }

  details{
    border: 1px solid rgba(15,23,42,.06);
    background: rgba(15,23,42,.42);
    border-radius: 14px;
    padding: 10px 12px;
    margin-top: 10px;
  }

  summary{cursor:pointer; font-weight:900;}

  .tag{
    display:inline-flex;
    gap:8px;
    align-items:center;
    padding:6px 10px;
    border-radius:999px;
    border:1px solid rgba(15,23,42,.08);
    background: rgba(30,41,59,.62);
    font-size:12px;
    color: #cbd5e1;
  }

  .controlBar{display:flex; gap:10px; align-items:center; flex-wrap:wrap;}

  .selectCompact{
    min-width:160px;
    width:auto !important;
    border-radius:12px;
    background: rgba(2,6,23,.56);
  }

  .is-active{
    box-shadow:0 0 0 2px rgba(255,255,255,.25) inset, 0 8px 20px rgba(59,130,246,.28);
  }

  @media (max-width: 900px){
    .grid4,.grid3,.grid2,.kpi{grid-template-columns: 1fr;}
    th{top: 118px;}
    .wrap{width:96vw;}
  }
</style>
"""

# =========================================================
# HELPERS GERAIS
# =========================================================
def brl(x: float) -> str:
    try:
        x = float(x or 0)
    except Exception:
        x = 0.0
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def _normalize_str(x) -> str:
    if x is None:
        return ""
    return str(x).strip()

def current_year_month():
    today = dt.date.today()
    return today.year, today.month

def month_ref_from(year_str: str, month_str: str) -> str:
    return f"{year_str}{month_str}"

def month_name_pt(month_num: str) -> str:
    names = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    try:
        m = int(month_num)
        return names[m - 1]
    except Exception:
        return str(month_num)

def competencia_label(year_str: str, month_str: str) -> str:
    # competência no formato completo, ex: Março/2026
    return f"{month_name_pt(month_str)}/{year_str}"

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _col_exists(conn, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cur.fetchall()]
    return col in cols

def ensure_column(conn, table: str, col: str, ddl: str):
    if not _col_exists(conn, table, col):
        cur = conn.cursor()
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        conn.commit()

# =========================================================
# INIT DB
# =========================================================
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id TEXT NOT NULL,
      month_ref TEXT NOT NULL,
      uploaded_by TEXT NOT NULL,
      dt_text TEXT,
      estabelecimento TEXT,
      categoria TEXT,
      valor REAL NOT NULL DEFAULT 0,
      tipo TEXT NOT NULL,
      dono TEXT NOT NULL,
      rateio TEXT NOT NULL,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS investment_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month_ref TEXT NOT NULL,
      profile TEXT NOT NULL,
      label TEXT NOT NULL,
      amount REAL NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE(month_ref, profile, label)
    )
    """)

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

    # migrações leves
    ensure_column(conn, "imports", "file_hash", "file_hash TEXT")
    ensure_column(conn, "imports", "source", "source TEXT DEFAULT 'excel'")

    conn.commit()
    conn.close()

init_db()

# =========================================================
# HEADER / UI
# =========================================================
def profile_dot(profile: str) -> str:
    if profile == "Lucas":
        return "lucas"
    if profile == "Rafa":
        return "rafa"
    return ""

def topbar_html(profile: str, active: str = "overview"):
    if not profile:
        return """
        <div class="topbar default">
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

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"

    # competência agora sempre em formato completo
    competencia = competencia_label(selected_year, selected_month)

    topbar_class = "lucas" if profile == "Lucas" else "rafa"
    pill_profile_class = "pillProfileLucas" if profile == "Lucas" else "pillProfileRafa"

    nav = f"""
    <div class="nav">
      {nav_btn("Overview", url_for("overview"), "overview")}
      {nav_btn("Transações", url_for("transacoes"), "transacoes")}
      {nav_btn("Investimentos", url_for("investimentos"), "investimentos")}
      {nav_btn("Perfil", url_for("perfil"), "perfil")}
      <span class="pill">Competência: <b>{competencia}</b></span>
    </div>
    """

    return f"""
    <div class="topbar {topbar_class}">
      <div class="wrap">
        <div class="row space">
          <div class="brand">
            <span class="dot {profile_dot(profile)}"></span>
            <div>
              <b>Casella</b><br/>
              <span class="pill {pill_profile_class}">Perfil: <b>{profile}</b></span>
            </div>
          </div>
          {nav}
        </div>
      </div>
    </div>
    """

# =========================================================
# PARSERS / UTIL
# =========================================================
def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

def _canon_col(c: str) -> str:
    s = _normalize_str(c).lower()
    s = (
        s.replace("ç", "c")
         .replace("ã", "a")
         .replace("á", "a")
         .replace("à", "a")
         .replace("â", "a")
         .replace("é", "e")
         .replace("ê", "e")
         .replace("í", "i")
         .replace("ó", "o")
         .replace("ô", "o")
         .replace("õ", "o")
         .replace("ú", "u")
    )
    s = s.replace(" ", "_")
    return s

def _parse_money(v) -> float:
    if v is None:
        return 0.0
    try:
        if pd.isna(v):
            return 0.0
    except Exception:
        pass

    s = str(v).strip()
    s = s.replace("R$", "").replace("\u00a0", " ").strip()
    s = s.replace(" ", "")

    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        if "," in s and "." not in s:
            s = s.replace(",", ".")

    try:
        return float(s)
    except Exception:
        return 0.0

def parse_num_br(v) -> float:
    try:
        v = str(v).replace("R$", "").replace(" ", "").strip()
        if "," in v and "." in v:
            v = v.replace(".", "").replace(",", ".")
        elif "," in v and "." not in v:
            v = v.replace(",", ".")
        return float(v) if v else 0.0
    except Exception:
        return 0.0

def parse_value_expression(v) -> float:
    s = _normalize_str(v)
    if not s:
        return 0.0

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
    except Exception:
        return parse_num_br(s)

def _canon_rateio(x: str) -> str:
    x = _normalize_str(x)
    if x in RATEIO_CANON:
        return RATEIO_CANON[x]
    return x

def _canon_tipo(x: str) -> str:
    t = _normalize_str(x).lower().replace(" ", "")
    t = t.replace("í", "i").replace("á", "a").replace("ã", "a")
    if t == "entrada":
        return "Entrada"
    if t in {"saida", "saída"}:
        return "Saida"
    return _normalize_str(x)

def signed_value(tipo: str, valor: float) -> float:
    v = abs(float(valor or 0))
    return v if tipo == "Entrada" else -v

def share_for(profile: str, rateio: str) -> float:
    if rateio == "60_40":
        return LUCAS_SHARE if profile == "Lucas" else RAFA_SHARE
    if rateio == "50_50":
        return 0.50
    return 1.0

# =========================================================
# EXCEL
# =========================================================
def read_excel_from_bytes(raw: bytes) -> pd.DataFrame:
    buf = io.BytesIO(raw)
    df = pd.read_excel(buf, engine="openpyxl")
    df = df.copy()
    df.columns = [_canon_col(c) for c in df.columns]

    if len(df.columns) >= 8:
        df_short = df.iloc[:, :8].copy()
        df_short.columns = ["Tipo", "Data", "Dono", "Categoria", "Descricao", "Valor", "Rateio", "Observacao"]

        df_short["Data"] = df_short["Data"].apply(lambda v: "" if pd.isna(v) else str(v))
        df_short["Valor"] = df_short["Valor"].apply(_parse_money)
        df_short["Tipo"] = df_short["Tipo"].apply(_canon_tipo)
        df_short["Valor"] = df_short["Valor"].apply(lambda x: abs(float(x or 0)))
        df_short["Estabelecimento"] = df_short["Descricao"].apply(_normalize_str)
        df_short["Parcela"] = ""
        df_short["Dono"] = df_short["Dono"].apply(_normalize_str)
        df_short["Categoria"] = df_short["Categoria"].apply(_normalize_str)
        df_short["Rateio"] = df_short["Rateio"].apply(_normalize_str)

        return df_short

    raise ValueError("Arquivo inválido: precisa ter pelo menos 8 colunas")

def validate_transactions(df: pd.DataFrame):
    errors = []
    normalized_rows = []

    for idx, row in df.iterrows():
        line_number = idx + 2

        tipo = _canon_tipo(row.get("Tipo"))
        resp = _normalize_str(row.get("Dono"))
        rateio_raw = _normalize_str(row.get("Rateio"))
        rateio = _canon_rateio(rateio_raw)

        valor = row.get("Valor")
        try:
            valor_f = float(valor)
        except Exception:
            valor_f = 0.0

        if valor_f <= 0:
            errors.append(f"Linha {line_number}: Valor inválido, precisa ser maior que 0")
        if tipo not in ALLOWED_TIPO:
            errors.append(f"Linha {line_number}: Tipo inválido, use Saida ou Entrada")
        if resp not in ALLOWED_RESP:
            errors.append(f"Linha {line_number}: Responsabilidade inválida, use Casa, Lucas ou Rafa")
        if rateio not in {"60_40", "50_50", "100_meu", "100_outro"}:
            errors.append(f"Linha {line_number}: Rateio inválido")

        if resp == "Casa" and rateio not in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: Responsabilidade Casa só permite 60/40 ou 50/50")
        if resp in {"Lucas", "Rafa"} and rateio in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: 60/40 ou 50/50 exige responsabilidade Casa")

        normalized_rows.append({
            "Data": _normalize_str(row.get("Data")),
            "Estabelecimento": _normalize_str(row.get("Estabelecimento")),
            "Categoria": _normalize_str(row.get("Categoria")),
            "Valor": abs(valor_f),
            "Tipo": tipo,
            "Dono": resp,
            "Rateio": rateio,
            "Observacao": _normalize_str(row.get("Observacao")),
            "Parcela": _normalize_str(row.get("Parcela")),
        })

    return errors, normalized_rows

# =========================================================
# IMPORTS / TRANSAÇÕES
# =========================================================
def is_duplicate_import(month_ref: str, profile: str, file_hash: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT 1
      FROM imports
      WHERE month_ref = ? AND uploaded_by = ? AND file_hash = ?
      LIMIT 1
    """, (month_ref, profile, file_hash))
    row = cur.fetchone()
    conn.close()
    return row is not None

def create_preview_batch(month_ref: str, profile: str, filename: str, rows: list, file_hash: str):
    batch_id = str(uuid.uuid4())
    now = dt.datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
      INSERT INTO imports (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source)
      VALUES (?, ?, ?, ?, ?, 'preview', ?, ?, 'excel')
    """, (batch_id, month_ref, profile, filename, len(rows), now, file_hash))

    for r in rows:
        cur.execute("""
          INSERT INTO transactions (
            batch_id, month_ref, uploaded_by, dt_text, estabelecimento, categoria,
            valor, tipo, dono, rateio, observacao, parcela, created_at
          )
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id, month_ref, profile,
            r.get("Data", ""),
            r.get("Estabelecimento", ""),
            r.get("Categoria", ""),
            float(r.get("Valor") or 0),
            r.get("Tipo", ""),
            r.get("Dono", ""),
            r.get("Rateio", ""),
            r.get("Observacao", ""),
            r.get("Parcela", ""),
            now,
        ))

    conn.commit()
    conn.close()
    return batch_id

def create_manual_batch(month_ref: str, profile: str, row: dict):
    batch_id = str(uuid.uuid4())
    now = dt.datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
      INSERT INTO imports (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source)
      VALUES (?, ?, ?, ?, ?, 'imported', ?, ?, 'manual')
    """, (batch_id, month_ref, profile, "manual", 1, now, None))

    cur.execute("""
      INSERT INTO transactions (
        batch_id, month_ref, uploaded_by, dt_text, estabelecimento, categoria,
        valor, tipo, dono, rateio, observacao, parcela, created_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        batch_id, month_ref, profile,
        row.get("Data", ""),
        row.get("Estabelecimento", ""),
        row.get("Categoria", ""),
        float(row.get("Valor") or 0),
        row.get("Tipo", ""),
        row.get("Dono", ""),
        row.get("Rateio", ""),
        row.get("Observacao", ""),
        row.get("Parcela", ""),
        now,
    ))

    conn.commit()
    conn.close()
    return batch_id

def finalize_import(batch_id: str, profile: str):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT uploaded_by, status FROM imports WHERE batch_id = ?", (batch_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Preview não encontrado"
    if row["uploaded_by"] != profile:
        conn.close()
        return False, "Você só pode confirmar imports do seu perfil"
    if row["status"] != "preview":
        conn.close()
        return False, "Esse batch não está em preview"

    cur.execute("UPDATE imports SET status = 'imported' WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Importação concluída"

def delete_batch(batch_id: str, profile: str):
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

def delete_transaction(tx_id: int, profile: str):
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

def update_transaction(tx_id: int, profile: str, row: dict):
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
      SELECT t.*, i.filename, i.status, i.source
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
      ORDER BY t.id DESC
    """, (month_ref,))
    rows = cur.fetchall()
    conn.close()
    return rows

# =========================================================
# LOCKS
# =========================================================
def get_lock(month_ref: str, profile: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT locked
      FROM month_locks
      WHERE month_ref = ? AND profile = ?
      LIMIT 1
    """, (month_ref, profile))
    row = cur.fetchone()
    conn.close()
    return bool(row["locked"]) if row else False

def set_lock(month_ref: str, profile: str, locked: bool):
    now = dt.datetime.utcnow().isoformat(timespec="seconds") if locked else None
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT id FROM month_locks
      WHERE month_ref = ? AND profile = ?
    """, (month_ref, profile))
    row = cur.fetchone()

    if row:
        cur.execute("""
          UPDATE month_locks
          SET locked = ?, locked_at = ?
          WHERE month_ref = ? AND profile = ?
        """, (1 if locked else 0, now, month_ref, profile))
    else:
        cur.execute("""
          INSERT INTO month_locks (month_ref, profile, locked, locked_at)
          VALUES (?, ?, ?, ?)
        """, (month_ref, profile, 1 if locked else 0, now))
    conn.commit()
    conn.close()

# =========================================================
# INVESTIMENTOS
# =========================================================
def get_investment(month_ref: str, profile: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT amount, note
      FROM investments
      WHERE month_ref = ? AND profile = ?
      LIMIT 1
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

def list_investment_items(month_ref: str, profile: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT label, amount
      FROM investment_items
      WHERE month_ref = ? AND profile = ?
      ORDER BY label ASC
    """, (month_ref, profile))
    rows = cur.fetchall()
    conn.close()
    return rows

def upsert_investment_item(month_ref: str, profile: str, label: str, amount: float):
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT id FROM investment_items
      WHERE month_ref = ? AND profile = ? AND label = ?
    """, (month_ref, profile, label))
    exists = cur.fetchone() is not None

    if exists:
        cur.execute("""
          UPDATE investment_items
          SET amount = ?, updated_at = ?
          WHERE month_ref = ? AND profile = ? AND label = ?
        """, (float(amount or 0), now, month_ref, profile, label))
    else:
        cur.execute("""
          INSERT INTO investment_items (month_ref, profile, label, amount, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?)
        """, (month_ref, profile, label, float(amount or 0), now, now))

    conn.commit()
    conn.close()

def get_total_investments(month_ref: str, profile: str) -> float:
    items = list_investment_items(month_ref, profile)
    items_total = sum([float(r["amount"] or 0) for r in items])
    legacy_total = float(get_investment(month_ref, profile).get("amount", 0) or 0)
    return max(items_total, legacy_total)

# =========================================================
# DATE HELPERS
# =========================================================
def _month_ref_shift(month_ref: str, delta: int) -> str:
    y = int(month_ref[:4])
    m = int(month_ref[4:6])
    m += delta
    while m <= 0:
        y -= 1
        m += 12
    while m > 12:
        y += 1
        m -= 12
    return f"{y}{m:02d}"

def last_n_month_refs(month_ref: str, n: int = 12):
    return [_month_ref_shift(month_ref, -i) for i in range(n - 1, -1, -1)]

def month_label_br(month_ref: str) -> str:
    names = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    y = month_ref[:4]
    m = int(month_ref[4:6])
    return f"{names[m-1]}/{y[2:]}"

# =========================================================
# OVERVIEW COMPUTES
# =========================================================
def compute_category_history(month_ref: str, mode: str, profile: str):
    refs = last_n_month_refs(month_ref, 12)
    cat_map = {}

    for rref in refs:
        rows = fetch_imported_transactions(rref)
        for r in rows:
            raw_signed = signed_value(r["tipo"], r["valor"])
            expense_val = abs(raw_signed) if raw_signed < 0 else 0.0
            cat = r["categoria"] or "Sem categoria"

            if mode == "casa":
                if r["dono"] != "Casa":
                    continue
            else:
                if not (r["uploaded_by"] == profile and r["dono"] == profile):
                    continue

            if cat not in cat_map:
                cat_map[cat] = [0.0 for _ in refs]
            idx = refs.index(rref)
            cat_map[cat][idx] += expense_val

    top = sorted(cat_map.items(), key=lambda x: sum(x[1]), reverse=True)[:8]
    labels = [month_label_br(x) for x in refs]
    return labels, {k: [round(v, 2) for v in arr] for k, arr in top}

def compute_investment_history(month_ref: str, profile: str):
    refs = last_n_month_refs(month_ref, 12)
    cat_map = {}
    totals = []

    for rref in refs:
        rows = list_investment_items(rref, profile)
        month_total = 0.0
        for r in rows:
            cat = _normalize_str(r["label"]) or "Sem categoria"
            val = float(r["amount"] or 0)
            month_total += val
            if cat not in cat_map:
                cat_map[cat] = [0.0 for _ in refs]
            idx = refs.index(rref)
            cat_map[cat][idx] += val
        totals.append(round(month_total, 2))

    top = sorted(cat_map.items(), key=lambda x: sum(x[1]), reverse=True)[:10]
    labels = [month_label_br(x) for x in refs]
    out_map = {k: [round(v, 2) for v in arr] for k, arr in top}

    prev_ref = _month_ref_shift(month_ref, -1)
    cur_total = sum([float(r["amount"] or 0) for r in list_investment_items(month_ref, profile)])
    prev_total = sum([float(r["amount"] or 0) for r in list_investment_items(prev_ref, profile)])
    ctc = cur_total - prev_total
    mom = None
    if prev_total > 0:
        mom = ((cur_total - prev_total) / prev_total) * 100
    elif cur_total > 0:
        mom = 100.0

    return {
        "labels": labels,
        "map": out_map,
        "totals": totals,
        "cur_total": round(cur_total, 2),
        "prev_total": round(prev_total, 2),
        "ctc": round(ctc, 2),
        "mom": mom,
        "prev_ref": prev_ref,
    }

def compute_casa(month_ref: str):
    rows = fetch_imported_transactions(month_ref)
    cat_map = {}
    total_cost = 0.0

    for r in rows:
        if r["dono"] != "Casa":
            continue
        val = signed_value(r["tipo"], r["valor"])
        cat = r["categoria"] or "Sem categoria"
        if cat not in cat_map:
            cat_map[cat] = {"total": 0.0, "items": []}
        cat_map[cat]["total"] += abs(val) if val < 0 else -abs(val)
        cat_map[cat]["items"].append(r)
        total_cost += abs(val) if val < 0 else -abs(val)

    cats_sorted = sorted(cat_map.items(), key=lambda x: abs(x[1]["total"]), reverse=True)
    return {
        "cats_sorted": cats_sorted,
        "total_cost": total_cost,
    }

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

        val = abs(float(r["valor"] or 0))
        cat = r["categoria"] or "Sem categoria"

        if r["tipo"] == "Saida" and r["dono"] == "Casa" and r["rateio"] in ("60_40", "50_50"):
            sh = share_for(profile, r["rateio"])
            part = val * sh
            house_total += part
            house_by_cat[cat] = house_by_cat.get(cat, 0.0) + part
            continue

        if r["tipo"] == "Saida" and r["rateio"] == "100_meu" and r["uploaded_by"] == profile and r["dono"] == profile:
            my_personal_total += val
            my_personal_by_cat[cat] = my_personal_by_cat.get(cat, 0.0) + val
            continue

        if r["tipo"] == "Saida" and r["rateio"] == "100_outro" and r["uploaded_by"] == profile and r["dono"] != "Casa" and r["dono"] != profile:
            receivable_total += val
            continue

        if r["tipo"] == "Saida" and r["rateio"] == "100_outro" and r["uploaded_by"] != profile and r["dono"] == profile:
            payable_total += val
            continue

    income = {"salario_1": 0.0, "salario_2": 0.0, "extras": income_total, "total": income_total}
    inv = get_investment(month_ref, profile)
    invested = get_total_investments(month_ref, profile)

    expenses_effective = house_total + my_personal_total + payable_total
    saldo_pos_pagamentos = income["total"] - expenses_effective
    saldo_em_conta = saldo_pos_pagamentos - invested
    invested_pct = invested / income["total"] if income["total"] > 0 else 0.0

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

# =========================================================
# SELECTORES DE MÊS / ANO
# =========================================================
def year_month_select_html(selected_year: str, selected_month: str):
    this_year = dt.date.today().year
    years = [str(y) for y in range(this_year - 2, this_year + 3)]
    months = [f"{m:02d}" for m in range(1, 13)]

    year_options = "".join([
        f"<option value='{y}' {'selected' if y == selected_year else ''}>{y}</option>"
        for y in years
    ])
    month_options = "".join([
        f"<option value='{m}' {'selected' if m == selected_month else ''}>{month_name_pt(m)}</option>"
        for m in months
    ])
    return year_options, month_options

def month_selector_block(selected_year: str, selected_month: str, action_url: str):
    # AGORA MÊS PRIMEIRO, ANO DEPOIS
    year_options, month_options = year_month_select_html(selected_year, selected_month)
    competencia = competencia_label(selected_year, selected_month)

    return f"""
      <form method="get" action="{action_url}" id="monthForm">
        <div class="grid2">
          <div>
            <label>Mês</label>
            <select name="Mes" onchange="document.getElementById('monthForm').submit()">{month_options}</select>
          </div>
          <div>
            <label>Ano</label>
            <select name="Ano" onchange="document.getElementById('monthForm').submit()">{year_options}</select>
          </div>
        </div>
        <div style="margin-top:10px;">
          <span class="pill">Mês de referência: <b>{competencia}</b></span>
        </div>
      </form>
    """

# =========================================================
# TEMPLATE PATH
# =========================================================
def find_template_file():
    # busca robusta do template no repo
    folder = os.path.join(BASE_DIR, "assets")
    candidates = [
        "Template_Casella.xlsx",
        "template_finanças_caseia.xlsx",
        "Template_Financas_Casella.xlsx",
        "Template__Financas__Casella.xlsx",
    ]
    for c in candidates:
        full = os.path.join(folder, c)
        if os.path.exists(full):
            return folder, c
    return None, None

# =========================================================
# ROUTES
# =========================================================
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
              <a class="btn btnLucas" style="padding:18px 16px; font-size:16px;" href="{url_for('set_profile', profile='Lucas')}">Entrar como Lucas</a>
              <a class="btn btnRafa" style="padding:18px 16px; font-size:16px;" href="{url_for('set_profile', profile='Rafa')}">Entrar como Rafa</a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """
    return html

@app.route("/set-profile/<profile>")
def set_profile(profile):
    if profile not in ALLOWED_PROFILES:
        return redirect(url_for("home"))
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
              <a class="btn btnLucas" style="padding:16px;" href="{url_for('set_profile', profile='Lucas')}">Ir para Lucas</a>
              <a class="btn btnRafa" style="padding:16px;" href="{url_for('set_profile', profile='Rafa')}">Ir para Rafa</a>
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
    # agora busca de forma robusta a partir do diretório real do app
    folder, filename = find_template_file()
    if not folder or not filename:
        return "Template não encontrado em /assets. Suba o arquivo como Template_Casella.xlsx.", 404
    return send_from_directory(folder, filename, as_attachment=True)

@app.route("/investimentos", methods=["GET", "POST"])
def investimentos():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    msg = ""

    categorias_base = [
        "NuCaixinha",
        "NuTurbo",
        "NuTotal",
        "Vested Amazon",
        "Previdência",
        "Ações",
        "CDI",
    ]
    categorias = sorted(categorias_base, key=lambda x: x.lower())

    categoria = _normalize_str(request.values.get("categoria")) or categorias[0]
    if categoria not in categorias:
        categoria = categorias[0]

    current_items = {r["label"]: float(r["amount"] or 0) for r in list_investment_items(month_ref, profile)}
    valor = float(current_items.get(categoria, 0) or 0)

    if request.method == "POST":
        valor = max(parse_num_br(request.form.get("valor", "0")), 0.0)
        categoria = _normalize_str(request.form.get("categoria")) or categorias[0]
        if categoria not in categorias:
            categoria = categorias[0]

        upsert_investment_item(month_ref, profile, categoria, valor)
        current_items[categoria] = valor
        total_now = sum(current_items.values())
        upsert_investment(month_ref, profile, total_now, "Atualização por categoria")
        msg = f"Investimento atualizado para {categoria}."

    current_items = {r["label"]: float(r["amount"] or 0) for r in list_investment_items(month_ref, profile)}
    valor = float(current_items.get(categoria, 0) or 0)

    prev_ref = _month_ref_shift(month_ref, -1)
    prev_items = {r["label"]: float(r["amount"] or 0) for r in list_investment_items(prev_ref, profile)}
    prev_valor = float(prev_items.get(categoria, 0) or 0)
    ctc_valor = valor - prev_valor
    mom_pct_text = "N/A"
    if prev_valor > 0:
        mom_pct_text = f"{((valor - prev_valor) / prev_valor) * 100:.2f}%"
    elif valor > 0:
        mom_pct_text = "100.00%"

    total_now = sum(current_items.values())
    cat_opts = "".join([f"<option value='{c}' {'selected' if c == categoria else ''}>{c}</option>" for c in categorias])

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Investimentos</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile, "investimentos")}
        <div class="wrap">
          <div class="card">
            <h2>Investimentos</h2>
            <p>Atualização mensal por categoria.</p>
            {month_selector_block(selected_year, selected_month, url_for('investimentos'))}
          </div>

          {f"<div class='card'><div class='okBox'><b>{msg}</b></div></div>" if msg else ""}

          <div class="card">
            <h3>Input do mês</h3>
            <form method="post">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <div class="grid2">
                <div>
                  <label>Valor</label>
                  <input type="text" name="valor" value="{valor:.2f}" placeholder="Ex.: 15000,00">
                </div>
                <div>
                  <label>Categoria</label>
                  <select name="categoria">{cat_opts}</select>
                </div>
              </div>
              <div class="row" style="margin-top:12px;">
                <button class="btn btnPrimary" type="submit">Salvar</button>
                <span class="pill">Valor da categoria: <b>{brl(valor)}</b></span>
                <span class="pill">Mês anterior ({competencia_label(prev_ref[:4], prev_ref[4:6])}): <b>{brl(prev_valor)}</b></span>
                <span class="pill">MoM%: <b>{mom_pct_text}</b></span>
                <span class="pill">CtC (R$): <b>{brl(ctc_valor)}</b></span>
                <span class="pill">Total consolidado do mês: <b>{brl(total_now)}</b></span>
              </div>
            </form>
          </div>
        </div>
      </body>
    </html>
    """
    return html

@app.route("/overview")
def overview():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.args.get("Ano") or str(now_y)
    selected_month = request.args.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    mode = request.args.get("mode") or "casa"
    overview_error = ""

    try:
        casa = compute_casa(month_ref)
        ind = compute_individual(month_ref, profile)
        invest_total = get_total_investments(month_ref, profile)
        inv_hist = compute_investment_history(month_ref, profile)
    except Exception as e:
        overview_error = f"Erro ao carregar overview: {e}"
        casa = {"cats_sorted": [], "total_cost": 0.0}
        ind = {"cats_personal": [], "income": {"total": 0.0}, "expenses_effective": 0.0, "saldo_em_conta": 0.0}
        invest_total = 0.0
        inv_hist = {"labels": [], "map": {}, "totals": [], "cur_total": 0.0, "prev_total": 0.0, "ctc": 0.0, "mom": None, "prev_ref": ""}

    def category_details_html(cat, obj):
        rows = ""
        items = obj.get("items", []) if isinstance(obj, dict) else []
        for r in items[:500]:
            val = signed_value(r["tipo"], r["valor"])
            rows += f"""
              <tr>
                <td class="small">{_normalize_str(r['dt_text'])}</td>
                <td class="small">{_normalize_str(r['estabelecimento'])}</td>
                <td class="right">{brl(abs(val))}</td>
                <td class="small">{r['tipo']}</td>
                <td class="small">{r['uploaded_by']}</td>
                <td class="small">{r['rateio']}</td>
              </tr>
            """
        if not rows:
            rows = "<tr><td colspan='6' class='small'>Sem itens</td></tr>"
        total_value = obj["total"] if isinstance(obj, dict) else obj
        return f"""
        <details>
          <summary>{cat} <span class="tag" style="margin-left:10px;">Total {brl(abs(total_value))}</span></summary>
          <table>
            <thead><tr><th>Data</th><th>Descrição</th><th class="right">Valor</th><th>Tipo</th><th>Pago por</th><th>Rateio</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </details>
        """

    if mode == "casa":
        category_items = casa["cats_sorted"]
        try:
            line_labels, line_map = compute_category_history(month_ref, "casa", profile)
        except Exception:
            line_labels, line_map = [], {}
        receitas = 0.0
        despesas = 0.0
        for _, obj in category_items:
            v = float(obj.get("total") or 0)
            if v >= 0:
                despesas += v
            else:
                receitas += abs(v)
        saldo = receitas - despesas
    elif mode == "individual":
        category_items = [(cat, val) for cat, val in ind["cats_personal"]]
        try:
            line_labels, line_map = compute_category_history(month_ref, "individual", profile)
        except Exception:
            line_labels, line_map = [], {}
        receitas = ind["income"]["total"]
        despesas = ind["expenses_effective"]
        saldo = ind["saldo_em_conta"]
    else:
        category_items = sorted(inv_hist["map"].items(), key=lambda x: sum(x[1]), reverse=True)
        line_labels, line_map = inv_hist["labels"], inv_hist["map"]
        receitas = 0.0
        despesas = 0.0
        saldo = inv_hist["cur_total"]

    pie_labels = [cat for cat, _ in category_items[:8]]
    pie_values = []
    for _, val in category_items[:8]:
        if isinstance(val, dict):
            pie_values.append(round(abs(float(val.get("total", 0))), 2))
        elif isinstance(val, (int, float)):
            pie_values.append(round(abs(float(val)), 2))
        else:
            pie_values.append(round(abs(sum([float(x or 0) for x in val])), 2))

    pie_colors = ["#5ea1ff", "#ef4444", "#f59e0b", "#9ca3af", "#34d399", "#a78bfa", "#fb7185", "#22d3ee"]

    toggle = f"""
    <div class="row" style="margin-top:10px;">
      <a class="btn {'btnPrimary' if mode=='casa' else 'btnGhost'}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&mode=casa">Casa</a>
      <a class="btn {'btnPrimary' if mode=='individual' else 'btnGhost'}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&mode=individual">Individual</a>
      <a class="btn {'btnPrimary' if mode=='investimentos' else 'btnGhost'}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&mode=investimentos">Investimentos</a>
    </div>
    """

    if mode == "casa":
        cats_details = "".join([category_details_html(cat, obj) for cat, obj in casa["cats_sorted"]])
        empty_msg = "<p class='small'>Sem itens.</p>"
        detail_block = f"<div class='card'><h3>Categorias Casa</h3>{cats_details if cats_details else empty_msg}</div>"
    elif mode == "individual":
        rows = "".join([f"<tr><td>{cat}</td><td class='right'>{brl(val)}</td></tr>" for cat, val in ind["cats_personal"]]) or "<tr><td colspan='2' class='small'>Sem dados</td></tr>"
        detail_block = f"<div class='card'><h3>Meu pessoal por categoria</h3><table><thead><tr><th>Categoria</th><th class='right'>Valor</th></tr></thead><tbody>{rows}</tbody></table></div>"
    else:
        inv_rows = ""
        for cat, vals in sorted(inv_hist["map"].items(), key=lambda x: sum(x[1]), reverse=True):
            inv_rows += f"<tr><td>{cat}</td><td class='right'>{brl(sum(vals))}</td></tr>"
        if not inv_rows:
            inv_rows = "<tr><td colspan='2' class='small'>Sem dados de investimentos.</td></tr>"
        mom_txt = "N/A" if inv_hist["mom"] is None else f"{inv_hist['mom']:.2f}%"
        prev_comp = competencia_label(inv_hist["prev_ref"][:4], inv_hist["prev_ref"][4:6]) if inv_hist["prev_ref"] else "-"
        detail_block = f"""
          <div class='card'>
            <h3>Investimentos por categoria</h3>
            <table><thead><tr><th>Categoria</th><th class='right'>Acumulado</th></tr></thead><tbody>{inv_rows}</tbody></table>
            <div class='row' style='margin-top:10px;'>
              <span class='pill'>Mês anterior ({prev_comp}): <b>{brl(inv_hist['prev_total'])}</b></span>
              <span class='pill'>MoM%: <b>{mom_txt}</b></span>
              <span class='pill'>CtC (R$): <b>{brl(inv_hist['ctc'])}</b></span>
            </div>
          </div>
        """

    chart_data = json.dumps({
        "mode": mode,
        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "pie_colors": pie_colors,
        "line_labels": line_labels,
        "line_map": line_map,
        "inv_totals": inv_hist["totals"],
    })

    DASHBOARD_CSS = """
    <style>
      .darkBoard{
        background: radial-gradient(1200px 700px at 15% 0%, #1e3a8a55 0%, transparent 50%), linear-gradient(180deg, #0b1226 0%, #121a33 100%);
        color:#e5e7eb;
        border-radius:20px;
        border:1px solid rgba(148,163,184,.25);
        padding:16px;
      }
      .darkBoard h2,.darkBoard h3{color:#f8fafc}
      .darkGrid{display:grid; grid-template-columns:repeat(4,1fr); gap:12px;}
      .darkKpi{
        padding:14px;
        border-radius:16px;
        border:1px solid rgba(148,163,184,.2);
        background:rgba(15,23,42,.55)
      }
      .darkKpi .label{font-size:12px; color:#93c5fd}
      .darkKpi .value{font-size:28px; font-weight:900; color:#fff}
      .panel{
        padding:14px;
        border-radius:16px;
        border:1px solid rgba(148,163,184,.2);
        background:rgba(15,23,42,.45)
      }
      .panelGrid{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px;}
      .catPick{display:flex; gap:8px; flex-wrap:wrap; margin:8px 0 0;}
      .catPick label{
        font-weight:600;
        font-size:12px;
        color:#cbd5e1;
        display:inline-flex;
        align-items:center;
        gap:6px;
        margin:0
      }
      @media (max-width: 900px){
        .darkGrid{grid-template-columns:1fr;}
        .panelGrid{grid-template-columns:1fr;}
      }
    </style>
    """

    if mode == "investimentos":
        receitas_label = "MoM%"
        receitas_value = "N/A" if inv_hist["mom"] is None else f"{inv_hist['mom']:.2f}%"
        despesas_label = "CtC (R$)"
        despesas_value = brl(inv_hist["ctc"])
    else:
        receitas_label = "Receitas"
        receitas_value = brl(receitas)
        despesas_label = "Despesas"
        despesas_value = brl(despesas)

    overview_warning = f"<div class='errorBox' style='margin-top:10px;'><b>{overview_error}</b></div>" if overview_error else ""

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Dashboard</title>
        {BASE_CSS}
        {DASHBOARD_CSS}
      </head>
      <body>
        {topbar_html(profile, "overview")}
        <div class="wrap">
          <div class="card darkBoard">
            <h2>Dashboard</h2>
            <p style="color:#94a3b8;">Visão geral Casa, Individual e Investimentos.</p>
            {overview_warning}
            {month_selector_block(selected_year, selected_month, url_for('overview'))}
            {toggle}

            <div class="darkGrid" style="margin-top:12px;">
              <div class="darkKpi"><div class="label">Saldo atual ({mode.title()})</div><div class="value">{brl(saldo) if mode!='investimentos' else brl(inv_hist['cur_total'])}</div></div>
              <div class="darkKpi"><div class="label">{receitas_label}</div><div class="value">{receitas_value}</div></div>
              <div class="darkKpi"><div class="label">{despesas_label}</div><div class="value">{despesas_value}</div></div>
              <div class="darkKpi"><div class="label">Patrimônio/Investimentos</div><div class="value">{brl(invest_total)}</div></div>
            </div>

            <div class="panelGrid">
              <div class="panel">
                <h3>{'Investimentos por categoria' if mode=='investimentos' else 'Despesas por Categoria'}</h3>
                <canvas id="pieChart" height="220"></canvas>
              </div>
              <div class="panel">
                <h3>{'Investimentos mês a mês' if mode=='investimentos' else 'Evolução mensal por categoria'}</h3>
                <div class="catPick" id="catPick"></div>
                <canvas id="lineChart" height="220"></canvas>
              </div>
            </div>
          </div>

          {detail_block}
        </div>

        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
          const payload = {chart_data};
          const pieCtx = document.getElementById('pieChart');
          if (pieCtx) {{
            new Chart(pieCtx, {{
              type: 'doughnut',
              data: {{ labels: payload.pie_labels, datasets: [{{ data: payload.pie_values, backgroundColor: payload.pie_colors }}] }},
              options: {{ plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#e5e7eb' }} }} }} }}
            }});
          }}

          const allCats = Object.keys(payload.line_map || {{}});
          const pick = document.getElementById('catPick');
          const colors = ['#5ea1ff','#ef4444','#f59e0b','#34d399','#a78bfa','#fb7185','#22d3ee','#9ca3af','#10b981','#f97316'];
          let selected = allCats.slice(0, Math.min(3, allCats.length));

          function buildSelectors() {{
            if (!pick) return;
            pick.innerHTML = '';
            allCats.forEach((cat, idx) => {{
              const id = 'cat_' + idx;
              const checked = selected.includes(cat) ? 'checked' : '';
              pick.insertAdjacentHTML('beforeend', `<label><input type="checkbox" id="${{id}}" data-cat="${{cat}}" ${{checked}}> ${{cat}}</label>`);
            }});
            pick.querySelectorAll('input[type="checkbox"]').forEach(el => {{
              el.addEventListener('change', () => {{
                const c = el.dataset.cat;
                if (el.checked) {{
                  if (!selected.includes(c)) selected.push(c);
                }} else {{
                  selected = selected.filter(x => x !== c);
                }}
                drawMain();
              }});
            }});
          }}

          let mainChart = null;
          function drawMain() {{
            const ctx = document.getElementById('lineChart');
            if (!ctx) return;
            if (mainChart) mainChart.destroy();

            const datasets = selected.map((cat, idx) => ({{
              label: cat,
              data: payload.line_map[cat] || [],
              borderColor: colors[idx % colors.length],
              backgroundColor: colors[idx % colors.length] + '55',
              tension: 0.25,
              fill: false,
              stack: 'inv'
            }}));

            const isInv = payload.mode === 'investimentos';
            mainChart = new Chart(ctx, {{
              type: isInv ? 'bar' : 'line',
              data: {{ labels: payload.line_labels, datasets }},
              options: {{
                responsive: true,
                scales: {{
                  x: {{ ticks: {{ color: '#cbd5e1' }}, stacked: isInv }},
                  y: {{ ticks: {{ color: '#cbd5e1' }}, stacked: isInv }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#e5e7eb' }} }} }}
              }}
            }});
          }}

          buildSelectors();
          drawMain();
        </script>
      </body>
    </html>
    """
    return html

@app.route("/entradas")
def entradas():
    return redirect(url_for("transacoes", **request.args))

@app.route("/saidas")
def saidas():
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
    open_panel = _normalize_str(request.values.get("panel")) or ""

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
                open_panel = "manual"
                valor = parse_value_expression(request.form.get("Valor"))
                tipo = _normalize_str(request.form.get("Tipo"))
                resp = _normalize_str(request.form.get("Dono"))
                rateio = _canon_rateio(_normalize_str(request.form.get("Rateio")))
                repetir_total = int(parse_num_br(request.form.get("RepetirMeses", "1")) or 1)
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
                open_panel = "upload"
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
                open_panel = "upload"
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
            <td class="small">{'Receita' if _normalize_str(r['tipo']) == 'Entrada' else 'Despesa'}</td>
            <td class="small">{_normalize_str(r["dt_text"])}</td>
            <td class="small">{_normalize_str(r["uploaded_by"])}</td>
            <td class="small">{_normalize_str(r["dono"])}</td>
            <td class="small">{_normalize_str(r["categoria"])}</td>
            <td>{_normalize_str(r["estabelecimento"])}</td>
            <td class="right">{brl(abs(val))}</td>
            <td class="small">{_normalize_str(r["rateio"])}</td>
            <td class="small">{_normalize_str(r["observacao"])}</td>
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
        rows_html = "<tr><td colspan='10' class='small'>Sem transações importadas</td></tr>"

    cat_datalist = "".join([f"<option value='{c}'></option>" for c in SUGGESTED_CATEGORIES])
    rateio_opts = "".join([f"<option value='{k}'>{k}</option>" for k in ["60/40", "50/50", "100%_Meu", "100%_Outro"]])
    resp_opts = "".join([f"<option value='{r}' {'selected' if r == profile else ''}>{r}</option>" for r in ["Casa", "Lucas", "Rafa"]])
    year_options, month_options = year_month_select_html(selected_year, selected_month)
    selected_competencia = competencia_label(selected_year, selected_month)

    err_block = f"<div class='card'><div class='errorBox'>{'<br/>'.join(errors)}</div></div>" if errors else ""
    info_block = f"<div class='card'><div class='{'okBox' if info_ok else 'errorBox'}'><b>{info}</b></div></div>" if info else ""

    preview_table = ""
    if preview_rows and preview_batch_id:
        table_rows = ""
        for r in preview_rows:
            table_rows += f"<tr><td>{_normalize_str(r['Data'])}</td><td>{_normalize_str(r['Dono'])}</td><td>{_normalize_str(r['Categoria'])}</td><td>{_normalize_str(r['Estabelecimento'])}</td><td class='right'>{brl(abs(signed_value(r['Tipo'], r['Valor'])))}</td><td>{r['Rateio']}</td><td>{r['Tipo']}</td></tr>"
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
                <p>Controle do mês e ações rápidas para input manual ou Excel.</p>
              </div>
              <div>
                <form method='get' action='{url_for('transacoes')}' id='monthFormTx' class='controlBar' style='justify-content:flex-end;'>
                  <!-- AGORA MÊS PRIMEIRO -->
                  <select class='selectCompact' name='Mes' onchange="document.getElementById('monthFormTx').submit()">{month_options}</select>
                  <select class='selectCompact' name='Ano' onchange="document.getElementById('monthFormTx').submit()">{year_options}</select>
                </form>
                <div class='row' style='justify-content:flex-end; margin-top:8px;'>
                  {lock_controls}
                </div>
              </div>
            </div>
            <div class='row' style='margin-top:8px;'>{lock_banner}<span class='pill'>Referência: <b>{selected_competencia}</b></span></div>
          </div>

          {err_block}
          {info_block}

          <div class='card'>
            <h3>Inputs</h3>
            <p class='small'>Clique no botão para abrir o input desejado.</p>

            <div class='row' style='margin:10px 0 12px;'>
              <button id='btnReceitaTop' class='btn btnIncome' type='button' {'disabled' if lock else ''}>+ RECEITA</button>
              <button id='btnDespesaTop' class='btn btnExpense' type='button' {'disabled' if lock else ''}>- DESPESA</button>
              <button id='btnUploadTop' class='btn btnGhost' type='button' {'disabled' if lock else ''}>UPLOAD</button>
              <a class='btn btnGhost' href='{url_for('download_template')}'>DOWNLOAD TEMPLATE</a>
            </div>

            <div id='manualPanel' style='display:none;'>
              <h4 style='margin:0 0 8px;'>Input manual</h4>
              <form method='post'>
                  <input type='hidden' name='Ano' value='{selected_year}'>
                  <input type='hidden' name='Mes' value='{selected_month}'>
                  <input type='hidden' name='action' value='manual'>
                  <input id='tipoManual' type='hidden' name='Tipo' value='Saida'>

                  <div class='grid2'>
                    <div><label>Descrição</label><input type='text' name='Estabelecimento' {'disabled' if lock else ''}/></div>
                    <div><label>Categoria</label><input list='cats' type='text' name='Categoria' {'disabled' if lock else ''}/><datalist id='cats'>{cat_datalist}</datalist></div>
                  </div>

                  <div class='grid2'>
                    <div><label>Valor</label><input type='text' name='Valor' placeholder='ex: 100+130+250' {'disabled' if lock else ''}/></div>
                    <div><label>Responsabilidade</label><select name='Dono' {'disabled' if lock else ''}>{resp_opts}</select></div>
                  </div>

                  <div class='grid2'>
                    <div><label>Rateio</label><select name='Rateio' {'disabled' if lock else ''}>{rateio_opts}</select></div>
                    <div><label>Observação</label><input type='text' name='Observacao' {'disabled' if lock else ''}/></div>
                  </div>

                  <div class='grid3'>
                    <div><label>Repetir por quantos meses</label><input type='number' name='RepetirMeses' value='1' min='1' max='36' {'disabled' if lock else ''}/></div>
                    <div><label>Parcela</label><input type='text' name='Parcela' {'disabled' if lock else ''}/></div>
                    <div><label>Data (opcional)</label><input type='date' name='Data' {'disabled' if lock else ''}/></div>
                  </div>

                  <div class='row' style='margin-top:12px;'><button class='btn btnPrimary' type='submit' {'disabled' if lock else ''}>Salvar transação</button></div>
              </form>
            </div>

            <div id='uploadPanel' style='display:none; margin-top:8px;'>
              <h4 style='margin:0 0 8px;'>Upload por Excel</h4>
              <form id='excelForm' method='post' enctype='multipart/form-data'>
                  <input type='hidden' name='Ano' value='{selected_year}'>
                  <input type='hidden' name='Mes' value='{selected_month}'>
                  <input type='hidden' name='action' value='excel_preview'>
                  <input id='fileInput' type='file' name='file' accept='.xlsx,.xls' style='display:none;' {'disabled' if lock else ''}/>
                  <div id='dropZone' class='card' style='margin-top:0; border-style:dashed; text-align:center; padding:28px; cursor:pointer;'>
                    <b>Arraste o Excel aqui</b><br/>
                    <span class='small'>ou clique para selecionar o arquivo</span>
                  </div>
              </form>
            </div>
          </div>

          {preview_table}
          {edit_form}

          <div class='card'>
            <h3>Lista do mês</h3>
            <table>
              <thead>
                <tr><th>Tipo</th><th>Data</th><th>Pago por</th><th>Responsabilidade</th><th>Categoria</th><th>Descrição</th><th class='right'>Valor</th><th>Rateio</th><th>Observações</th><th>Ações</th></tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table>
          </div>
        </div>

        <script>
          const fileInput = document.getElementById('fileInput');
          const form = document.getElementById('excelForm');
          const dropZone = document.getElementById('dropZone');
          const manualPanel = document.getElementById('manualPanel');
          const uploadPanel = document.getElementById('uploadPanel');

          function openPanel(panel) {{
            if (manualPanel) manualPanel.style.display = panel === 'manual' ? 'block' : 'none';
            if (uploadPanel) uploadPanel.style.display = panel === 'upload' ? 'block' : 'none';
          }}

          if (fileInput && form) {{
            fileInput.addEventListener('change', () => {{
              if (fileInput.files && fileInput.files.length > 0) {{
                form.submit();
              }}
            }});
          }}

          if (dropZone && fileInput) {{
            dropZone.addEventListener('click', () => fileInput.click());
            dropZone.addEventListener('dragover', (e) => {{ e.preventDefault(); dropZone.style.borderColor = '#60a5fa'; }});
            dropZone.addEventListener('dragleave', () => {{ dropZone.style.borderColor = ''; }});
            dropZone.addEventListener('drop', (e) => {{
              e.preventDefault();
              dropZone.style.borderColor = '';
              if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {{
                fileInput.files = e.dataTransfer.files;
                form.submit();
              }}
            }});
          }}

          const tipoManual = document.getElementById('tipoManual');
          const btnDespesa = document.getElementById('btnDespesaTop');
          const btnReceita = document.getElementById('btnReceitaTop');
          const btnUpload = document.getElementById('btnUploadTop');

          function setTipoManual(tipo) {{
            if (!tipoManual || !btnDespesa || !btnReceita) return;
            tipoManual.value = tipo;
            if (tipo === 'Entrada') {{
              btnReceita.classList.add('is-active');
              btnDespesa.classList.remove('is-active');
            }} else {{
              btnDespesa.classList.add('is-active');
              btnReceita.classList.remove('is-active');
            }}
          }}

          if (btnDespesa) btnDespesa.addEventListener('click', () => {{ setTipoManual('Saida'); openPanel('manual'); }});
          if (btnReceita) btnReceita.addEventListener('click', () => {{ setTipoManual('Entrada'); openPanel('manual'); }});
          if (btnUpload) btnUpload.addEventListener('click', () => openPanel('upload'));

          const startPanel = '{open_panel if open_panel in ("manual", "upload") else ("upload" if preview_rows else "")}';
          if (startPanel) openPanel(startPanel);
          setTipoManual('Saida');
        </script>
      </body>
    </html>
    """
    return html

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
