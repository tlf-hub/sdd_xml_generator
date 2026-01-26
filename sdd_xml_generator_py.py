import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv
from datetime import datetime
import os

class SDDXMLGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Generatore XML SEPA SDD")
        self.root.geometry("800x700")
        
        self.company_data = {
            'nome_azienda': '',
            'iban': '',
            'creditor_id': ''
        }
        self.csv_data = []
        
        self.setup_ui()
    
    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg='#1e3a8a', pady=20)
        header.pack(fill='x')
        
        tk.Label(
            header, 
            text="Generatore XML SEPA SDD", 
            font=('Arial', 20, 'bold'),
            bg='#1e3a8a',
            fg='white'
        ).pack()
        
        tk.Label(
            header,
            text="Genera file XML per incassi SDD da caricare su home banking",
            font=('Arial', 10),
            bg='#1e3a8a',
            fg='#bfdbfe'
        ).pack()
        
        # Main container
        main = tk.Frame(self.root, padx=20, pady=20)
        main.pack(fill='both', expand=True)
        
        # Sezione 1: Dati Aziendali
        section1 = tk.LabelFrame(main, text="1. Dati Aziendali", font=('Arial', 12, 'bold'), padx=15, pady=15)
        section1.pack(fill='x', pady=(0, 15))
        
        tk.Button(
            section1,
            text="📥 Scarica Template Dati Aziendali",
            command=self.download_company_template,
            bg='#3b82f6',
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief='flat',
            padx=10,
            pady=8
        ).pack(anchor='w', pady=(0, 10))
        
        tk.Button(
            section1,
            text="📂 Carica CSV Dati Aziendali",
            command=self.load_company_data,
            bg='#6366f1',
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief='flat',
            padx=10,
            pady=8
        ).pack(anchor='w', pady=(0, 10))
        
        self.company_info_label = tk.Label(section1, text="Nessun dato caricato", fg='#6b7280', font=('Arial', 9))
        self.company_info_label.pack(anchor='w')
        
        # Sezione 2: CSV Incassi
        section2 = tk.LabelFrame(main, text="2. CSV Incassi", font=('Arial', 12, 'bold'), padx=15, pady=15)
        section2.pack(fill='x', pady=(0, 15))
        
        tk.Button(
            section2,
            text="📥 Scarica Template CSV Incassi",
            command=self.download_csv_template,
            bg='#8b5cf6',
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief='flat',
            padx=10,
            pady=8
        ).pack(anchor='w', pady=(0, 10))
        
        tk.Button(
            section2,
            text="📂 Carica CSV Incassi",
            command=self.load_csv_data,
            bg='#a855f7',
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief='flat',
            padx=10,
            pady=8
        ).pack(anchor='w', pady=(0, 10))
        
        self.csv_info_label = tk.Label(section2, text="Nessun CSV caricato", fg='#6b7280', font=('Arial', 9))
        self.csv_info_label.pack(anchor='w')
        
        # Sezione 3: Genera XML
        section3 = tk.LabelFrame(main, text="3. Genera XML", font=('Arial', 12, 'bold'), padx=15, pady=15)
        section3.pack(fill='x', pady=(0, 15))
        
        self.generate_btn = tk.Button(
            section3,
            text="✅ Genera e Scarica XML SEPA SDD",
            command=self.generate_xml,
            bg='#10b981',
            fg='white',
            font=('Arial', 12, 'bold'),
            cursor='hand2',
            relief='flat',
            padx=15,
            pady=12,
            state='disabled'
        )
        self.generate_btn.pack()
        
        # Note
        note_frame = tk.Frame(main, bg='#f3f4f6', relief='solid', borderwidth=1)
        note_frame.pack(fill='x', pady=(10, 0))
        
        tk.Label(
            note_frame,
            text="Note:",
            font=('Arial', 9, 'bold'),
            bg='#f3f4f6',
            anchor='w'
        ).pack(fill='x', padx=10, pady=(10, 5))
        
        notes = [
            "• Formato CSV: nome, cognome, iban, importo, causale, data_scadenza",
            "• Date in formato YYYY-MM-DD (es. 2024-02-15)",
            "• Importo con punto decimale (es. 100.50)",
            "• XML compatibile con standard SEPA pain.008.001.02"
        ]
        
        for note in notes:
            tk.Label(
                note_frame,
                text=note,
                font=('Arial', 8),
                bg='#f3f4f6',
                anchor='w',
                fg='#4b5563'
            ).pack(fill='x', padx=10)
        
        tk.Label(note_frame, text="", bg='#f3f4f6').pack(pady=5)
    
    def download_company_template(self):
        content = "campo,valore\n"
        content += "nome_azienda,NOME_AZIENDA_DA_MODIFICARE\n"
        content += "iban,IT00A0000000000000000000000\n"
        content += "creditor_id,IT00ZZZ000000000000"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="template_dati_aziendali.csv"
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Successo", "Template dati aziendali scaricato!")
    
    def download_csv_template(self):
        content = "nome,cognome,iban,importo,causale,data_scadenza\n"
        content += "Mario,Rossi,IT60X0542811101000000123456,100.50,Pagamento fattura 001,2024-02-15\n"
        content += "Laura,Bianchi,IT28W8000000292100645211208,250.00,Abbonamento mensile,2024-02-15"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="template_incassi_sdd.csv"
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Successo", "Template CSV incassi scaricato!")
    
    def load_company_data(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    campo = row.get('campo', '').strip()
                    valore = row.get('valore', '').strip()
                    
                    if campo == 'nome_azienda':
                        self.company_data['nome_azienda'] = valore
                    elif campo == 'iban':
                        self.company_data['iban'] = valore
                    elif campo == 'creditor_id':
                        self.company_data['creditor_id'] = valore
            
            info_text = f"✓ Dati caricati:\n"
            info_text += f"  Azienda: {self.company_data['nome_azienda']}\n"
            info_text += f"  IBAN: {self.company_data['iban']}\n"
            info_text += f"  Creditor ID: {self.company_data['creditor_id']}"
            
            self.company_info_label.config(text=info_text, fg='#059669')
            self.check_can_generate()
            messagebox.showinfo("Successo", "Dati aziendali caricati correttamente!")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del file:\n{str(e)}")
    
    def load_csv_data(self):
        if not self.company_data['nome_azienda']:
            messagebox.showwarning("Attenzione", "Carica prima i dati aziendali!")
            return
        
        filepath = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            self.csv_data = []
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.csv_data.append(row)
            
            total = sum(float(row.get('importo', 0)) for row in self.csv_data)
            info_text = f"✓ Incassi caricati: {len(self.csv_data)}\n"
            info_text += f"  Importo totale: € {total:.2f}"
            
            self.csv_info_label.config(text=info_text, fg='#059669')
            self.check_can_generate()
            messagebox.showinfo("Successo", f"Caricati {len(self.csv_data)} incassi!")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del CSV:\n{str(e)}")
    
    def check_can_generate(self):
        if (self.company_data['nome_azienda'] and 
            self.company_data['iban'] and 
            self.company_data['creditor_id'] and 
            len(self.csv_data) > 0):
            self.generate_btn.config(state='normal')
        else:
            self.generate_btn.config(state='disabled')
    
    def generate_xml(self):
        now = datetime.now()
        msg_id = f"MSG-{int(now.timestamp())}"
        cre_dt_tm = now.isoformat()
        reqd_colltn_dt = self.csv_data[0].get('data_scadenza', now.strftime('%Y-%m-%d'))
        
        total_amount = sum(float(row.get('importo', 0)) for row in self.csv_data)
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        xml += '  <CstmrDrctDbtInitn>\n'
        xml += '    <GrpHdr>\n'
        xml += f'      <MsgId>{msg_id}</MsgId>\n'
        xml += f'      <CreDtTm>{cre_dt_tm}</CreDtTm>\n'
        xml += f'      <NbOfTxs>{len(self.csv_data)}</NbOfTxs>\n'
        xml += f'      <CtrlSum>{total_amount:.2f}</CtrlSum>\n'
        xml += '      <InitgPty>\n'
        xml += f'        <Nm>{self.company_data["nome_azienda"]}</Nm>\n'
        xml += '      </InitgPty>\n'
        xml += '    </GrpHdr>\n'
        xml += '    <PmtInf>\n'
        xml += f'      <PmtInfId>PMTINF-{int(now.timestamp())}</PmtInfId>\n'
        xml += '      <PmtMtd>DD</PmtMtd>\n'
        xml += f'      <NbOfTxs>{len(self.csv_data)}</NbOfTxs>\n'
        xml += f'      <CtrlSum>{total_amount:.2f}</CtrlSum>\n'
        xml += '      <PmtTpInf>\n'
        xml += '        <SvcLvl>\n'
        xml += '          <Cd>SEPA</Cd>\n'
        xml += '        </SvcLvl>\n'
        xml += '        <LclInstrm>\n'
        xml += '          <Cd>CORE</Cd>\n'
        xml += '        </LclInstrm>\n'
        xml += '        <SeqTp>RCUR</SeqTp>\n'
        xml += '      </PmtTpInf>\n'
        xml += f'      <ReqdColltnDt>{reqd_colltn_dt}</ReqdColltnDt>\n'
        xml += '      <Cdtr>\n'
        xml += f'        <Nm>{self.company_data["nome_azienda"]}</Nm>\n'
        xml += '      </Cdtr>\n'
        xml += '      <CdtrAcct>\n'
        xml += '        <Id>\n'
        xml += f'          <IBAN>{self.company_data["iban"]}</IBAN>\n'
        xml += '        </Id>\n'
        xml += '      </CdtrAcct>\n'
        xml += '      <CdtrSchmeId>\n'
        xml += '        <Id>\n'
        xml += '          <PrvtId>\n'
        xml += '            <Othr>\n'
        xml += f'              <Id>{self.company_data["creditor_id"]}</Id>\n'
        xml += '              <SchmeNm>\n'
        xml += '                <Prtry>SEPA</Prtry>\n'
        xml += '              </SchmeNm>\n'
        xml += '            </Othr>\n'
        xml += '          </PrvtId>\n'
        xml += '        </Id>\n'
        xml += '      </CdtrSchmeId>\n'
        
        for index, row in enumerate(self.csv_data):
            end_to_end_id = f"E2E-{int(now.timestamp())}-{index + 1}"
            xml += '      <DrctDbtTxInf>\n'
            xml += '        <PmtId>\n'
            xml += f'          <EndToEndId>{end_to_end_id}</EndToEndId>\n'
            xml += '        </PmtId>\n'
            xml += f'        <InstdAmt Ccy="EUR">{float(row.get("importo", 0)):.2f}</InstdAmt>\n'
            xml += '        <DrctDbtTx>\n'
            xml += '          <MndtRltdInf>\n'
            xml += f'            <MndtId>MNDT-{index + 1}</MndtId>\n'
            xml += f'            <DtOfSgntr>{now.strftime("%Y-%m-%d")}</DtOfSgntr>\n'
            xml += '          </MndtRltdInf>\n'
            xml += '        </DrctDbtTx>\n'
            xml += '        <DbtrAgt>\n'
            xml += '          <FinInstnId>\n'
            xml += '            <ClrSysMmbId>\n'
            xml += '              <MmbId>NOTPROVIDED</MmbId>\n'
            xml += '            </ClrSysMmbId>\n'
            xml += '          </FinInstnId>\n'
            xml += '        </DbtrAgt>\n'
            xml += '        <Dbtr>\n'
            xml += f'          <Nm>{row.get("nome", "")} {row.get("cognome", "")}</Nm>\n'
            xml += '        </Dbtr>\n'
            xml += '        <DbtrAcct>\n'
            xml += '          <Id>\n'
            xml += f'            <IBAN>{row.get("iban", "")}</IBAN>\n'
            xml += '          </Id>\n'
            xml += '        </DbtrAcct>\n'
            xml += '        <RmtInf>\n'
            xml += f'          <Ustrd>{row.get("causale", "")}</Ustrd>\n'
            xml += '        </RmtInf>\n'
            xml += '      </DrctDbtTxInf>\n'
        
        xml += '    </PmtInf>\n'
        xml += '  </CstmrDrctDbtInitn>\n'
        xml += '</Document>'
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")],
            initialfile=f"SEPA_SDD_{int(now.timestamp())}.xml"
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml)
            messagebox.showinfo("Successo", f"File XML generato con successo!\n\n{filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SDDXMLGenerator(root)
    root.mainloop()