import re
import pdfplumber

class Parser:
    def __init__(self, filepath: str):
        self.filepath = filepath

    def create_text(self) -> str:
        """Estrae il testo da tutte le pagine del PDF e lo restituisce come unica stringa."""
        testo = []
        with pdfplumber.open(self.filepath) as pdf:
            for pagina in pdf.pages:
                estratto = pagina.extract_text() or ""
                testo.append(estratto)
        # Unisci il testo delle pagine separandole con una riga vuota
        full_text = "\n\n".join(testo)
        # Normalizza spazi multipli e spazi prima dei segni di punteggiatura
        full_text = re.sub(r"[ \t]+", " ", full_text)
        full_text = re.sub(r" *\n *", "\n", full_text)
        return full_text.strip()

    def create_chunks(self, testo: str) -> list[str]:
        """
        Divide il testo in frasi (chunk) ogni volta che trova un punto finale.
        Mantiene il punto alla fine di ogni chunk.
        """
        # Divide su punto seguito da spazi/newline, mantenendo il punto nel chunk precedente
        frasi = re.split(r"(?<=\.)\s+", testo)
        # Pulisci e filtra vuoti
        frasi = [f.strip() for f in frasi if f and f.strip()]
        return frasi

# Esempio d'uso
if __name__ == "__main__":
    p = Parser("Riassunti-LLM\Diritto della crisi d-impresa e dell-insolvenza.pdf")
    testo = p.create_text()
    chunks = p.create_chunks(testo)
    print(f"Numero di chunk: {len(chunks)}")
    print(chunks[5])  # anteprima
