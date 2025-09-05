import os
import re
import threading
import tempfile
import webbrowser

from flask import Flask, request, render_template_string, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Usa le CLASSI ESISTENTI (Nessuna riscrittura!)
from parser import Parser            # la tua classe Parser
from llm import Elaborazione         # la tua classe Elaborazione (usa già OpenAI client definito in llm.py)

# Dipendenze per creare il PDF del riassunto nella cartella scelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

load_dotenv()

ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Salvataggio PDF nella cartella scelta dall'utente (non ridefinisce metodi esistenti)
def save_summary_pdf(summary_text: str, output_dir: str, base_name: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_\- ]", "_", base_name)
    output_path = os.path.join(output_dir, f"{safe_name}_riassunto_llm.pdf")

    styles = getSampleStyleSheet()
    story = [Paragraph("Riassunto LLM", styles["Title"]), Spacer(1, 20)]

    # FIX: niente split("") — spezzatura per paragrafi (linee vuote) o per riga
    text = (summary_text or "").strip()
    # Prova prima per paragrafi separati da righe vuote
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()] or text.splitlines()

    for par in paragraphs:
        if par.strip():
            story.append(Paragraph(par.strip(), styles["Normal"]))
            story.append(Spacer(1, 10))

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    doc.build(story)
    return output_path

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

PAGE = """
<!doctype html>
<html lang=\"it\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Ottieni il tuo riassunto dettagliato</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
    .card { max-width: 720px; margin: 0 auto; padding: 1.5rem; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }
    label { display:block; margin: .5rem 0 .25rem; font-weight: 600; }
    input[type=file], input[type=text] { width: 100%; padding: .75rem; border: 1px solid #d1d5db; border-radius: 8px; }
    .row { display: grid; gap: 1rem; }
    .btn { display:inline-block; padding:.75rem 1rem; border-radius: 10px; border:0; background:#111827; color:white; font-weight:600; cursor:pointer; }
    .btn:disabled { opacity:.6; cursor:not-allowed; }
    .muted { color:#6b7280; font-size:.9rem; }
    .flash { background:#fef3c7; color:#92400e; padding:.75rem; border-radius:8px; margin: .5rem 0 1rem; }
    .success { background:#ecfdf5; color:#065f46; }
    .result { background:#f9fafb; padding:1rem; border:1px dashed #e5e7eb; border-radius:8px; }
    code { background:#f3f4f6; padding:2px 4px; border-radius:4px; }
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Ottieni il tuo riassunto dettagliato</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class=\"flash {{ 'success' if category == 'success' else '' }}\">{{ message|safe }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <form method=\"post\" action=\"{{ url_for('process') }}\" enctype=\"multipart/form-data\">
      <div class=\"row\">
        <div>
          <label for=\"pdf\">PDF da caricare</label>
          <input id=\"pdf\" name=\"pdf\" type=\"file\" accept=\"application/pdf\" required />
          <p class=\"muted\">Seleziona il PDF da riassumere.</p>
        </div>
        <div>
          <label for=\"output_dir\">Cartella di destinazione</label>
          <input id=\"output_dir\" name=\"output_dir\" type=\"text\" placeholder=\"Es. C:\\\\Users\\\\tuo_utente\\\\Documents o /Users/tuo_utente/Documents\">
          <p class=\"muted\">Percorso in cui salvare il PDF del riassunto (deve esistere e essere scrivibile).</p>
        </div>
      </div>
      <div style=\"margin-top:1rem\">
        <button class=\"btn\" type=\"submit\">Esegui riassunto</button>
      </div>
    </form>

    {% if result_path %}
      <div class=\"result\" style=\"margin-top:1.5rem\">
        <p><strong>File generato:</strong><br>{{ result_path }}</p>
        <p>
          <a class=\"btn\" href=\"{{ url_for('download', path=result_path) }}\">Scarica</a>
        </p>
      </div>
    {% endif %}
  </div>
</body>
</html>
"""

@app.get("/")
def index():
    return render_template_string(PAGE, result_path=None)

@app.post("/process")
def process():
    if "pdf" not in request.files:
        flash("Nessun file selezionato.")
        return redirect(url_for("index"))

    file = request.files["pdf"]
    output_dir = request.form.get("output_dir", "").strip()

    if not file or file.filename == "":
        flash("Nessun file selezionato.")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Il file deve essere un PDF.")
        return redirect(url_for("index"))

    if not output_dir:
        flash("Specifica una cartella di destinazione.")
        return redirect(url_for("index"))

    if not os.path.isdir(output_dir):
        flash("La cartella di destinazione non esiste.")
        return redirect(url_for("index"))

    if not os.access(output_dir, os.W_OK):
        flash("La cartella di destinazione non è scrivibile.")
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, filename)
        file.save(temp_path)

        try:
            # Pipeline con LE CLASSI ESISTENTI
            parser = Parser(temp_path)
            testo = parser.create_text()
            chunks = parser.create_chunks(testo)
            indice = parser.create_index(chunks)

            elab = Elaborazione(indice)
            gruppi = elab.create_blocks(indice)
            riassunto = elab.create_summary(gruppi)

            base_name = os.path.splitext(filename)[0]
            result_path = save_summary_pdf(riassunto, output_dir, base_name)
        except Exception as e:
            flash(f"Errore durante l'elaborazione: {e}")
            return redirect(url_for("index"))

    flash("✅ Riassunto completato con successo!", "success")
    return render_template_string(PAGE, result_path=result_path)

@app.get("/download")
def download():
    path = request.args.get("path")
    if not path or not os.path.isfile(path):
        flash("File non trovato per il download.")
        return redirect(url_for("index"))
    return send_file(path, as_attachment=True)

def _open_browser(port: int):
    """Apre il browser sulla pagina principale (utile per doppio-click)."""
    try:
        webbrowser.open(f"http://127.0.0.1:{port}/")
    except Exception:
        pass

if __name__ == "__main__":
    # Porta configurabile via env, default 5000
    port = int(os.environ.get("PORT", 5000))
    # Avvia il browser automaticamente poco dopo l'avvio del server
    threading.Timer(1.0, _open_browser, args=(port,)).start()
    # Se lo lanci in Docker/WSL e vuoi aprirlo dall'host, usa host="0.0.0.0"
    app.run(host="127.0.0.1", port=port, debug=False)
