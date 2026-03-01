from flask import Flask, redirect, url_for, session, request, send_file, jsonify
import io
import os
import sqlite3
import datetime as dt
import uuid
import hashlib
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-secret-change-later")

DB_PATH = os.environ.get("DB_PATH", "data.db")

LUCAS_SHARE = 0.40
RAFA_SHARE = 0.60

ALLOWED_PROFILES = {"Lucas", "Rafa"}

# Template rules
ALLOWED_PAGADOR = {"Lucas", "Rafa", "Casa"}
ALLOWED_CATEGORIAS = {
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
    "Transporte",
    "Viagens e Lazer",
    "Outros",
}
ALLOWED_RATEIO_DISPLAY = {"60/40", "50/50", "100%_Meu", "100%_Outro"}

RATEIO_DISPLAY_TO_KEY = {
    "60/40": "60_40",
    "50/50": "50_50",
    "100%_Meu": "100_meu",
    "100%_Outro": "100_outro",
}
RATEIO_KEY_TO_DISPLAY = {v: k for k, v in RATEIO_DISPLAY_TO_KEY.items()}

ALLOWED_TIPO = {"Saida", "Entrada"}  # manter
ALLOWED_DONO = {"Casa", "Lucas", "Rafa"}  # manter

# Arquivo do template dentro do repo (você vai colocar ele aí)
TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", os.path.join("assets", "Template__Finanças__Casella.xlsx"))

# Seed de fixos e pendentes
FIXOS_SEED = [
    # descricao, valor, pagador_label, rateio_display, categoria
    ("Aluguel", 2541.00, "Rafa", "60/40", "Contas da Casa"),
    ("Condomínio", 1374.42, "Lucas", "60/40", "Contas da Casa"),
    ("Internet", 115.00, "Lucas", "60/40", "Contas da Casa"),
    ("Estacionamento Amazon", 75.00, "Rafa", "60/40", "Contas da Casa"),
]

PENDENTES_SEED = [
    # descricao, categoria
    ("Luz", "Contas da Casa"),
    ("Gás", "Contas da Casa"),
    ("Empregada", "Contas da Casa"),
]

BASE_CSS = """
<style>
  :root{
    --bg: #f6f7fb;
    --card: rgba(255,255,255,.95);
    --text: #0f172a;
    --muted: rgba(15,23,42,.62);
    --line: rgba(15,23,42,.10);

    --accent: #1d4ed8;
    --accent2: #22c55e;
    --danger: #ef4444;
    --warn: #f59e0b;

    --shadow: 0 12px 30px rgba(2,6,23,.12);
    --radius: 18px;
  }

  body{
    font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
    margin:0;
    color: var(--text);
    background:
      radial-gradient(1100px 500px at 10% 10%, rgba(29,78,216,.16), transparent 60%),
      radial-gradient(900px 500px at 90% 15%, rgba(34,197,94,.14), transparent 60%),
      #f6f7fb;
    min-height:100vh;
  }

  .topbar{
    position: sticky;
    top: 0;
    z-index: 50;
    background: rgba(255,255,255,.78);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(15,23,42,.08);
  }

  .wrap { max-width: 1200px; margin: 0 auto; padding: 18px; }

  .inner{
    max-width:1200px;
    margin:0 auto;
    padding: 14px 18px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap: 12px;
  }

  .brand{ display:flex; align-items:center; gap: 12px; color: rgba(15,23,42,.92); }
  .logo{
    width: 38px;
    height: 38px;
    border-radius: 14px;
    background: linear-gradient(135deg, rgba(29,78,216,.25), rgba(34,197,94,.22));
    border: 1px solid rgba(15,23,42,.08);
    box-shadow: 0 10px 24px rgba(2,6,23,.10);
  }

  .row { display:flex; gap: 10px; flex-wrap: wrap; align-items:center; justify-content: space-between; }
  .nav { display: inline-flex; gap: 8px; flex-wrap: wrap; }

  .pill {
    display:inline-flex;
    gap: 8px;
    align-items:center;
    padding: 7px 12px;
    border-radius: 999px;
    border: 1px solid rgba(15,23,42,.10);
    background: rgba(255,255,255,.70);
    font-size: 12px;
    color: rgba(15,23,42,.82);
  }
  .pillWarn{ border-color: rgba(245,158,11,.28); background: rgba(245,158,11,.10); }
  .pillOk{ border-color: rgba(34,197,94,.24); background: rgba(34,197,94,.10); }

  .btn {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    padding: 10px 12px;
    border-radius: 14px;
    text-decoration: none;
    border: 1px solid rgba(15,23,42,.12);
    background: rgba(255,255,255,.75);
    color: rgba(15,23,42,.92);
    font-weight: 800;
    cursor: pointer;
    user-select:none;
  }
  .btn:hover{ border-color: rgba(15,23,42,.18); }
  .btnPrimary{
    background: linear-gradient(135deg, var(--accent), #2563eb);
    border-color: rgba(29,78,216,.15);
    color: white;
  }
  .btnGreen{
    background: linear-gradient(135deg, var(--accent2), #34d399);
    border-color: rgba(34,197,94,.14);
    color: #052e16;
  }
  .btnDanger{
    background: linear-gradient(135deg, var(--danger), #fb7185);
    border-color: rgba(239,68,68,.20);
    color: white;
  }
  .btnWarn{
    background: linear-gradient(135deg, var(--warn), #fbbf24);
    border-color: rgba(245,158,11,.20);
    color: #1f1300;
  }

  .card{
    background: var(--card);
    border: 1px solid rgba(15,23,42,.08);
    border-radius: var(--radius);
    padding: 18px;
    margin-top: 14px;
    box-shadow: var(--shadow);
  }

  h1, h2, h3 { margin: 0 0 10px; }
  p { margin: 0 0 10px; color: rgba(15,23,42,.78); }

  label { font-weight: 800; display:block; margin-top: 10px; margin-bottom: 6px; color: rgba(15,23,42,.85); }

  input[type="text"], input[type="number"], input[type="file"], select, textarea{
    width: 100%;
    padding: 10px 12px;
    border: 1px solid rgba(15,23,42,.12);
    border-radius: 14px;
    background: rgba(255,255,255,.82);
    color: rgba(15,23,42,.92);
    outline: none;
  }
  textarea{ min-height: 90px; resize: vertical; }

  .grid2{ display:grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .grid3{ display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }
  .grid4{ display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; }

  .muted{ color: rgba(15,23,42,.58); font-size: 12px; }
  .mono{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
  .right{ text-align:right; }
  .small{ font-size: 12px; }

  .errorBox{
    border: 1px solid rgba(239,68,68,.25);
    background: rgba(239,68,68,.08);
    padding: 12px;
    border-radius: 14px;
  }
  .okBox{
    border: 1px solid rgba(34,197,94,.22);
    background: rgba(34,197,94,.10);
    padding: 12px;
    border-radius: 14px;
  }
  .warnBox{
    border: 1px solid rgba(245,158,11,.26);
    background: rgba(245,158,11,.10);
    padding: 12px;
    border-radius: 14px;
  }

  table{ width:100%; border-collapse: collapse; margin-top: 10px; }
  th, td{ border-bottom: 1px solid rgba(15,23,42,.08); padding: 10px 8px; text-align:left; font-size: 13px; vertical-align: top; }
  th{ background: rgba(15,23,42,.03); }

  .kpi{ display:grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; }
  .kpi .box{
    background: rgba(255,255,255,.75);
    border: 1px solid rgba(15,23,42,.08);
    border-radius: 18px;
    padding: 14px;
  }
  .kpi .label{ font-size: 12px; color: rgba(15,23,42,.58); margin-bottom: 6px; }
  .kpi .value{ font-size: 20px; font-weight: 900; color: rgba(15,23,42,.92); }

  .stickyBar{
    position: sticky;
    top: 72px;
    background: rgba(246,247,251,.88);
    backdrop-filter: blur(8px);
    padding: 10px 0;
    border-bottom: 1px solid rgba(15,23,42,.08);
    z-index: 2;
  }

  .rowTop{ display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap; }

  .tag{
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding: 6px 10px;
    border-radius: 999px;
    border: 1px solid rgba(15,23,42,.10);
    background: rgba(255,255,255,.65);
    font-size: 12px;
    color: rgba(15,23,42,.82);
  }
  .tagPending{ border-color: rgba(245,158,11,.26); background: rgba(245,158,11,.10); }
  .tagFixed{ border-color: rgba(29,78,216,.22); background: rgba(29,78,216,.10); }

  @media (max-width: 900px){
    .grid4, .grid3, .grid2, .kpi { grid-template-columns: 1fr; }
    .stickyBar{ top: 64px; }
  }
</style>
"""


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
        return "0,0%"


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
      created_at TEXT NOT NULL,
      file_hash TEXT,
      source TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_id TEXT NOT NULL,
      month_ref TEXT NOT NULL,
      uploaded_by TEXT NOT NULL,

      dt_text TEXT,
      categoria TEXT,
      descricao TEXT,
      valor REAL NOT NULL,
      tipo TEXT NOT NULL,

      pagador_label TEXT,
      pagador_real TEXT,

      dono TEXT NOT NULL,
      rateio TEXT NOT NULL,
      rateio_display TEXT,

      observacao TEXT,
      parcela TEXT,

      is_seed INTEGER NOT NULL DEFAULT 0,
      is_pending INTEGER NOT NULL DEFAULT 0,

      created_at TEXT NOT NULL
    )
    """)

    # Backward compat: se existirem colunas antigas em DB antigo, a gente ignora. Em DB novo, já cria certo.

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
    CREATE TABLE IF NOT EXISTS month_locks (
      month_ref TEXT NOT NULL,
      profile TEXT NOT NULL,
      locked INTEGER NOT NULL DEFAULT 0,
      locked_at TEXT,
      PRIMARY KEY (month_ref, profile)
    )
    """)

    conn.commit()
    conn.close()


init_db()


def topbar_html(profile: str):
    nav = ""
    if profile:
        nav = f"""
        <div class="nav">
          <a class="btn" href="{url_for('overview')}">Overview</a>
          <a class="btn" href="{url_for('entrada')}">Entrada</a>
          <a class="btn" href="{url_for('saida')}">Saída</a>
          <a class="btn" href="{url_for('perfil')}">Perfil</a>
        </div>
        """
    return f"""
    <div class="topbar">
      <div class="inner">
        <div class="brand">
          <div class="logo"></div>
          <div>
            <b>Finanças da Casa</b><br/>
            {f"<span class='pill'>Perfil: <b>{profile}</b></span>" if profile else ""}
          </div>
        </div>
        {nav}
      </div>
    </div>
    """


def signed_value(tipo: str, valor: float) -> float:
    if tipo == "Entrada":
        return -abs(valor)
    return abs(valor)


def share_for(profile: str, rateio_key: str) -> float:
    if rateio_key == "50_50":
        return 0.5
    if rateio_key == "60_40":
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


def month_selector_auto(selected_year: str, selected_month: str, action_url: str, extra_hidden: dict | None = None):
    year_options, month_options = year_month_select_html(selected_year, selected_month)
    extra = ""
    if extra_hidden:
        for k, v in extra_hidden.items():
            extra += f"<input type='hidden' name='{k}' value='{_normalize_str(v)}' />"
    return f"""
      <form id="monthForm" method="get" action="{action_url}">
        {extra}
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
      </form>
    """


def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def num_brl(v) -> float:
    try:
        s = _normalize_str(v)
        if not s:
            return 0.0
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except:
        return 0.0


def is_month_locked(month_ref: str, profile: str) -> bool:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT locked FROM month_locks WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    row = cur.fetchone()
    conn.close()
    if not row:
        return False
    return int(row["locked"] or 0) == 1


def set_month_lock(month_ref: str, profile: str, locked: bool):
    now = dt.datetime.utcnow().isoformat(timespec="seconds")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT locked FROM month_locks WHERE month_ref = ? AND profile = ?", (month_ref, profile))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE month_locks SET locked = ?, locked_at = ? WHERE month_ref = ? AND profile = ?",
                    (1 if locked else 0, now, month_ref, profile))
    else:
        cur.execute("INSERT INTO month_locks (month_ref, profile, locked, locked_at) VALUES (?, ?, ?, ?)",
                    (month_ref, profile, 1 if locked else 0, now))
    conn.commit()
    conn.close()


def other_profile(profile: str) -> str:
    return "Rafa" if profile == "Lucas" else "Lucas"


def rateio_to_dono(rateio_key: str, pagador_real: str) -> str:
    if rateio_key in {"60_40", "50_50"}:
        return "Casa"
    if rateio_key == "100_meu":
        return pagador_real
    if rateio_key == "100_outro":
        return other_profile(pagador_real)
    return "Casa"


def normalize_row_from_template(row: dict, uploader_profile: str) -> tuple[list[str], dict]:
    errors = []
    out = {}

    dt_text = _normalize_str(row.get("Data"))
    pagador_label = _normalize_str(row.get("Pagador"))
    categoria = _normalize_str(row.get("Categoria"))
    descricao = _normalize_str(row.get("Descrição"))
    valor = row.get("Valor")
    rateio_display = _normalize_str(row.get("Rateio"))

    if pagador_label not in ALLOWED_PAGADOR:
        errors.append("Pagador inválido")
    if categoria not in ALLOWED_CATEGORIAS:
        errors.append("Categoria inválida")
    if not descricao:
        errors.append("Descrição vazia")

    try:
        if pd.isna(valor):
            valor_f = 0.0
        else:
            valor_f = float(valor)
    except:
        valor_f = 0.0

    if valor_f <= 0:
        errors.append("Valor inválido")

    if rateio_display not in ALLOWED_RATEIO_DISPLAY:
        errors.append("Rateio inválido")

    if pagador_label == "Casa" and rateio_display not in {"60/40", "50/50"}:
        errors.append("Pagador Casa só aceita rateio 60/40 ou 50/50")

    rateio_key = RATEIO_DISPLAY_TO_KEY.get(rateio_display, "")
    if not rateio_key:
        errors.append("Rateio inválido")

    pagador_real = pagador_label if pagador_label != "Casa" else uploader_profile
    dono = rateio_to_dono(rateio_key, pagador_real)

    if dono not in ALLOWED_DONO:
        errors.append("Dono inválido")

    out = {
        "dt_text": dt_text,
        "categoria": categoria,
        "descricao": descricao,
        "valor": float(valor_f),
        "tipo": "Saida",
        "pagador_label": pagador_label,
        "pagador_real": pagador_real,
        "dono": dono,
        "rateio": rateio_key,
        "rateio_display": rateio_display,
        "observacao": "",
        "parcela": "",
        "is_seed": 0,
        "is_pending": 0,
    }
    return errors, out


def read_template_xlsx(raw: bytes) -> pd.DataFrame:
    buf = io.BytesIO(raw)
    xls = pd.ExcelFile(buf, engine="openpyxl")

    # tenta por nome, senão pega primeira
    sheet = None
    for cand in ["Preenchimento", "preenchimento", "Sheet1", "Planilha1"]:
        if cand in xls.sheet_names:
            sheet = cand
            break
    if not sheet:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(xls, sheet_name=sheet)

    required = ["Data", "Pagador", "Categoria", "Descrição", "Valor", "Rateio"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Colunas faltando: " + ", ".join(missing))

    df = df.copy()
    for c in required:
        df[c] = df[c].apply(lambda v: "" if pd.isna(v) else v)
    return df


def _insert_import(conn, batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO imports (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (batch_id, month_ref, uploaded_by, filename, row_count, status, created_at, file_hash, source))


def _insert_transaction(conn, batch_id, month_ref, uploaded_by, r: dict, created_at):
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO transactions
      (batch_id, month_ref, uploaded_by, dt_text, categoria, descricao, valor, tipo, pagador_label, pagador_real, dono, rateio, rateio_display, observacao, parcela, is_seed, is_pending, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        batch_id,
        month_ref,
        uploaded_by,
        r.get("dt_text", ""),
        r.get("categoria", ""),
        r.get("descricao", ""),
        float(r.get("valor") or 0),
        r.get("tipo", "Saida"),
        r.get("pagador_label", ""),
        r.get("pagador_real", ""),
        r.get("dono", ""),
        r.get("rateio", ""),
        r.get("rateio_display", ""),
        r.get("observacao", ""),
        r.get("parcela", ""),
        int(r.get("is_seed") or 0),
        int(r.get("is_pending") or 0),
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


def fetch_transactions_month(month_ref: str) -> list[sqlite3.Row]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*, i.source, i.filename, i.status
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.month_ref = ?
        AND i.status = 'imported'
      ORDER BY t.is_seed DESC, t.is_pending DESC, t.id ASC
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

        payer = r["pagador_real"] or r["uploaded_by"]
        if payer == "Lucas":
            paid_lucas += val
            by_category[cat]["lucas"] += val
        elif payer == "Rafa":
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
    rows = fetch_transactions_month(month_ref)

    house_by_cat = {}
    house_total = 0.0

    my_personal_by_cat = {}
    my_personal_total = 0.0

    receivable_total = 0.0
    payable_total = 0.0

    for r in rows:
        val = signed_value(r["tipo"], r["valor"])
        cat = r["categoria"] or "Sem categoria"

        # Minha parte da casa
        if r["dono"] == "Casa" and r["rateio"] in ("60_40", "50_50"):
            sh = share_for(profile, r["rateio"])
            part = val * sh
            house_total += part
            house_by_cat[cat] = house_by_cat.get(cat, 0.0) + part
            continue

        # Meu pessoal é quando dono é eu e quem pagou de fato foi eu
        payer = r["pagador_real"] or r["uploaded_by"]
        if r["rateio"] == "100_meu" and payer == profile and r["dono"] == profile:
            my_personal_total += val
            my_personal_by_cat[cat] = my_personal_by_cat.get(cat, 0.0) + val
            continue

        # 100%_Outro, eu paguei algo que é do outro, eu tenho a receber
        if r["rateio"] == "100_outro" and payer == profile and r["dono"] != "Casa" and r["dono"] != profile:
            receivable_total += val
            continue

        # 100%_Outro, o outro pagou algo que é meu, eu tenho a pagar
        if r["rateio"] == "100_outro" and payer != profile and r["dono"] == profile:
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
    }


def create_manual_batch(month_ref: str, uploaded_by: str, rows: list[dict]) -> str:
    batch_id = uuid.uuid4().hex
    now = dt.datetime.utcnow().isoformat(timespec="seconds")

    conn = get_db()
    _insert_import(conn, batch_id, month_ref, uploaded_by, "manual_entry", len(rows), "imported", now, None, "manual")
    for r in rows:
        _insert_transaction(conn, batch_id, month_ref, uploaded_by, r, now)

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
        return False, "Lançamento não encontrado"
    if tx["uploaded_by"] != profile:
        return False, "Você só pode excluir lançamentos do seu perfil"
    if int(tx["is_seed"] or 0) == 1:
        return False, "Esse item é do seed do mês. Edite o valor em vez de excluir."

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
    return True, "Lançamento excluído"


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


def ensure_fixed_rows(month_ref: str):
    """
    Garante que existam as linhas fixas e pendentes no mês, uma vez por perfil.
    Elas entram como um batch importado, source seed.
    """
    conn = get_db()
    cur = conn.cursor()

    for profile in ["Lucas", "Rafa"]:
        # já existe seed importado para esse perfil e mês?
        cur.execute("""
          SELECT 1 FROM imports
          WHERE month_ref = ?
            AND uploaded_by = ?
            AND source = 'seed'
            AND status = 'imported'
          LIMIT 1
        """, (month_ref, profile))
        exists = cur.fetchone() is not None
        if exists:
            continue

        batch_id = uuid.uuid4().hex
        now = dt.datetime.utcnow().isoformat(timespec="seconds")
        seed_rows = []

        # FIXOS
        for desc, val, pag_label, rateio_disp, cat in FIXOS_SEED:
            rateio_key = RATEIO_DISPLAY_TO_KEY[rateio_disp]
            pag_real = pag_label  # fixo tem pagador real explícito
            dono = rateio_to_dono(rateio_key, pag_real)
            seed_rows.append({
                "dt_text": "",
                "categoria": cat,
                "descricao": desc,
                "valor": float(val),
                "tipo": "Saida",
                "pagador_label": "Casa" if pag_label == "Casa" else pag_label,
                "pagador_real": pag_real,
                "dono": dono,
                "rateio": rateio_key,
                "rateio_display": rateio_disp,
                "observacao": "FIXO",
                "parcela": "",
                "is_seed": 1,
                "is_pending": 0,
            })

        # PENDENTES
        for desc, cat in PENDENTES_SEED:
            # por padrão, pendente como Casa 60/40, pagador real vira o perfil que está preenchendo
            rateio_disp = "60/40"
            rateio_key = RATEIO_DISPLAY_TO_KEY[rateio_disp]
            pag_label = "Casa"
            pag_real = profile
            dono = rateio_to_dono(rateio_key, pag_real)
            seed_rows.append({
                "dt_text": "",
                "categoria": cat,
                "descricao": desc,
                "valor": 0.0,
                "tipo": "Saida",
                "pagador_label": pag_label,
                "pagador_real": pag_real,
                "dono": dono,
                "rateio": rateio_key,
                "rateio_display": rateio_disp,
                "observacao": "PENDENTE",
                "parcela": "",
                "is_seed": 1,
                "is_pending": 1,
            })

        _insert_import(conn, batch_id, month_ref, profile, "seed", len(seed_rows), "imported", now, None, "seed")
        for r in seed_rows:
            _insert_transaction(conn, batch_id, month_ref, profile, r, now)

    conn.commit()
    conn.close()


def pending_count(month_ref: str, profile: str) -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT COUNT(*) AS c
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.month_ref = ?
        AND i.status = 'imported'
        AND t.uploaded_by = ?
        AND t.is_pending = 1
        AND (t.valor IS NULL OR t.valor <= 0)
    """, (month_ref, profile))
    c = int(cur.fetchone()["c"] or 0)
    conn.close()
    return c


@app.route("/download-template")
def download_template():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    if not os.path.exists(TEMPLATE_PATH):
        return f"Template não encontrado em {TEMPLATE_PATH}. Crie a pasta assets e coloque o arquivo lá.", 404

    return send_file(TEMPLATE_PATH, as_attachment=True, download_name=os.path.basename(TEMPLATE_PATH))


@app.route("/")
def home():
    active_profile = session.get("profile", "")
    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Finanças</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(active_profile)}
        <div class="wrap">
          <div class="card">
            <h1 style="margin-bottom:6px;">Finanças</h1>
            <p>Escolha seu perfil para continuar.</p>

            <div class="grid2" style="margin-top:14px;">
              <a class="btn btnPrimary" style="padding:18px 16px; border-radius:18px; font-size:16px; font-weight:900; text-align:center;"
                 href="{url_for('set_profile', profile='Lucas')}">
                 Entrar como Lucas
              </a>

              <a class="btn btnGreen" style="padding:18px 16px; border-radius:18px; font-size:16px; font-weight:900; text-align:center;"
                 href="{url_for('set_profile', profile='Rafa')}">
                 Entrar como Rafa
              </a>
            </div>

            <p class="muted" style="margin-top:12px;">
              MVP sem senha, só para separar perfil e evitar confusão.
            </p>
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
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Perfil</h2>
            <p class="muted">Trocar perfil</p>

            <div class="grid2" style="margin-top:14px;">
              <a class="btn btnPrimary" style="padding:18px 16px; border-radius:18px; font-size:16px; font-weight:900; text-align:center;"
                 href="{url_for('set_profile', profile='Lucas')}">Virar Lucas</a>

              <a class="btn btnGreen" style="padding:18px 16px; border-radius:18px; font-size:16px; font-weight:900; text-align:center;"
                 href="{url_for('set_profile', profile='Rafa')}">Virar Rafa</a>
            </div>

            <div class="row" style="justify-content:flex-start; margin-top:12px;">
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

    ensure_fixed_rows(month_ref)

    view = request.args.get("view") or "casa"
    if view not in {"casa", "individual"}:
        view = "casa"

    locked = is_month_locked(month_ref, profile)
    pend = pending_count(month_ref, profile)

    pill_lock = "<span class='pill pillOk'>Mês aberto</span>"
    if locked:
        pill_lock = "<span class='pill pillWarn'>Mês fechado</span>"

    pill_pend = ""
    if pend > 0:
        pill_pend = f"<span class='pill pillWarn'>Pendentes: <b>{pend}</b></span>"
    else:
        pill_pend = "<span class='pill pillOk'>Pendentes: <b>0</b></span>"

    toggle = f"""
      <div class="row" style="justify-content:flex-start; gap:10px; margin-top:12px;">
        <a class="btn {'btnPrimary' if view=='casa' else ''}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&view=casa">Casa</a>
        <a class="btn {'btnPrimary' if view=='individual' else ''}" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&view=individual">Individual</a>
        {pill_lock}
        {pill_pend}
      </div>
    """

    lock_btn = ""
    if locked:
        lock_btn = f"<button class='btn btnWarn' onclick=\"toggleLock(false)\">Editar mês</button>"
    else:
        lock_btn = f"<button class='btn btnWarn' onclick=\"toggleLock(true)\">Fechar mês</button>"

    if view == "casa":
        data = compute_casa(month_ref)
        cats_rows = ""
        for cat, obj in data["cats_sorted"]:
            cats_rows += f"""
              <tr>
                <td>{cat}</td>
                <td class="right">{brl(obj["total"])}</td>
                <td class="right">{brl(obj["lucas"])}</td>
                <td class="right">{brl(obj["rafa"])}</td>
              </tr>
            """
        if not cats_rows:
            cats_rows = "<tr><td colspan='4' class='muted'>Sem lançamentos de Casa</td></tr>"

        body = f"""
          <div class="card">
            <div class="rowTop">
              <div>
                <h2>Overview</h2>
                <p class="muted">Mês de referência: <b>{month_ref}</b></p>
              </div>
              <div class="row" style="justify-content:flex-end;">
                {lock_btn}
              </div>
            </div>
            {month_selector_auto(selected_year, selected_month, url_for('overview'), {"view": view})}
            {toggle}
          </div>

          <div class="card">
            <div class="kpi">
              <div class="box"><div class="label">Total Casa</div><div class="value">{brl(data["total_casa"])}</div></div>
              <div class="box"><div class="label">Pago Lucas</div><div class="value">{brl(data["paid_lucas"])}</div><div class="muted">Deveria: {brl(data["expected_lucas"])}</div></div>
              <div class="box"><div class="label">Pago Rafa</div><div class="value">{brl(data["paid_rafa"])}</div><div class="muted">Deveria: {brl(data["expected_rafa"])}</div></div>
              <div class="box"><div class="label">Acerto</div><div class="value">{brl(data["settlement_value"])}</div><div class="muted">{data["settlement_text"]}</div></div>
            </div>
          </div>

          <div class="card">
            <h3>Por categoria</h3>
            <table>
              <thead><tr><th>Categoria</th><th class="right">Total</th><th class="right">Lucas</th><th class="right">Rafa</th></tr></thead>
              <tbody>{cats_rows}</tbody>
            </table>
          </div>
        """
    else:
        data = compute_individual(month_ref, profile)
        cats_house = "".join([f"<tr><td>{c}</td><td class='right'>{brl(v)}</td></tr>" for c, v in data["cats_house"]]) or "<tr><td colspan='2' class='muted'>Sem dados</td></tr>"
        cats_personal = "".join([f"<tr><td>{c}</td><td class='right'>{brl(v)}</td></tr>" for c, v in data["cats_personal"]]) or "<tr><td colspan='2' class='muted'>Sem dados</td></tr>"

        body = f"""
          <div class="card">
            <div class="rowTop">
              <div>
                <h2>Overview</h2>
                <p class="muted">Mês de referência: <b>{month_ref}</b></p>
              </div>
              <div class="row" style="justify-content:flex-end;">
                {lock_btn}
              </div>
            </div>
            {month_selector_auto(selected_year, selected_month, url_for('overview'), {"view": view})}
            {toggle}
          </div>

          <div class="card">
            <div class="kpi">
              <div class="box"><div class="label">Renda total</div><div class="value">{brl(data["income"]["total"])}</div></div>
              <div class="box"><div class="label">Minha parte da casa</div><div class="value">{brl(data["house_total"])}</div></div>
              <div class="box"><div class="label">Meu pessoal</div><div class="value">{brl(data["my_personal_total"])}</div></div>
              <div class="box"><div class="label">Saldo em conta</div><div class="value">{brl(data["saldo_em_conta"])}</div></div>
            </div>
          </div>

          <div class="grid2">
            <div class="card" style="margin-top:0;">
              <h3>Casa por categoria</h3>
              <table><thead><tr><th>Categoria</th><th class="right">Valor</th></tr></thead><tbody>{cats_house}</tbody></table>
            </div>
            <div class="card" style="margin-top:0;">
              <h3>Meu pessoal por categoria</h3>
              <table><thead><tr><th>Categoria</th><th class="right">Valor</th></tr></thead><tbody>{cats_personal}</tbody></table>
            </div>
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
        {topbar_html(profile)}
        <div class="wrap">
          {body}
        </div>

        <script>
          async function toggleLock(toLocked){{
            const pend = {pend};
            if(toLocked){{
              if(pend > 0){{
                const ok = confirm("Existem pendentes neste mês. Você quer fechar mesmo assim?");
                if(!ok) return;
              }} else {{
                const ok = confirm("Confirmar fechar o mês?");
                if(!ok) return;
              }}
            }} else {{
              const ok = confirm("Confirmar reabrir o mês para edição?");
              if(!ok) return;
            }}

            const res = await fetch("/api/toggle-month-lock", {{
              method: "POST",
              headers: {{"Content-Type":"application/json"}},
              body: JSON.stringify({{month_ref: "{month_ref}", locked: toLocked}})
            }});
            const data = await res.json();
            if(!data.ok){{
              alert(data.error || "Erro");
              return;
            }}
            window.location.reload();
          }}
        </script>
      </body>
    </html>
    """
    return html


@app.route("/entrada", methods=["GET", "POST"])
def entrada():
    return renda()


@app.route("/renda", methods=["GET", "POST"])
def renda():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    ensure_fixed_rows(month_ref)

    msg = ""
    if request.method == "POST":
        if is_month_locked(month_ref, profile):
            msg = "Mês fechado, reabra para editar"
        else:
            s1 = num_brl(request.form.get("salario_1"))
            s2 = num_brl(request.form.get("salario_2"))
            ex = num_brl(request.form.get("extras"))
            upsert_income(month_ref, profile, s1, s2, ex)
            msg = "Entrada salva"

    inc = get_income(month_ref, profile)
    locked = is_month_locked(month_ref, profile)

    msg_block = ""
    if msg:
        klass = "okBox" if "salva" in msg.lower() else "warnBox"
        msg_block = f"""
          <div class="card">
            <div class="{klass}">
              <b>{msg}</b>
            </div>
          </div>
        """

    lock_line = "<span class='pill pillOk'>Mês aberto</span>"
    if locked:
        lock_line = "<span class='pill pillWarn'>Mês fechado</span>"

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Entrada</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">
          <div class="card">
            <h2>Entrada do {profile}</h2>
            <p class="muted">Mês de referência: <b>{month_ref}</b> {lock_line}</p>
            {month_selector_auto(selected_year, selected_month, url_for('entrada'))}
          </div>

          <div class="card">
            <h3>Valores do mês</h3>
            <form method="post">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">

              <div class="grid3">
                <div>
                  <label>Salário 1</label>
                  <input type="text" name="salario_1" value="{inc['salario_1']:.2f}" {'disabled' if locked else ''}/>
                </div>
                <div>
                  <label>Salário 2</label>
                  <input type="text" name="salario_2" value="{inc['salario_2']:.2f}" {'disabled' if locked else ''}/>
                </div>
                <div>
                  <label>Extras</label>
                  <input type="text" name="extras" value="{inc['extras']:.2f}" {'disabled' if locked else ''}/>
                </div>
              </div>

              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <button class="btn btnPrimary" type="submit" {'disabled' if locked else ''}>Salvar</button>
                <a class="btn" href="{url_for('overview')}?Ano={selected_year}&Mes={selected_month}&view=individual">Ver overview individual</a>
              </div>

              <p class="muted" style="margin-top:10px;">Total do mês: <b>{brl(inc['total'])}</b></p>
            </form>
          </div>

          {msg_block}
        </div>
      </body>
    </html>
    """
    return html


@app.route("/saida", methods=["GET", "POST"])
def saida():
    profile = session.get("profile", "")
    if not profile:
        return redirect(url_for("home"))

    now_y, now_m = current_year_month()
    selected_year = request.values.get("Ano") or str(now_y)
    selected_month = request.values.get("Mes") or f"{now_m:02d}"
    month_ref = month_ref_from(selected_year, selected_month)

    ensure_fixed_rows(month_ref)

    locked = is_month_locked(month_ref, profile)

    action = request.form.get("action", "")
    errors = []
    info = ""
    info_ok = True

    preview_rows = []
    preview_batch_id = ""

    if request.method == "POST":
        if locked:
            errors.append("Mês fechado. Use Overview para reabrir o mês antes de editar ou importar.")
        else:
            if action == "excel_preview":
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
                            df = read_template_xlsx(raw)
                            normalized = []
                            row_errors = []
                            for idx, r in df.iterrows():
                                line = idx + 2
                                e, out = normalize_row_from_template(r.to_dict(), profile)
                                if e:
                                    row_errors.append(f"Linha {line}: " + "; ".join(e))
                                else:
                                    normalized.append(out)
                            if row_errors:
                                errors.extend(row_errors[:60])
                            else:
                                preview_rows = normalized
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

            elif action == "manual_add":
                # Extra manual com repetição
                dt_text = _normalize_str(request.form.get("Data"))
                pagador_label = _normalize_str(request.form.get("Pagador"))
                categoria = _normalize_str(request.form.get("Categoria"))
                descricao = _normalize_str(request.form.get("Descrição"))
                rateio_display = _normalize_str(request.form.get("Rateio"))
                parcelas = _normalize_str(request.form.get("Repetir"))
                valor = num_brl(request.form.get("Valor"))

                try:
                    repetir = int(parcelas) if parcelas else 1
                except:
                    repetir = 1

                if repetir < 1:
                    repetir = 1
                if repetir > 24:
                    repetir = 24

                if pagador_label not in ALLOWED_PAGADOR:
                    errors.append("Pagador inválido")
                if categoria not in ALLOWED_CATEGORIAS:
                    errors.append("Categoria inválida")
                if not descricao:
                    errors.append("Descrição vazia")
                if valor <= 0:
                    errors.append("Valor inválido")
                if rateio_display not in ALLOWED_RATEIO_DISPLAY:
                    errors.append("Rateio inválido")
                if pagador_label == "Casa" and rateio_display not in {"60/40", "50/50"}:
                    errors.append("Pagador Casa só aceita rateio 60/40 ou 50/50")

                if not errors:
                    rateio_key = RATEIO_DISPLAY_TO_KEY[rateio_display]
                    # Regra do Casa: pagador real vira o profile atual
                    pagador_real = pagador_label if pagador_label != "Casa" else profile
                    dono = rateio_to_dono(rateio_key, pagador_real)

                    rows = []
                    # Repete a partir do mês atual do input
                    base_year = int(selected_year)
                    base_month = int(selected_month)

                    for i in range(repetir):
                        y = base_year
                        m = base_month + i
                        while m > 12:
                            m -= 12
                            y += 1
                        mref = month_ref_from(str(y), f"{m:02d}")

                        ensure_fixed_rows(mref)

                        rows.append({
                            "dt_text": dt_text,
                            "categoria": categoria,
                            "descricao": descricao,
                            "valor": float(valor),
                            "tipo": "Saida",
                            "pagador_label": pagador_label,
                            "pagador_real": pagador_real,
                            "dono": dono,
                            "rateio": rateio_key,
                            "rateio_display": rateio_display,
                            "observacao": "EXTRA",
                            "parcela": f"{i+1}/{repetir}" if repetir > 1 else "",
                            "is_seed": 0,
                            "is_pending": 0,
                        })

                    # Cria um batch por mês para manter tudo organizado
                    # Simples: cria manual batch separado por mês
                    by_month = {}
                    for r in rows:
                        # month_ref calculado acima está em mref, mas precisamos reter, então refaz aqui:
                        # usamos índice para mapear
                        pass

                    # reconstroi e cria batch por mês
                    for i in range(repetir):
                        y = base_year
                        m = base_month + i
                        while m > 12:
                            m -= 12
                            y += 1
                        mref = month_ref_from(str(y), f"{m:02d}")
                        if is_month_locked(mref, profile):
                            continue
                        create_manual_batch(mref, profile, [rows[i]])

                    info = "Gasto manual adicionado"
                    info_ok = True

    # Preview block
    err_block = ""
    if errors:
        items = "".join([f"<li>{e}</li>" for e in errors[:80]])
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
            </div>
          </div>
        """

    preview_table = ""
    if preview_batch_id and preview_rows and not errors:
        head = "".join([f"<th>{c}</th>" for c in ["Data", "Pagador", "Categoria", "Descrição", "Valor", "Rateio"]])
        body_rows = ""
        for r in preview_rows[:20]:
            body_rows += f"""
              <tr>
                <td class="small">{_normalize_str(r.get("dt_text"))}</td>
                <td>{_normalize_str(r.get("pagador_label"))}</td>
                <td class="small">{_normalize_str(r.get("categoria"))}</td>
                <td class="small">{_normalize_str(r.get("descricao"))}</td>
                <td class="right">{brl(float(r.get("valor") or 0))}</td>
                <td>{_normalize_str(r.get("rateio_display"))}</td>
              </tr>
            """

        preview_table = f"""
          <div class="card">
            <h3>Preview do upload</h3>
            <p class="muted">Batch: <span class="mono">{preview_batch_id[:10]}...</span> mostrando 20 linhas</p>
            <div class="okBox">
              <form method="post">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="action" value="excel_import">
                <input type="hidden" name="batch_id" value="{preview_batch_id}">
                <div class="row" style="justify-content:flex-start;">
                  <button class="btn btnPrimary" type="submit">OK importar</button>
                </div>
              </form>
              <p class="muted" style="margin-top:10px;">Se você não importar, esse batch fica como preview e pode ser excluído depois.</p>
            </div>
            <table>
              <thead><tr>{head}</tr></thead>
              <tbody>{body_rows}</tbody>
            </table>
          </div>
        """

    # Lista do mês, com seed no topo e edição inline
    rows = fetch_transactions_month(month_ref)

    locked_pill = "<span class='pill pillOk'>Mês aberto</span>"
    if locked:
        locked_pill = "<span class='pill pillWarn'>Mês fechado</span>"

    pend = pending_count(month_ref, profile)
    pend_pill = "<span class='pill pillOk'>Pendentes: <b>0</b></span>"
    if pend > 0:
        pend_pill = f"<span class='pill pillWarn'>Pendentes: <b>{pend}</b></span>"

    month_line = f"<p class='muted'>Mês de referência: <b>{month_ref}</b> {locked_pill} {pend_pill}</p>"

    # options
    pagador_opts = "".join([f"<option value='{p}'>{p}</option>" for p in ["Lucas", "Rafa", "Casa"]])
    cat_opts = "".join([f"<option value='{c}'>{c}</option>" for c in sorted(list(ALLOWED_CATEGORIAS))])
    rateio_opts = "".join([f"<option value='{r}'>{r}</option>" for r in ["60/40", "50/50", "100%_Meu", "100%_Outro"]])

    row_html = ""
    for r in rows[:1200]:
        can_edit = (r["uploaded_by"] == profile) and (not locked)
        can_delete = can_edit and (int(r["is_seed"] or 0) == 0)

        tags = ""
        if int(r["is_seed"] or 0) == 1:
            tags += "<span class='tag tagFixed'>Seed</span> "
        if int(r["is_pending"] or 0) == 1 and float(r["valor"] or 0) <= 0:
            tags += "<span class='tag tagPending'>Pendente</span> "

        val = signed_value(r["tipo"], r["valor"])
        rate_disp = _normalize_str(r["rateio_display"] or RATEIO_KEY_TO_DISPLAY.get(r["rateio"], r["rateio"]))
        pag_label = _normalize_str(r["pagador_label"] or "")
        cat = _normalize_str(r["categoria"] or "")
        desc = _normalize_str(r["descricao"] or "")
        dt_text = _normalize_str(r["dt_text"] or "")

        edit_btn = ""
        if can_edit:
            edit_btn = f"<button class='btn' type='button' onclick='toggleEdit({r['id']})'>Editar</button>"

        del_btn = ""
        if can_delete:
            del_btn = f"""
              <form method="post" style="display:inline;">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="action" value="delete_one">
                <input type="hidden" name="tx_id" value="{r['id']}">
                <button class="btn btnDanger" type="submit">Excluir</button>
              </form>
            """

        row_html += f"""
          <tr data-id="{r['id']}">
            <td class="mono">{r['id']}</td>
            <td>{tags}<span class="small muted">{dt_text}</span></td>

            <td>
              <span class="v v_pag" id="v_pag_{r['id']}">{pag_label}</span>
              <select class="i i_pag" id="i_pag_{r['id']}" style="display:none;" onchange="saveSelect({r['id']}, 'pagador_label', this.value)">{pagador_opts}</select>
            </td>

            <td>
              <span class="v v_cat" id="v_cat_{r['id']}">{cat}</span>
              <select class="i i_cat" id="i_cat_{r['id']}" style="display:none;" onchange="saveSelect({r['id']}, 'categoria', this.value)">{cat_opts}</select>
            </td>

            <td style="min-width:220px;">
              <span class="v v_desc" id="v_desc_{r['id']}">{desc}</span>
              <input class="i i_desc" id="i_desc_{r['id']}" style="display:none;" value="{desc}" onkeydown="if(event.key==='Enter') saveInput({r['id']}, 'descricao', this.value)" />
            </td>

            <td class="right" style="min-width:140px;">
              <span class="v v_val" id="v_val_{r['id']}">{brl(val)}</span>
              <input class="i i_val" id="i_val_{r['id']}" style="display:none;" value="{float(r['valor'] or 0):.2f}" onkeydown="if(event.key==='Enter') saveInput({r['id']}, 'valor', this.value)" />
            </td>

            <td>
              <span class="v v_rat" id="v_rat_{r['id']}">{rate_disp}</span>
              <select class="i i_rat" id="i_rat_{r['id']}" style="display:none;" onchange="saveSelect({r['id']}, 'rateio_display', this.value)">{rateio_opts}</select>
            </td>

            <td class="small">{_normalize_str(r["observacao"] or "")}</td>
            <td>
              {edit_btn}
              {del_btn}
            </td>
          </tr>
        """

    if not row_html:
        row_html = "<tr><td colspan='8' class='muted'>Sem lançamentos</td></tr>"

    # Batches (para excluir previews)
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
        if can_del_batch and (b["source"] != "seed"):
            btn = f"""
              <form method="post" style="display:inline;">
                <input type="hidden" name="Ano" value="{selected_year}">
                <input type="hidden" name="Mes" value="{selected_month}">
                <input type="hidden" name="action" value="delete_batch">
                <input type="hidden" name="batch_id" value="{b['batch_id']}">
                <button class="btn btnDanger" type="submit">Excluir</button>
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

    # POST handlers for delete_one/delete_batch
    if request.method == "POST" and action in {"delete_one", "delete_batch"} and (not locked):
        if action == "delete_one":
            try:
                tx_id = int(request.form.get("tx_id"))
            except:
                tx_id = 0
            ok, m = delete_transaction_any(tx_id, profile)
            info = m
            info_ok = ok
            return redirect(url_for("saida", Ano=selected_year, Mes=selected_month))
        if action == "delete_batch":
            batch_id = _normalize_str(request.form.get("batch_id"))
            ok, m = delete_batch(batch_id, profile)
            info = m
            info_ok = ok
            return redirect(url_for("saida", Ano=selected_year, Mes=selected_month))

    html = f"""
    <!doctype html>
    <html lang="pt-br">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Saída</title>
        {BASE_CSS}
      </head>
      <body>
        {topbar_html(profile)}
        <div class="wrap">

          <div class="card">
            <h2>Saída</h2>
            {month_line}
            {month_selector_auto(selected_year, selected_month, url_for('saida'))}
          </div>

          {err_block}
          {info_block}

          <div class="card">
            <h3>Upload do mês</h3>
            <p class="muted">Você faz upload do seu arquivo. Se Pagador for Casa, o pagador real vira quem está logado.</p>

            <div class="row" style="justify-content:flex-start;">
              <a class="btn" href="{url_for('download_template')}">Baixar template</a>
            </div>

            <form id="excelForm" method="post" enctype="multipart/form-data" style="margin-top:12px;">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <input type="hidden" name="action" value="excel_preview">

              <label>Arquivo Excel</label>
              <input id="fileInput" type="file" name="file" accept=".xlsx,.xls" {'disabled' if locked else ''}/>
              <p class="muted">Colunas esperadas: Data, Pagador, Categoria, Descrição, Valor, Rateio</p>
            </form>
          </div>

          {preview_table}

          <div class="card">
            <h3>Adicionar gasto manual</h3>
            <p class="muted">Para extras. Você pode repetir por alguns meses, começando neste mês.</p>

            <form method="post">
              <input type="hidden" name="Ano" value="{selected_year}">
              <input type="hidden" name="Mes" value="{selected_month}">
              <input type="hidden" name="action" value="manual_add">

              <div class="grid2">
                <div>
                  <label>Data</label>
                  <input type="text" name="Data" placeholder="Opcional" {'disabled' if locked else ''}/>
                </div>
                <div>
                  <label>Valor</label>
                  <input type="text" name="Valor" placeholder="ex: 120,50" {'disabled' if locked else ''}/>
                </div>
              </div>

              <div class="grid2">
                <div>
                  <label>Pagador</label>
                  <select name="Pagador" {'disabled' if locked else ''}>
                    <option value="Lucas">Lucas</option>
                    <option value="Rafa">Rafa</option>
                    <option value="Casa">Casa</option>
                  </select>
                </div>
                <div>
                  <label>Rateio</label>
                  <select name="Rateio" {'disabled' if locked else ''}>
                    <option value="60/40">60/40</option>
                    <option value="50/50">50/50</option>
                    <option value="100%_Meu">100%_Meu</option>
                    <option value="100%_Outro">100%_Outro</option>
                  </select>
                </div>
              </div>

              <div class="grid2">
                <div>
                  <label>Categoria</label>
                  <select name="Categoria" {'disabled' if locked else ''}>
                    {cat_opts}
                  </select>
                </div>
                <div>
                  <label>Repetir por quantos meses</label>
                  <input type="text" name="Repetir" placeholder="1" {'disabled' if locked else ''}/>
                </div>
              </div>

              <div>
                <label>Descrição</label>
                <input type="text" name="Descrição" {'disabled' if locked else ''}/>
              </div>

              <div class="row" style="justify-content:flex-start; margin-top:12px;">
                <button class="btn btnPrimary" type="submit" {'disabled' if locked else ''}>Salvar</button>
              </div>
            </form>
          </div>

          <div class="card">
            <h3>Lista do mês</h3>
            <p class="muted">Os fixos e pendentes aparecem no topo somente aqui. Clique em Editar para ajustar.</p>

            <div class="stickyBar">
              <div class="row" style="justify-content:flex-start;">
                <span class="pill">Editável: <b>{'Não' if locked else 'Sim'}</b></span>
                <span class="pill">Seu perfil: <b>{profile}</b></span>
              </div>
            </div>

            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Tags</th>
                  <th>Pagador</th>
                  <th>Categoria</th>
                  <th>Descrição</th>
                  <th class="right">Valor</th>
                  <th>Rateio</th>
                  <th>Obs</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {row_html}
              </tbody>
            </table>
          </div>

          <div class="card">
            <h3>Batches do mês</h3>
            <p class="muted">Preview também aparece aqui. Você pode excluir preview e imports do seu perfil.</p>
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
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {batches_html}
              </tbody>
            </table>
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

          function toggleEdit(id){{
            const show = (el, flag) => {{ if(el) el.style.display = flag ? "inline" : "none"; }};
            const showBlock = (el, flag) => {{ if(el) el.style.display = flag ? "inline-block" : "none"; }};

            // pagador
            show(document.getElementById("v_pag_"+id), false);
            showBlock(document.getElementById("i_pag_"+id), true);

            // categoria
            show(document.getElementById("v_cat_"+id), false);
            showBlock(document.getElementById("i_cat_"+id), true);

            // descricao
            show(document.getElementById("v_desc_"+id), false);
            showBlock(document.getElementById("i_desc_"+id), true);

            // valor
            show(document.getElementById("v_val_"+id), false);
            showBlock(document.getElementById("i_val_"+id), true);

            // rateio
            show(document.getElementById("v_rat_"+id), false);
            showBlock(document.getElementById("i_rat_"+id), true);

            // preencher selects com valor atual
            const vPag = document.getElementById("v_pag_"+id)?.innerText?.trim() || "";
            const vCat = document.getElementById("v_cat_"+id)?.innerText?.trim() || "";
            const vRat = document.getElementById("v_rat_"+id)?.innerText?.trim() || "";

            const iPag = document.getElementById("i_pag_"+id);
            const iCat = document.getElementById("i_cat_"+id);
            const iRat = document.getElementById("i_rat_"+id);

            if(iPag) iPag.value = vPag;
            if(iCat) iCat.value = vCat;
            if(iRat) iRat.value = vRat;
          }}

          async function saveField(id, field, value){{
            const res = await fetch("/api/update-transaction", {{
              method: "POST",
              headers: {{"Content-Type":"application/json"}},
              body: JSON.stringify({{id, field, value}})
            }});
            const data = await res.json();
            if(!data.ok){{
              alert(data.error || "Erro");
              return false;
            }}
            return true;
          }}

          async function saveInput(id, field, value){{
            const ok = await saveField(id, field, value);
            if(ok) window.location.reload();
          }}

          async function saveSelect(id, field, value){{
            const ok = await saveField(id, field, value);
            if(ok) window.location.reload();
          }}
        </script>
      </body>
    </html>
    """
    return html


@app.post("/api/update-transaction")
def api_update_transaction():
    profile = session.get("profile", "")
    if not profile:
        return jsonify({"ok": False, "error": "Sem perfil"}), 401

    data = request.get_json(silent=True) or {}
    try:
        tid = int(data.get("id"))
    except:
        return jsonify({"ok": False, "error": "ID inválido"}), 400

    field = _normalize_str(data.get("field"))
    value = data.get("value")

    allowed = {"valor", "descricao", "categoria", "pagador_label", "rateio_display"}
    if field not in allowed:
        return jsonify({"ok": False, "error": "Campo não permitido"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
      SELECT t.*, i.status
      FROM transactions t
      JOIN imports i ON i.batch_id = t.batch_id
      WHERE t.id = ?
      LIMIT 1
    """, (tid,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Item não encontrado"}), 404

    if row["uploaded_by"] != profile:
        conn.close()
        return jsonify({"ok": False, "error": "Você só pode editar itens do seu perfil"}), 403

    month_ref = row["month_ref"]
    if is_month_locked(month_ref, profile):
        conn.close()
        return jsonify({"ok": False, "error": "Mês fechado"}), 403

    if field == "valor":
        v = num_brl(value)
        if v <= 0:
            conn.close()
            return jsonify({"ok": False, "error": "Valor inválido"}), 400

        # se era pendente, zera a flag
        is_pending = int(row["is_pending"] or 0)
        if is_pending == 1:
            cur.execute("UPDATE transactions SET valor = ?, is_pending = 0, observacao = 'PREENCHIDO' WHERE id = ?", (v, tid))
        else:
            cur.execute("UPDATE transactions SET valor = ? WHERE id = ?", (v, tid))

    elif field == "descricao":
        txt = _normalize_str(value)
        if not txt:
            conn.close()
            return jsonify({"ok": False, "error": "Descrição vazia"}), 400
        cur.execute("UPDATE transactions SET descricao = ? WHERE id = ?", (txt, tid))

    elif field == "categoria":
        txt = _normalize_str(value)
        if txt not in ALLOWED_CATEGORIAS:
            conn.close()
            return jsonify({"ok": False, "error": "Categoria inválida"}), 400
        cur.execute("UPDATE transactions SET categoria = ? WHERE id = ?", (txt, tid))

    elif field == "pagador_label":
        txt = _normalize_str(value)
        if txt not in ALLOWED_PAGADOR:
            conn.close()
            return jsonify({"ok": False, "error": "Pagador inválido"}), 400

        # regra Casa: pagador real vira quem está logado
        pag_real = txt if txt != "Casa" else profile

        # recalcula dono mantendo rateio atual
        rateio_key = row["rateio"]
        rateio_disp = row["rateio_display"] or RATEIO_KEY_TO_DISPLAY.get(rateio_key, rateio_key)

        if txt == "Casa" and rateio_disp not in {"60/40", "50/50"}:
            conn.close()
            return jsonify({"ok": False, "error": "Pagador Casa só aceita 60/40 ou 50/50"}), 400

        dono = rateio_to_dono(rateio_key, pag_real)
        cur.execute("UPDATE transactions SET pagador_label = ?, pagador_real = ?, dono = ? WHERE id = ?", (txt, pag_real, dono, tid))

    elif field == "rateio_display":
        txt = _normalize_str(value)
        if txt not in ALLOWED_RATEIO_DISPLAY:
            conn.close()
            return jsonify({"ok": False, "error": "Rateio inválido"}), 400

        pag_label = row["pagador_label"] or ""
        pag_real = row["pagador_real"] or row["uploaded_by"]

        if pag_label == "Casa" and txt not in {"60/40", "50/50"}:
            conn.close()
            return jsonify({"ok": False, "error": "Pagador Casa só aceita 60/40 ou 50/50"}), 400

        rateio_key = RATEIO_DISPLAY_TO_KEY.get(txt, "")
        dono = rateio_to_dono(rateio_key, pag_real)
        cur.execute("UPDATE transactions SET rateio_display = ?, rateio = ?, dono = ? WHERE id = ?", (txt, rateio_key, dono, tid))

    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/toggle-month-lock")
def api_toggle_month_lock():
    profile = session.get("profile", "")
    if not profile:
        return jsonify({"ok": False, "error": "Sem perfil"}), 401

    data = request.get_json(silent=True) or {}
    month_ref = _normalize_str(data.get("month_ref"))
    locked = bool(data.get("locked"))

    if not month_ref or len(month_ref) != 6 or (not month_ref.isdigit()):
        return jsonify({"ok": False, "error": "month_ref inválido"}), 400

    set_month_lock(month_ref, profile, locked)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
