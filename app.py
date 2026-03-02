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

# Split padrão
LUCAS_SHARE = 0.40
RAFA_SHARE = 0.60

# Perfis (pagador real sempre é o perfil que fez upload)
ALLOWED_PROFILES = {"Lucas", "Rafa"}

# Tipos
ALLOWED_TIPO = {"Saida", "Entrada"}

# Responsabilidade (antigo "Dono")
ALLOWED_RESP = {"Casa", "Lucas", "Rafa"}

# Rateio
ALLOWED_RATEIO = {"60_40", "50_50", "100_meu", "100_outro"}

# Template no repo (você já colocou em assets)
TEMPLATE_DIR = "assets"
TEMPLATE_FILENAME = "Template__Finanças__Casella.xlsx"
TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", os.path.join(TEMPLATE_DIR, TEMPLATE_FILENAME))

# Colunas aceitas no input
# Observação: aceitamos "Dono" (legado) ou "Responsabilidade" (novo)
REQUIRED_COLUMNS_NEW = [
    "Data",
    "Estabelecimento",
    "Categoria",
    "Valor",
    "Tipo",
    "Responsabilidade",
    "Rateio",
    "Observacao",
    "Parcela",
]

REQUIRED_COLUMNS_OLD = [
    "Data",
    "Estabelecimento",
    "Categoria",
    "Valor",
    "Tipo",
    "Dono",
    "Rateio",
    "Observacao",
    "Parcela",
]

# ---------- UI / CSS ----------
BASE_CSS = """
<style>
  :root{
    --bg0:#f7f8fb;
    --card:#ffffff;
    --text:#101828;
    --muted:#667085;
    --border:#eaecf0;
    --shadow: 0 14px 40px rgba(16,24,40,.08);
    --shadow2: 0 6px 18px rgba(16,24,40,.08);
    --radius: 18px;

    /* Default (Lucas) */
    --p1:#2563eb;
    --p2:#1e40af;
    --pSoft: rgba(37,99,235,.10);
    --pSoft2: rgba(30,64,175,.10);
    --chipBg: rgba(16,24,40,.06);
  }

  body{
    margin:0;
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, "Noto Sans", "Liberation Sans", sans-serif;
    background: radial-gradient(1200px 600px at 15% 10%, rgba(37,99,235,.14), transparent 60%),
                radial-gradient(900px 500px at 85% 0%, rgba(34,197,94,.10), transparent 55%),
                radial-gradient(1200px 800px at 70% 100%, rgba(168,85,247,.10), transparent 60%),
                var(--bg0);
    color: var(--text);
  }

  .wrap{
    max-width: 1200px;
    margin: 0 auto;
    padding: 18px;
  }

  .topbar{
    position: sticky;
    top:0;
    z-index: 30;
    backdrop-filter: blur(10px);
    background: rgba(247,248,251,.78);
    border-bottom: 1px solid var(--border);
  }

  .topbarInner{
    max-width: 1200px;
    margin: 0 auto;
    padding: 12px 18px;
    display:flex;
    gap: 12px;
    align-items:center;
    justify-content: space-between;
  }

  .brand{
    display:flex;
    flex-direction: column;
    gap: 2px;
    min-width: 220px;
  }

  .brand b{
    font-size: 14px;
    letter-spacing: .2px;
  }

  .pill{
    display:inline-flex;
    align-items:center;
    gap: 8px;
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 999px;
    background: var(--chipBg);
    color: var(--text);
    border: 1px solid rgba(16,24,40,.06);
  }

  .nav{
    display:flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .btn{
    display:inline-flex;
    align-items:center;
    justify-content:center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 14px;
    border: 1px solid var(--border);
    background: rgba(255,255,255,.72);
    color: var(--text);
    text-decoration:none;
    font-weight: 800;
    cursor:pointer;
    box-shadow: var(--shadow2);
  }
  .btn:hover{
    transform: translateY(-1px);
    box-shadow: 0 10px 22px rgba(16,24,40,.10);
  }

  .btnPrimary{
    border: 1px solid rgba(255,255,255,.20);
    color: #fff;
    background: linear-gradient(135deg, var(--p1), var(--p2));
    box-shadow: 0 16px 38px rgba(37,99,235,.22);
  }

  .btnSoft{
    border: 1px solid rgba(16,24,40,.08);
    background: linear-gradient(135deg, var(--pSoft), rgba(255,255,255,.70));
  }

  .btnDanger{
    border: 1px solid rgba(255,255,255,.20);
    color:#fff;
    background: linear-gradient(135deg, #d92d20, #b42318);
    box-shadow: 0 14px 34px rgba(217,45,32,.18);
  }

  .card{
    background: rgba(255,255,255,.82);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    margin-top: 14px;
    box-shadow: var(--shadow);
  }

  h1,h2,h3{
    margin: 0 0 10px;
    letter-spacing: -0.2px;
  }

  p{
    margin: 0 0 10px;
    color: var(--muted);
  }

  label{
    font-weight: 900;
    display:block;
    margin-top: 10px;
    margin-bottom: 6px;
    color: var(--text);
  }

  input[type="text"], input[type="number"], input[type="file"], input[type="date"], select, textarea{
    width: 100%;
    padding: 11px 12px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: rgba(255,255,255,.90);
    color: var(--text);
    outline: none;
  }
  input:focus, select:focus, textarea:focus{
    border-color: rgba(37,99,235,.45);
    box-shadow: 0 0 0 4px rgba(37,99,235,.12);
  }

  textarea{
    min-height: 90px;
    resize: vertical;
  }

  .grid2{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid3{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .grid4{ display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; }

  .row{ display:flex; gap: 10px; flex-wrap: wrap; align-items:center; justify-content: space-between; }

  .muted{ color: var(--muted); font-size: 12px; }
  .small{ font-size: 12px; }
  .right{ text-align: right; }
  .mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }

  .okBox{
    border: 1px solid rgba(34,197,94,.25);
    background: rgba(34,197,94,.08);
    padding: 12px;
    border-radius: 14px;
    color: var(--text);
  }

  .errorBox{
    border: 1px solid rgba(217,45,32,.25);
    background: rgba(217,45,32,.08);
    padding: 12px;
    border-radius: 14px;
    color: var(--text);
  }

  table{
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    background: rgba(255,255,255,.65);
    border: 1px solid var(--border);
    border-radius: 14px;
    overflow: hidden;
  }
  th, td{
    border-bottom: 1px solid var(--border);
    padding: 10px 10px;
    text-align: left;
    font-size: 13px;
    vertical-align: top;
  }
  th{
    background: rgba(16,24,40,.04);
    font-weight: 900;
  }
  tr:hover td{
    background: rgba(16,24,40,.02);
  }

  .kpi{
    display:grid;
    grid-template-columns: 1fr 1fr 1fr 1fr;
    gap: 12px;
  }
  .kpi .box{
    background: rgba(255,255,255,.78);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
    box-shadow: var(--shadow2);
  }
  .kpi .label{
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 6px;
    font-weight: 800;
  }
  .kpi .value{
    font-size: 20px;
    font-weight: 1000;
    letter-spacing: -0.4px;
  }

  .tabs{
    display:flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .tab{
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 10px 14px;
    background: rgba(255,255,255,.72);
    font-weight: 900;
    cursor: pointer;
    text-decoration: none;
    color: var(--text);
    box-shadow: var(--shadow2);
  }
  .tabActive{
    background: linear-gradient(135deg, var(--pSoft), rgba(255,255,255,.72));
    border-color: rgba(37,99,235,.35);
  }

  details{
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 10px 12px;
    background: rgba(255,255,255,.72);
    box-shadow: var(--shadow2);
  }
  details summary{
    cursor: pointer;
    font-weight: 1000;
    color: var(--text);
  }

  .loginWrap{
    min-height: calc(100vh - 72px);
    display:flex;
    align-items: center;
  }
  .loginCard{
    width: 100%;
    max-width: 780px;
    margin: 0 auto;
    padding: 20px;
  }
  .bigBtns{
    display:grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 14px;
  }
  .bigBtn{
    display:flex;
    flex-direction: column;
    gap: 8px;
    padding: 18px;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,.24);
    color:#fff;
    text-decoration:none;
    font-weight: 1000;
    box-shadow: 0 18px 44px rgba(16,24,40,.16);
    transition: transform .08s ease;
  }
  .bigBtn:hover{
    transform: translateY(-2px);
  }
  .bigBtn .t{
    font-size: 18px;
    letter-spacing: -0.3px;
  }
  .bigBtn .s{
    font-size: 12px;
    opacity: .92;
    font-weight: 800;
  }
  .lucasGrad{ background: linear-gradient(135deg, #2563eb, #1e40af); }
  .rafaGrad{ background: linear-gradient(135deg, #22c55e, #15803d); }

  @media (max-width: 980px){
    .kpi{ grid-template-columns: 1fr 1fr; }
    .brand{ min-width: auto; }
  }
  @media (max-width: 820px){
    .grid4{ grid-template-columns: 1fr; }
    .grid3{ grid-template-columns: 1fr; }
    .grid2{ grid-template-columns: 1fr; }
    .kpi{ grid-template-columns: 1fr; }
    .bigBtns{ grid-template-columns: 1fr; }
    .topbarInner{ flex-direction: column; align-items: flex-start; }
    .nav{ justify-content: flex-start; }
  }
</style>
"""

def profile_theme_vars(profile: str) -> str:
    # Lucas azul, Rafa verde
    if profile == "Rafa":
        return """
        <style>
          :root{
            --p1:#22c55e;
            --p2:#15803d;
            --pSoft: rgba(34,197,94,.12);
            --pSoft2: rgba(21,128,61,.10);
          }
        </style>
        """
    return """
    <style>
      :root{
        --p1:#2563eb;
        --p2:#1e40af;
        --pSoft: rgba(37,99,235,.12);
        --pSoft2: rgba(30,64,175,.10);
      }
    </style>
    """

# ---------- Helpers ----------
def brl(x: float) -> str:
    if x is None:
        x = 0.0
    s = f"{x:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
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

    conn.commit()
    conn.close()

init_db()

def topbar_html(profile: str):
    if not profile:
        return """
        <div class="topbar">
          <div class="topbarInner">
            <div class="brand">
              <b>Finanças da Casa</b>
              <span class="muted">Selecione um perfil</span>
            </div>
          </div>
        </div>
        """

    nav = f"""
      <div class="nav">
        <a class="btn btnSoft" href="{url_for('overview')}">Overview</a>
        <a class="btn btnSoft" href="{url_for('entrada')}">Entradas</a>
        <a class="btn btnSoft" href="{url_for('saidas')}">Saidas</a>
        <a class="btn btnSoft" href="{url_for('perfil')}">Perfil</a>
      </div>
    """

    return f"""
    <div class="topbar">
      <div class="topbarInner">
        <div class="brand">
          <b>Finanças da Casa</b>
          <span class="pill">Perfil <b>{profile}</b></span>
        </div>
        {nav}
      </div>
    </div>
    """

def signed_value(tipo: str, valor: float) -> float:
    if tipo == "Entrada":
        return -abs(valor)
    return abs(valor)

def share_for(profile: str, rateio: str) -> float:
    if rateio == "50_50":
        return 0.5
    if rateio == "60_40":
        return LUCAS_SHARE if profile == "Lucas" else RAFA_SHARE
    return 0.0

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
    # Sem botão Atualizar, submit automático
    return f"""
      <form id="monthForm" method="get" action="{action_url}">
        <div class="grid2">
          <div>
            <label>Ano</label>
            <select name="Ano" onchange="document.getElementById('monthForm').submit()">{year_options}</select>
          </div>
          <div>
            <label>Mes</label>
            <select name="Mes" onchange="document.getElementById('monthForm').submit()">{month_options}</select>
          </div>
        </div>
        <p class="muted" style="margin-top:10px;">Mes de referencia <b>{month_ref}</b></p>
      </form>
    """

def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()

def _safe_to_str_date(v) -> str:
    # Aceita qualquer formato, inclusive date/datetime
    if pd.isna(v):
        return ""
    if isinstance(v, (dt.date, dt.datetime)):
        return v.strftime("%d/%m/%Y")
    return str(v).strip()

def read_excel_from_bytes(raw: bytes) -> tuple[pd.DataFrame, list[str]]:
    buf = io.BytesIO(raw)
    df = pd.read_excel(buf, engine="openpyxl")

    # Identificar qual set de colunas está vindo
    cols = set([str(c).strip() for c in df.columns])
    use_new = all(c in cols for c in REQUIRED_COLUMNS_NEW)
    use_old = all(c in cols for c in REQUIRED_COLUMNS_OLD)

    if not use_new and not use_old:
        raise ValueError(
            "Colunas faltando. Use as colunas: "
            + ", ".join(REQUIRED_COLUMNS_NEW)
            + " (ou legado: "
            + ", ".join(REQUIRED_COLUMNS_OLD)
            + ")"
        )

    # Normalização e compat
    df = df.copy()
    if use_old and "Responsabilidade" not in df.columns and "Dono" in df.columns:
        df["Responsabilidade"] = df["Dono"]

    # Garante que as colunas esperadas existam
    missing = [c for c in REQUIRED_COLUMNS_NEW if c not in df.columns]
    if missing:
        raise ValueError("Colunas faltando: " + ", ".join(missing))

    for col in ["Estabelecimento", "Categoria", "Tipo", "Responsabilidade", "Rateio", "Observacao", "Parcela"]:
        df[col] = df[col].apply(_normalize_str)

    df["Data"] = df["Data"].apply(_safe_to_str_date)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")

    warnings = []
    # Não validamos Data nem Categoria, apenas suavizamos problemas comuns
    return df, warnings

def validate_transactions(df: pd.DataFrame):
    errors = []
    normalized_rows = []

    for idx, row in df.iterrows():
        line_number = idx + 2

        tipo = row["Tipo"]
        resp = row["Responsabilidade"]
        rateio = row["Rateio"]
        valor = row["Valor"]

        if pd.isna(valor) or float(valor) <= 0:
            errors.append(f"Linha {line_number}: Valor invalido, precisa ser maior que 0")

        if tipo not in ALLOWED_TIPO:
            errors.append(f"Linha {line_number}: Tipo invalido, use Saida ou Entrada")

        if resp not in ALLOWED_RESP:
            errors.append(f"Linha {line_number}: Responsabilidade invalida, use Casa, Lucas ou Rafa")

        if rateio not in ALLOWED_RATEIO:
            errors.append(f"Linha {line_number}: Rateio invalido, use 60_40, 50_50, 100_meu ou 100_outro")

        # Regra: se Responsabilidade é Casa, rateio só pode ser 60_40 ou 50_50
        if resp == "Casa" and rateio not in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: Responsabilidade Casa exige rateio 60_40 ou 50_50")

        # Regra: se Responsabilidade não é Casa, rateio não pode ser 60_40 ou 50_50
        if resp != "Casa" and rateio in {"60_40", "50_50"}:
            errors.append(f"Linha {line_number}: Rateio {rateio} exige Responsabilidade Casa")

        normalized_rows.append(
            {
                "Data": row.get("Data", ""),
                "Estabelecimento": row.get("Estabelecimento", ""),
                "Categoria": row.get("Categoria", ""),
                "Valor": None if pd.isna(valor) else float(valor),
                "Tipo": tipo,
                "Responsabilidade": resp,
                "Rateio": rateio,
                "Observacao": row.get("Observacao", ""),
                "Parcela": row.get("Parcela", ""),
            }
        )

    return errors, normalized_rows

def _insert_import(conn, batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO imports (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source))

def _insert_transaction(conn, batch_id, month_ref, uploaded_by, r, created_at):
    # DB usa coluna "dono" mas aqui significa Responsabilidade
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
        r.get("Responsabilidade", ""),
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

def create_preview_batch(month_ref: str, uploaded_by: str, filename: str, rows: list[dict], file_hash: str) -> str:
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
        return False, "Importacao nao encontrada"

    if imp["uploaded_by"] != profile:
        conn.close()
        return False, "Voce so pode importar batches criados no seu perfil"

    if imp["status"] == "imported":
        conn.close()
        return False, "Esse batch ja foi importado"

    cur.execute("UPDATE imports SET status = 'imported' WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Importacao concluida"

def delete_batch(batch_id: str, profile: str) -> tuple[bool, str]:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM imports WHERE batch_id = ?", (batch_id,))
    imp = cur.fetchone()
    if not imp:
        conn.close()
        return False, "Importacao nao encontrada"

    if imp["uploaded_by"] != profile:
        conn.close()
        return False, "Voce so pode excluir imports feitos no seu perfil"

    cur.execute("DELETE FROM transactions WHERE batch_id = ?", (batch_id,))
    cur.execute("DELETE FROM imports WHERE batch_id = ?", (batch_id,))
    conn.commit()
    conn.close()
    return True, "Importacao excluida"

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
            by_category[cat] = {"total": 0.0, "lucas": 0.0, "rafa": 0.0}
        by_category[cat]["total"] += val

        # Pagador real é quem fez upload do batch (uploaded_by)
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

    settlement_text = "Sem acerto necessario"
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
        "rows": rows,
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

    house_by_cat = {}
    house_total = 0.0

    my_personal_by_cat = {}
    my_personal_total = 0.0

    receivable_total = 0.0
    payable_total = 0.0

    for r in rows:
        val = signed_value(r["tipo"], r["valor"])
        cat = r["categoria"] or "Sem categoria"

        # Casa: Responsabilidade Casa, rateio 60_40 ou 50_50
        if r["dono"] == "Casa" and r["rateio"] in ("60_40", "50_50"):
            sh = share_for(profile, r["rateio"])
            part = val * sh
            house_total += part
            house_by_cat[cat] = house_by_cat.get(cat, 0.0) + part
            continue

        # Pessoal: responsabilidade do próprio profile e import feito por ele com 100_meu
        if r["rateio"] == "100_meu" and r["uploaded_by"] == profile and r["dono"] == profile:
            my_personal_total += val
            my_personal_by_cat[cat] = my_personal_by_cat.get(cat, 0.0) + val
            continue

        # Receber do outro: eu paguei e marquei como 100_outro para responsabilidade do outro
        if r["rateio"] == "100_outro" and r["uploaded_by"] == profile and r["dono"] != "Casa" and r["dono"] != profile:
            receivable_total += val
            continue

        # Pagar para o outro: outro pagou e marcou como 100_outro e responsabilidade é minha
        if r["rateio"] == "100_outro" and r["uploaded_by"] != profile and r["dono"] == profile:
            payable_total += val
            continue

    income = get_income(month_ref, profile)
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
        "rows": rows,
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

def get_transaction(tx_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*, i.source, i.status, i.filename
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.id = ?
      LIMIT 1
    """, (tx_id,))
    row = cur.fetchone()
    conn.close()
    return row

def delete_transaction_any(tx_id: int, profile: str) -> tuple[bool, str]:
    tx = get_transaction(tx_id)
    if not tx:
        return False, "Lancamento nao encontrado"
    if tx["uploaded_by"] != profile:
        return False, "Voce so pode excluir lancamentos do seu perfil"

    batch_id = tx["batch_id"]

    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))

    cur.execute("SELECT COUNT(*) as c FROM transactions WHERE batch_id = ?", (batch_id,))
    c = int(cur.fetchone()["c"])
    if c == 0:
        cur.execute("DELETE FROM imports WHERE batch_id = ?", (batch_id,))

    conn.commit()
    conn.close()
    return True, "Lancamento excluido"

def delete_transactions_bulk(ids: list[int], profile: str) -> tuple[int, list[str]]:
    deleted = 0
    errors = []
    for tx_id in ids:
        ok, msg = delete_transaction_any(tx_id, profile)
        if ok:
            deleted += 1
        else:
            errors.append(f"ID {tx_id}: {msg}")
    return deleted, errors

# ---------- Routes ----------
@app.route("/template")
def template_download():
    # Download do template direto do repo
    if not os.path.exists(TEMPLATE_PATH):
        return "Template nao encontrado no servidor", 404
    return send_from_directory(TEMPLATE_DIR, TEMPLATE_FILENAME, as_attachment=True)

@app.route("/")
def home():
    active_profile = session.get("profile", "")
    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Financas</title>
        {BASE_CSS}
        {profile_theme_vars(active_profile)}
      </head>
      <body>
        {topbar_html(active_profile)}
        <div class="loginWrap">
          <div class="wrap loginCard">
            <div class="card">
              <h1>Financas da Casa</h1>
              <p>Escolha um perfil para entrar.</p>

              <div class="bigBtns">
                <a class="bigBtn lucasGrad" href="{url_for('set_profile', profile='Lucas')}">
                  <div class="t">Entrar como Lucas</div>
                  <div class="s">Cor azul no app</div>
                </a>
                <a class="bigBtn rafaGrad" href="{url_for('set_profile', profile='Rafa')}">
                  <div class="t">Entrar como Rafa</div>
                  <div class="s">Cor verde no app</div>
                </a>
              </div>

              <p class="muted" style="margin-top:14px;">
                Sem senha no MVP, so para evitar confusao de perfil.
              </p>
            </div>
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
        return "Perfil invalido", 400
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
        {profile_theme_vars(profile)}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Perfil</h2>
            <p class="muted">Trocar perfil</p>
            <div class="row" style="justify-content:flex-start;">
              <a class="btn btnPrimary" href="{url_for('set_profile', profile='Lucas')}">Lucas</a>
              <a class="btn btnPrimary" href="{url_for('set_profile', profile='Rafa')}">Rafa</a>
              <a class="btn" href="{url_for('home')}">Sair</a>
            </div>
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

    view = request.args.get("view") or "casa"  # casa ou individual

    casa_data = compute_casa(month_ref)
    ind_data = compute_individual(month_ref, profile)

    # Drilldown por categoria (itens que compõem)
    def drilldown_rows_for_category_casa(cat_name: str):
        out = ""
        for r in casa_data["rows"]:
            cat = (r["categoria"] or "Sem categoria")
            if cat != cat_name:
                continue
            val = signed_value(r["tipo"], r["valor"])
            out += f"""
              <tr>
                <td class="small">{_normalize_str(r["dt_text"])}</td>
                <td class="small">{_normalize_str(r["estabelecimento"])}</td>
                <td class="small">{_normalize_str(r["uploaded_by"])}</td>
                <td class="small">{_normalize_str(r["rateio"])}</td>
                <td class="right">{brl(val)}</td>
              </tr>
            """
        if not out:
            out = "<tr><td colspan='5' class='muted'>Sem itens</td></tr>"
        return out

    def drilldown_rows_for_category_ind(cat_name: str, kind: str):
        # kind: house ou personal
        out = ""
        for r in ind_data["rows"]:
            cat = (r["categoria"] or "Sem categoria")
            if cat != cat_name:
                continue
            val = signed_value(r["tipo"], r["valor"])

            if kind == "house":
                if not (r["dono"] == "Casa" and r["rateio"] in ("60_40", "50_50")):
                    continue
                part = val * share_for(profile, r["rateio"])
                out += f"""
                  <tr>
                    <td class="small">{_normalize_str(r["dt_text"])}</td>
                    <td class="small">{_normalize_str(r["estabelecimento"])}</td>
                    <td class="small">{_normalize_str(r["uploaded_by"])}</td>
                    <td class="small">{_normalize_str(r["rateio"])}</td>
                    <td class="right">{brl(part)}</td>
                  </tr>
                """
            else:
                if not (r["rateio"] == "100_meu" and r["uploaded_by"] == profile and r["dono"] == profile):
                    continue
                out += f"""
                  <tr>
                    <td class="small">{_normalize_str(r["dt_text"])}</td>
                    <td class="small">{_normalize_str(r["estabelecimento"])}</td>
                    <td class="small">{_normalize_str(r["uploaded_by"])}</td>
                    <td class="small">{_normalize_str(r["dono"])}</td>
                    <td class="right">{brl(val)}</td>
                  </tr>
                """
        if not out:
            out = "<tr><td colspan='5' class='muted'>Sem itens</td></tr>"
        return out

    # Render categorias com details para abrir e ver composição
    cats_cards = ""
    if view == "casa":
        for cat, obj in casa_data["cats_sorted"]:
            inner = drilldown_rows_for_category_casa(cat)
            cats_cards += f"""
              <details style="margin-top:10px;">
                <summary>{cat}  <span class="muted">Total {brl(obj["total"])}</span></summary>
                <div style="margin-top:10px;">
                  <table>
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Estabelecimento</th>
                        <th>Pagador</th>
                        <th>Rateio</th>
                        <th class="right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>{inner}</tbody>
                  </table>
                </div>
              </details>
            """
        if not cats_cards:
            cats_cards = "<p class='muted'>Sem dados de Casa para esse mes.</p>"
    else:
        # Individual
        # Minha parte da casa por categoria
        cats_cards += "<h3 style='margin-top:0;'>Minha parte da Casa por categoria</h3>"
        for cat, val in ind_data["cats_house"]:
            inner = drilldown_rows_for_category_ind(cat, "house")
            cats_cards += f"""
              <details style="margin-top:10px;">
                <summary>{cat}  <span class="muted">Total {brl(val)}</span></summary>
                <div style="margin-top:10px;">
                  <table>
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Estabelecimento</th>
                        <th>Pagador</th>
                        <th>Rateio</th>
                        <th class="right">Minha parte</th>
                      </tr>
                    </thead>
                    <tbody>{inner}</tbody>
                  </table>
                </div>
              </details>
            """
        if not ind_data["cats_house"]:
            cats_cards += "<p class='muted'>Sem gastos de Casa para esse mes.</p>"

        cats_cards += "<h3 style='margin-top:16px;'>Meu pessoal por categoria</h3>"
        for cat, val in ind_data["cats_personal"]:
            inner = drilldown_rows_for_category_ind(cat, "personal")
            cats_cards += f"""
              <details style="margin-top:10px;">
                <summary>{cat}  <span class="muted">Total {brl(val)}</span></summary>
                <div style="margin-top:10px;">
                  <table>
                    <thead>
                      <tr>
                        <th>Data</th>
                        <th>Estabelecimento</th>
                        <th>Pagador</th>
                        <th>Responsabilidade</th>
                        <th class="right">Valor</th>
                      </tr>
                    </thead>
                    <tbody>{inner}</tbody>
                  </table>
                </div>
              </details>
            """
        if not ind_data["cats_personal"]:
            cats_cards += "<p class='muted'>Sem gastos pessoais para esse mes.</p>"

    casa_summary = f"""
      <div class="kpi">
        <div class="box">
          <div class="label">Total Casa</div>
          <div class="value">{brl(casa_data["total_casa"])}</div>
        </div>
        <div class="box">
          <div class="label">Pago Lucas</div>
          <div class="value">{brl(casa_data["paid_lucas"])}</div>
          <div class="muted">Deveria {brl(casa_data["expected_lucas"])}</div>
        </div>
        <div class="box">
          <div class="label">Pago Rafa</div>
          <div class="value">{brl(casa_data["paid_rafa"])}</div>
          <div class="muted">Deveria {brl(casa_data["expected_rafa"])}</div>
        </div>
        <div class="box">
          <div class="label">Acerto</div>
          <div class="value">{brl(casa_data["settlement_value"])}</div>
          <div class="muted">{_normalize_str(casa_data["settlement_text"])}</div>
        </div>
      </div>
    """

    individual_summary = f"""
      <div class="kpi">
        <div class="box">
          <div class="label">Renda total</div>
          <div class="value">{brl(ind_data["income"]["total"])}</div>
        </div>
        <div class="box">
          <div class="label">Minha parte da casa</div>
          <div class="value">{brl(ind_data["house_total"])}</div>
        </div>
        <div class="box">
          <div class="label">Meu pessoal</div>
          <div class="value">{brl(ind_data["my_personal_total"])}</div>
        </div>
        <div class="box">
          <div class="label">A pagar para o outro</div>
          <div class="value">{brl(ind_data["payable_total"])}</div>
        </div>
      </div>

      <div class="kpi" style="margin-top:12px;">
        <div class="box">
          <div class="label">Gastos efetivos</div>
          <div class="value">{brl(ind_data["expenses_effective"])}</div>
          <div class="muted">Casa mais Pessoal mais A pagar</div>
        </div>
        <div class="box">
          <div class="label">Saldo pos pagamentos</div>
          <div class="value">{brl(ind_data["saldo_pos_pagamentos"])}</div>
        </div>
        <div class="box">
          <div class="label">Investir</div>
          <div class="value">{brl(ind_data["invested"])}</div>
          <div class="muted">{pct(ind_data["invested_pct"])} da renda do mes</div>
        </div>
        <div class="box">
          <div class="label">Saldo em conta</div>
          <div class="value">{brl(ind_data["saldo_em_conta"])}</div>
        </div>
      </div>
    """

    summary_block = casa_summary if view == "casa" else individual_summary
    tab_casa = "tab tabActive" if view == "casa" else "tab"
    tab_ind = "tab tabActive" if view == "individual" else "tab"

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Overview</title>
        {BASE_CSS}
        {profile_theme_vars(profile)}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Overview</h2>
            <p class="muted">Toggle entre Casa e Individual, com detalhamento por categoria.</p>
            {month_selector_block(selected_year, selected_month, url_for('overview'))}

            <div class="tabs">
              <a class="{tab_casa}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&view=casa">Casa</a>
              <a class="{tab_ind}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&view=individual">Individual</a>
            </div>
          </div>

          <div class="card">
            <h3>Resumo</h3>
            {summary_block}
          </div>

          <div class="card">
            <h3>Categorias</h3>
            <p class="muted">Clique na categoria para abrir e ver os itens que compoem.</p>
            {cats_cards}
          </div>
        </div>
      </body>
    </html>
    """
    return html

@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    # Entradas é a antiga Renda, mantida
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    msg = ""
    if request.method == "POST":
        def num(v):
            try:
                v = str(v).replace(".", "").replace(",", ".")
                return float(v) if v else 0.0
            except:
                return 0.0

        s1 = num(request.form.get("salario_1"))
        s2 = num(request.form.get("salario_2"))
        ex = num(request.form.get("extras"))
        upsert_income(month_ref, profile, s1, s2, ex)
        msg = "Entradas salvas"

    inc = get_income(month_ref, profile)

    msg_block = ""
    if msg:
        msg_block = f"""
          <div class="card">
            <div class="okBox"><b>{msg}</b></div>
          </div>
        """

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Entradas</title>
        {BASE_CSS}
        {profile_theme_vars(profile)}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Entradas</h2>
            {month_selector_block(selected_year, selected_month, url_for('entrada'))}
          </div>

          <div class="card">
            <h3>Valores do mes</h3>
            <form method="post">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">

              <div class="grid3">
                <div>
                  <label>Salario 1</label>
                  <input type="text" name="salario_1" value="{inc['salario_1']:.2f}" />
                </div>
                <div>
                  <label>Salario 2</label>
                  <input type="text" name="salario_2" value="{inc['salario_2']:.2f}" />
                </div>
                <div>
                  <label>Extras</label>
                  <input type="text" name="extras" value="{inc['extras']:.2f}" />
                </div>
              </div>

              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <button class="btn btnPrimary" type="submit">Salvar</button>
              </div>

              <p class="muted" style="margin-top:10px;">Total do mes <b>{brl(inc['total'])}</b></p>
            </form>
          </div>

          {msg_block}
        </div>
      </body>
    </html>
    """
    return html

@app.route("/saidas", methods=["GET", "POST"])
def saidas():
    # Saidas unifica upload e manual, mantendo comportamento do MVP
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

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
        "Responsabilidade": "Casa",
        "Rateio": "60_40",
        "Observacao": "",
        "Parcela": "",
    }

    if request.method == "POST":
        if action == "manual":
            form_data = dict(manual_defaults)
            for k in form_data.keys():
                form_data[k] = _normalize_str(request.form.get(k))

            # Data optional, input date vem yyyy-mm-dd, mas aceitamos qualquer string
            # Valor
            try:
                v = str(form_data["Valor"]).replace(".", "").replace(",", ".")
                valor = float(v) if v else 0.0
            except:
                valor = 0.0

            tipo = form_data["Tipo"]
            resp = form_data["Responsabilidade"]
            rateio = form_data["Rateio"]

            if valor <= 0:
                errors.append("Valor precisa ser maior que 0")
            if tipo not in ALLOWED_TIPO:
                errors.append("Tipo invalido")
            if resp not in ALLOWED_RESP:
                errors.append("Responsabilidade invalida")
            if rateio not in ALLOWED_RATEIO:
                errors.append("Rateio invalido")

            if resp == "Casa" and rateio not in {"60_40", "50_50"}:
                errors.append("Responsabilidade Casa exige rateio 60_40 ou 50_50")
            if resp != "Casa" and rateio in {"60_40", "50_50"}:
                errors.append("Rateio 60_40 ou 50_50 exige Responsabilidade Casa")

            if not errors:
                row = dict(form_data)
                row["Valor"] = valor
                create_manual_batch(month_ref, profile, row)
                info = "Gasto manual adicionado"
                info_ok = True

        elif action == "excel_preview":
            file = request.files.get("file")
            if not file or file.filename.strip() == "":
                errors.append("Arquivo obrigatorio")

            if not errors:
                try:
                    raw = file.read()
                    file_hash = compute_file_hash(raw)

                    if is_duplicate_import(month_ref, profile, file_hash):
                        errors.append("Esse mesmo arquivo ja foi importado nesse mes para esse perfil")
                    else:
                        df, warnings = read_excel_from_bytes(raw)
                        errors, preview_rows = validate_transactions(df)
                        if not errors:
                            preview_batch_id = create_preview_batch(month_ref, profile, file.filename, preview_rows, file_hash)
                            info = "Preview criado. Confirme para importar."
                            info_ok = True
                except Exception as e:
                    errors.append(str(e))

        elif action == "excel_import":
            batch_id = _normalize_str(request.form.get("batch_id"))
            ok, msg = finalize_import(batch_id, profile)
            info = msg
            info_ok = ok

        elif action == "go_lancamentos":
            return redirect(url_for("lancamentos") + f"?Ano={selected_year}&Mes={selected_month}")

    # opções
    tipo_opts = "".join([f"<option value='{t}'>{t}</option>" for t in ["Saida", "Entrada"]])
    resp_opts = "".join([f"<option value='{d}'>{d}</option>" for d in ["Casa", "Lucas", "Rafa"]])
    rateio_opts = "".join([f"<option value='{r}'>{r}</option>" for r in ["60_40", "50_50", "100_meu", "100_outro"]])

    err_block = ""
    if errors:
        items = "".join([f"<li>{e}</li>" for e in errors[:40]])
        err_block = f"""
          <div class="card">
            <h3>Erros</h3>
            <div class="errorBox"><ul>{items}</ul></div>
          </div>
        """

    info_block = ""
    if info:
        klass = "okBox" if info_ok else "errorBox"
        info_block = f"""
          <div class="card">
            <div class="{klass}">
              <b>{info}</b>
              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <a class="btn btnPrimary" href="{url_for('lancamentos')}?Ano={selected_year}&Mes={selected_month}">Ver lancamentos</a>
                <a class="btn" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}">Ir para overview</a>
              </div>
            </div>
          </div>
        """

    preview_table = ""
    if preview_batch_id and preview_rows and not errors:
        head = "".join([f"<th>{c}</th>" for c in ["Data","Estabelecimento","Categoria","Valor","Tipo","Responsabilidade","Rateio","Observacao","Parcela"]])
        body_rows = ""
        for r in preview_rows[:25]:
            tds = "".join([
                f"<td>{'' if r.get(c) is None else r.get(c)}</td>"
                for c in ["Data","Estabelecimento","Categoria","Valor","Tipo","Responsabilidade","Rateio","Observacao","Parcela"]
            ])
            body_rows += f"<tr>{tds}</tr>"

        preview_table = f"""
          <div class="card">
            <h3>Preview do arquivo</h3>
            <p class="muted">Batch <span class="mono">{preview_batch_id[:10]}...</span> mostrando 25 linhas</p>
            <div class="okBox">
              <form method="post">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="action" value="excel_import">
                <input type="hidden" name="batch_id" value="{preview_batch_id}">
                <div class="row" style="justify-content:flex-start;">
                  <button class="btn btnPrimary" type="submit">OK importar</button>
                  <a class="btn" href="{url_for('lancamentos')}?Ano={selected_year}&Mes={selected_month}">Ver lancamentos</a>
                </div>
              </form>
              <p class="muted" style="margin-top:10px;">Se voce nao importar, o batch fica como preview e pode ser excluido em Lancamentos.</p>
            </div>
            <table>
              <thead><tr>{head}</tr></thead>
              <tbody>{body_rows}</tbody>
            </table>
          </div>
        """

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Saidas</title>
        {BASE_CSS}
        {profile_theme_vars(profile)}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Saidas</h2>
            <p class="muted">Upload do mes e lancamentos manuais.</p>
            {month_selector_block(selected_year, selected_month, url_for('saidas'))}

            <div class="row" style="justify-content:flex-start; margin-top:10px;">
              <a class="btn btnPrimary" href="{url_for('template_download')}">Baixar template</a>
              <a class="btn" href="{url_for('lancamentos')}?Ano={selected_year}&Mes={selected_month}">Ver lancamentos</a>
            </div>
          </div>

          {err_block}
          {info_block}

          <div class="card">
            <h3>Upload do mes</h3>
            <p class="muted">Ao escolher o arquivo, o preview abre automaticamente.</p>
            <form id="excelForm" method="post" enctype="multipart/form-data">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <input type="hidden" name="action" value="excel_preview">
              <label>Arquivo Excel</label>
              <input id="fileInput" type="file" name="file" accept=".xlsx,.xls" />
              <p class="muted">Colunas recomendadas incluem Responsabilidade. Data e Categoria sao livres.</p>
            </form>
          </div>

          {preview_table}

          <div class="card">
            <h3>Adicionar gasto manual</h3>
            <p class="muted">Data nao e obrigatoria. Use o calendario se quiser.</p>
            <form method="post">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <input type="hidden" name="action" value="manual">

              <div class="grid2">
                <div>
                  <label>Data</label>
                  <input type="date" name="Data" placeholder="Opcional" />
                  <div class="muted" style="margin-top:6px;">Se preferir, deixe em branco.</div>
                </div>
                <div>
                  <label>Valor</label>
                  <input type="text" name="Valor" placeholder="ex 120,50" />
                </div>
              </div>

              <div class="grid2">
                <div>
                  <label>Estabelecimento</label>
                  <input type="text" name="Estabelecimento" />
                </div>
                <div>
                  <label>Categoria</label>
                  <input type="text" name="Categoria" placeholder="Livre. Ex Lura, Academia, Mercado, Itens de Casa" />
                </div>
              </div>

              <div class="grid3">
                <div>
                  <label>Tipo</label>
                  <select name="Tipo">{tipo_opts}</select>
                </div>
                <div>
                  <label>Responsabilidade</label>
                  <select name="Responsabilidade">{resp_opts}</select>
                </div>
                <div>
                  <label>Rateio</label>
                  <select name="Rateio">{rateio_opts}</select>
                  <div class="muted" style="margin-top:6px;">Se Responsabilidade for Casa, use 60_40 ou 50_50.</div>
                </div>
              </div>

              <div class="grid2">
                <div>
                  <label>Parcela</label>
                  <input type="text" name="Parcela" placeholder="Opcional" />
                </div>
                <div>
                  <label>Observacao</label>
                  <input type="text" name="Observacao" placeholder="Opcional" />
                </div>
              </div>

              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <button class="btn btnPrimary" type="submit">Salvar gasto manual</button>
              </div>
            </form>
          </div>

        </div>

        <script>
          const fileInput = document.getElementById("fileInput");
          const form = document.getElementById("excelForm");
          if (fileInput && form) {{
            fileInput.addEventListener("change", () => {{
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

@app.route("/lancamentos", methods=["GET", "POST"])
def lancamentos():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    filter_profile = request.values.get("filter_profile") or "Todos"

    msg = ""
    msg_ok = True
    errors = []

    if request.method == "POST":
        action = request.form.get("action", "")

        if action == "delete_one":
            try:
                tx_id = int(request.form.get("tx_id"))
            except:
                tx_id = 0
            ok, m = delete_transaction_any(tx_id, profile)
            msg = m
            msg_ok = ok

        elif action == "delete_bulk":
            ids_raw = request.form.getlist("tx_ids")
            ids = []
            for v in ids_raw:
                try:
                    ids.append(int(v))
                except:
                    pass
            deleted, errs = delete_transactions_bulk(ids, profile)
            msg = f"{deleted} lancamentos excluidos"
            msg_ok = True
            if errs:
                errors.extend(errs[:30])

        elif action == "delete_batch":
            batch_id = _normalize_str(request.form.get("batch_id"))
            ok, m = delete_batch(batch_id, profile)
            msg = m
            msg_ok = ok

    rows = fetch_imported_transactions(month_ref)

    if filter_profile in ("Lucas", "Rafa"):
        rows = [r for r in rows if r["uploaded_by"] == filter_profile]

    row_html = ""
    for r in rows[:900]:
        val = signed_value(r["tipo"], r["valor"])
        can_delete = (r["uploaded_by"] == profile)

        delete_btn = ""
        if can_delete:
            delete_btn = f"""
              <form method="post" style="display:inline;">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="filter_profile" value="{filter_profile}">
                <input type="hidden" name="action" value="delete_one">
                <input type="hidden" name="tx_id" value="{r['id']}">
                <button class="btn btnDanger" type="submit">Excluir</button>
              </form>
            """

        checkbox = f"<input type='checkbox' name='tx_ids' value='{r['id']}' {'disabled' if not can_delete else ''} />"
        src = r["source"] or ""
        fname = _normalize_str(r["filename"])

        row_html += f"""
          <tr>
            <td>{checkbox}</td>
            <td class="mono">{r['id']}</td>
            <td>{r['uploaded_by']}</td>
            <td class="small">{src}</td>
            <td class="small">{fname}</td>
            <td class="small">{_normalize_str(r['dt_text'])}</td>
            <td class="small">{_normalize_str(r['estabelecimento'])}</td>
            <td class="small">{_normalize_str(r['categoria'])}</td>
            <td class="right">{brl(val)}</td>
            <td class="small">{r['tipo']}</td>
            <td class="small">{_normalize_str(r['dono'])}</td>
            <td class="small">{r['rateio']}</td>
            <td>{delete_btn}</td>
          </tr>
        """

    if not row_html:
        row_html = "<tr><td colspan='13' class='muted'>Sem lancamentos importados para esse mes</td></tr>"

    # batches
    batches_html = ""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT * FROM imports
      WHERE month_ref = ?
      ORDER BY created_at DESC
    """, (month_ref,))
    batches = cur.fetchall()
    conn.close()

    for b in batches:
        can_del_batch = (b["uploaded_by"] == profile)
        btn = ""
        if can_del_batch:
            btn = f"""
              <form method="post" style="display:inline;">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="filter_profile" value="{filter_profile}">
                <input type="hidden" name="action" value="delete_batch">
                <input type="hidden" name="batch_id" value="{b['batch_id']}">
                <button class="btn btnDanger" type="submit">Excluir batch</button>
              </form>
            """
        batches_html += f"""
          <tr>
            <td class="small">{b['created_at']}</td>
            <td>{b['uploaded_by']}</td>
            <td class="small">{b['status']}</td>
            <td class="small">{_normalize_str(b['source'])}</td>
            <td class="small">{_normalize_str(b['filename'])}</td>
            <td class="right">{b['row_count']}</td>
            <td class="mono">{b['batch_id'][:10]}...</td>
            <td>{btn}</td>
          </tr>
        """

    if not batches_html:
        batches_html = "<tr><td colspan='8' class='muted'>Sem batches</td></tr>"

    msg_block = ""
    if msg:
        klass = "okBox" if msg_ok else "errorBox"
        msg_block = f"""
          <div class="card">
            <div class="{klass}">
              <b>{msg}</b>
            </div>
          </div>
        """

    err_block = ""
    if errors:
        items = "".join([f"<li>{e}</li>" for e in errors[:40]])
        err_block = f"""
          <div class="card">
            <h3>Erros</h3>
            <div class="errorBox"><ul>{items}</ul></div>
          </div>
        """

    filter_opts = ""
    for opt in ["Todos", "Lucas", "Rafa"]:
        sel = "selected" if opt == filter_profile else ""
        filter_opts += f"<option value='{opt}' {sel}>{opt}</option>"

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Lancamentos</title>
        {BASE_CSS}
        {profile_theme_vars(profile)}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">

          <div class="card">
            <h2>Lancamentos</h2>
            <p class="muted">Voce so consegue excluir lancamentos do seu perfil {profile}.</p>
            {month_selector_block(selected_year, selected_month, url_for('lancamentos'))}

            <form method="get" style="margin-top:10px;">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <label>Filtrar por pagador</label>
              <select name="filter_profile" onchange="this.form.submit()">{filter_opts}</select>
              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <a class="btn btnPrimary" href="{url_for('saidas')}?Ano={selected_year}&Mes={selected_month}">Voltar para saidas</a>
                <a class="btn" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}">Ir para overview</a>
              </div>
            </form>
          </div>

          {msg_block}
          {err_block}

          <div class="card">
            <h3>Lista</h3>
            <form method="post" id="bulkForm">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <input type="hidden" name="filter_profile" value="{filter_profile}">
              <input type="hidden" name="action" value="delete_bulk">

              <div class="row" style="justify-content:flex-start; margin-top:8px;">
                <button class="btn btnDanger" type="submit">Excluir selecionados</button>
                <button class="btn" type="button" onclick="selectAll(true)">Selecionar tudo meus</button>
                <button class="btn" type="button" onclick="selectAll(false)">Limpar selecao</button>
              </div>

              <table>
                <thead>
                  <tr>
                    <th></th>
                    <th>ID</th>
                    <th>Pagador</th>
                    <th>Fonte</th>
                    <th>Arquivo</th>
                    <th>Data</th>
                    <th>Estabelecimento</th>
                    <th>Categoria</th>
                    <th class="right">Valor</th>
                    <th>Tipo</th>
                    <th>Responsabilidade</th>
                    <th>Rateio</th>
                    <th>Acao</th>
                  </tr>
                </thead>
                <tbody>
                  {row_html}
                </tbody>
              </table>
            </form>
          </div>

          <div class="card">
            <h3>Batches do mes</h3>
            <p class="muted">Preview tambem aparece aqui. Voce pode excluir batch do seu perfil.</p>
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Pagador</th>
                  <th>Status</th>
                  <th>Fonte</th>
                  <th>Arquivo</th>
                  <th class="right">Linhas</th>
                  <th>Batch</th>
                  <th>Acao</th>
                </tr>
              </thead>
              <tbody>
                {batches_html}
              </tbody>
            </table>
          </div>

        </div>

        <script>
          function selectAll(flag) {{
            const boxes = document.querySelectorAll("input[type='checkbox'][name='tx_ids']");
            boxes.forEach(b => {{
              if (b.disabled) return;
              b.checked = flag;
            }});
          }}
        </script>
      </body>
    </html>
    """
    return html

# Mantém compat com rota antiga, se você tinha links salvos
@app.route("/dashboard")
def dashboard():
    return redirect(url_for("overview"))

@app.route("/renda", methods=["GET", "POST"])
def renda():
    return redirect(url_for("entrada"))

@app.route("/gastos", methods=["GET", "POST"])
def gastos():
    return redirect(url_for("saidas"))

@app.route("/casa", methods=["GET"])
def casa():
    # Mantida por compat, mas agora Overview é o principal
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))
    now_y, now_m = current_year_month()
    selected_year = request.args.get("Ano") or str(now_y)
    selected_month = request.args.get("Mes") or f"{now_m:02d}"
    return redirect(url_for("overview") + f"?Ano={selected_year}&Mes={selected_month}&view=casa")

@app.route("/individual", methods=["GET", "POST"])
def individual():
    # Mantida por compat, mas agora Overview é o principal
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))
    now_y, now_m = current_year_month()
    selected_year = request.args.get("Ano") or str(now_y)
    selected_month = request.args.get("Mes") or f"{now_m:02d}"
    return redirect(url_for("overview") + f"?Ano={selected_year}&Mes={selected_month}&view=individual")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
