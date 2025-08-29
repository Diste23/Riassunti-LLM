from openai import OpenAI
import os
import openai
from dotenv import load_dotenv
from parser import Parser
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

# Carica le variabili da .env
load_dotenv()

client = OpenAI()

class Elaborazione:
    def __init__(self,indice:dict):
        self.indice=indice
        pass

    def create_blocks(self,indice):
        chunks = list(indice.keys())  # oppure la tua lista reale di chunk
        lunghezze = list(indice.values())

        gruppi_testo = []
        gruppo_corrente = []
        somma = 0
        limite = 20000

        for chunk, lung in zip(chunks, lunghezze):
            if somma + lung > limite and gruppo_corrente:
                # chiudi gruppo
                gruppi_testo.append("".join(gruppo_corrente))
                gruppo_corrente = []
                somma = 0
            
            gruppo_corrente.append(chunk)
            somma += lung

        # aggiungi ultimo gruppo
        if gruppo_corrente:
            gruppi_testo.append("".join(gruppo_corrente))

        return gruppi_testo
        # ora puoi iterare sui testi concatenati

    def create_summary(self, gruppi_testo: list[str]) -> str:
        summary = ""
        for i, gruppo in enumerate(gruppi_testo, start=1):
            response = client.responses.create(
                model="gpt-5-nano",  # resta sul tuo modello
                instructions=(
                    "Sei un giurista esperto in diritto societario, privato, civile, "
                    "costituzionale e commerciale. Riassumi in modo accurato e fedele, "
                    "senza perdere o distorcere informazioni importanti. Se possibile, "
                    "usa punti elenco e mantieni la terminologia giuridica corretta." \
                    "Non interrompere mai bruscamente il tuo riassunto, se necessario continua. " \
                    "All'Inizio del riassunto fai un elenco puntato degli argomenti principali che andrai a riassumere nelle righe successive."
                    "Non propormi altre cose che potresti fare o suggerimenti. limitati esclusivamente a svolgere il tuo compito"
                ),
                input=f"Testo da riassumere: {gruppo}",
                #temperature=0.2,
                max_output_tokens=7000,
            )
            summary += response.output_text
        return summary
    
    def salva_pdf(self, riassunto: str, pdf_path: str) -> str:
        """
        Crea un PDF contenente il riassunto.
        Lo salva in una nuova cartella 'output' accanto a 'Riassunti-LLM'.
        """
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        # cartella padre di "Riassunti-LLM"
        parent_dir = os.path.dirname(os.path.dirname(pdf_path))
        output_dir = os.path.join(parent_dir, "output")
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, base_name + "_riassunto_llm.pdf")

        # Stili
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Riassunto LLM", styles["Title"]))
        story.append(Spacer(1, 20))

        # Aggiungi paragrafi del riassunto
        for par in riassunto.split("\n"):
            if par.strip():
                story.append(Paragraph(par.strip(), styles["Normal"]))
                story.append(Spacer(1, 10))

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        doc.build(story)

        return output_path

pdf_path = r"C:\Users\Maurizio\Desktop\Progetti\Riassunti LLM\Riassunti-LLM\Diritto della crisi d-impresa e dell-insolvenza.pdf"
p = Parser(str(pdf_path))
testo = p.create_text()
chunks = p.create_chunks(testo)
indice = p.create_index(chunks)

elab = Elaborazione(indice)
tutti_i_gruppi = elab.create_blocks(indice)       # << qui limiti ai primi due
risultato = elab.create_summary(tutti_i_gruppi)
output_file = elab.salva_pdf(risultato, pdf_path)
print(f"✅ Riassunto salvato in: {output_file}")

