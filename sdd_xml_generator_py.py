import streamlit as st
import csv
from datetime import datetime
import io

st.set_page_config(
    page_title="Generatore XML SEPA SDD",
    page_icon="💶",
    layout="wide"
)

# Inizializza session state
if 'company_data' not in st.session_state:
    st.session_state.company_data = {
        'nome_azienda': '',
        'iban': '',
        'creditor_id': ''
    }
if 'csv_data' not in st.session_state:
    st.session_state.csv_data = []

# Header
st.title("💶 Generatore XML SEPA SDD")
st.markdown("### Genera file XML per incassi SDD da caricare su home banking")
st.divider()

# Sezione 1: Dati Aziendali
st.header("1️⃣ Dati Aziendali")

col1, col2 = st.columns(2)

with col1:
    if st.button("📥 Scarica Template Dati Aziendali", type="primary"):
        template_content = "campo,valore\n"
        template_content += "nome_azienda,NOME_AZIENDA_DA_MODIFICARE\n"
        template_content += "iban,IT00A0000000000000000000000\n"
        template_content += "creditor_id,IT00ZZZ000000000000"
        
        st.download_button(
            label="💾 Clicca per scaricare",
            data=template_content,
            file_name="template_dati_aziendali.csv",
            mime="text/csv"
        )

with col2:
    company_file = st.file_uploader(
        "📂 Carica CSV Dati Aziendali",
        type=['csv'],
        key="company_uploader"
    )
    
    if company_file is not None:
        try:
            content = company_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            
            for row in reader:
                campo = row.get('campo', '').strip()
                valore = row.get('valore', '').strip()
                
                if campo == 'nome_azienda':
                    st.session_state.company_data['nome_azienda'] = valore
                elif campo == 'iban':
                    st.session_state.company_data['iban'] = valore
                elif campo == 'creditor_id':
                    st.session_state.company_data['creditor_id'] = valore
            
            st.success("✅ Dati aziendali caricati!")
        except Exception as e:
            st.error(f"❌ Errore nel caricamento: {str(e)}")

# Mostra dati caricati
if st.session_state.company_data['nome_azienda']:
    st.info(f"""
    **Dati caricati:**
    - **Azienda:** {st.session_state.company_data['nome_azienda']}
    - **IBAN:** {st.session_state.company_data['iban']}
    - **Creditor ID:** {st.session_state.company_data['creditor_id']}
    """)

st.divider()

# Sezione 2: CSV Incassi
st.header("2️⃣ CSV Incassi")

col3, col4 = st.columns(2)

with col3:
    if st.button("📥 Scarica Template CSV Incassi", type="primary"):
        template_csv = "nome,cognome,iban,importo,causale,data_scadenza,rum,data_firma_mandato,tipo_sequenza\n"
        template_csv += "Mario,Rossi,IT60X0542811101000000123456,100.50,Pagamento fattura 001,2024-02-15,CLIENTE-001-2024,2024-01-10,RCUR\n"
        template_csv += "Laura,Bianchi,IT28W8000000292100645211208,250.00,Abbonamento mensile,2024-02-15,CLIENTE-002-2024,2024-01-12,RCUR"
        
        st.download_button(
            label="💾 Clicca per scaricare",
            data=template_csv,
            file_name="template_incassi_sdd.csv",
            mime="text/csv"
        )

with col4:
    csv_file = st.file_uploader(
        "📂 Carica CSV Incassi",
        type=['csv'],
        key="csv_uploader",
        disabled=not st.session_state.company_data['nome_azienda']
    )
    
    if csv_file is not None:
        try:
            content = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            st.session_state.csv_data = list(reader)
            
            st.success(f"✅ Caricati {len(st.session_state.csv_data)} incassi!")
        except Exception as e:
            st.error(f"❌ Errore nel caricamento: {str(e)}")

# Mostra riepilogo incassi
if st.session_state.csv_data:
    total = sum(float(row.get('importo', 0)) for row in st.session_state.csv_data)
    st.info(f"""
    **Incassi caricati:** {len(st.session_state.csv_data)}  
    **Importo totale:** € {total:.2f}
    """)
    
    with st.expander("📋 Visualizza dettagli incassi"):
        st.dataframe(st.session_state.csv_data)

st.divider()

# Sezione 3: Genera XML
st.header("3️⃣ Genera XML")

can_generate = (
    st.session_state.company_data['nome_azienda'] and
    st.session_state.company_data['iban'] and
    st.session_state.company_data['creditor_id'] and
    len(st.session_state.csv_data) > 0
)

if st.button("✅ Genera XML SEPA SDD", type="primary", disabled=not can_generate):
    try:
        now = datetime.now()
        msg_id = f"MSG-{int(now.timestamp())}"
        cre_dt_tm = now.isoformat()
        reqd_colltn_dt = st.session_state.csv_data[0].get('data_scadenza', now.strftime('%Y-%m-%d'))
        
        total_amount = sum(float(row.get('importo', 0)) for row in st.session_state.csv_data)
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.02" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        xml += '  <CstmrDrctDbtInitn>\n'
        xml += '    <GrpHdr>\n'
        xml += f'      <MsgId>{msg_id}</MsgId>\n'
        xml += f'      <CreDtTm>{cre_dt_tm}</CreDtTm>\n'
        xml += f'      <NbOfTxs>{len(st.session_state.csv_data)}</NbOfTxs>\n'
        xml += f'      <CtrlSum>{total_amount:.2f}</CtrlSum>\n'
        xml += '      <InitgPty>\n'
        xml += f'        <Nm>{st.session_state.company_data["nome_azienda"]}</Nm>\n'
        xml += '      </InitgPty>\n'
        xml += '    </GrpHdr>\n'
        xml += '    <PmtInf>\n'
        xml += f'      <PmtInfId>PMTINF-{int(now.timestamp())}</PmtInfId>\n'
        xml += '      <PmtMtd>DD</PmtMtd>\n'
        xml += f'      <NbOfTxs>{len(st.session_state.csv_data)}</NbOfTxs>\n'
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
        xml += f'        <Nm>{st.session_state.company_data["nome_azienda"]}</Nm>\n'
        xml += '      </Cdtr>\n'
        xml += '      <CdtrAcct>\n'
        xml += '        <Id>\n'
        xml += f'          <IBAN>{st.session_state.company_data["iban"]}</IBAN>\n'
        xml += '        </Id>\n'
        xml += '      </CdtrAcct>\n'
        xml += '      <CdtrSchmeId>\n'
        xml += '        <Id>\n'
        xml += '          <PrvtId>\n'
        xml += '            <Othr>\n'
        xml += f'              <Id>{st.session_state.company_data["creditor_id"]}</Id>\n'
        xml += '              <SchmeNm>\n'
        xml += '                <Prtry>SEPA</Prtry>\n'
        xml += '              </SchmeNm>\n'
        xml += '            </Othr>\n'
        xml += '          </PrvtId>\n'
        xml += '        </Id>\n'
        xml += '      </CdtrSchmeId>\n'
        
        for index, row in enumerate(st.session_state.csv_data):
            end_to_end_id = f"E2E-{int(now.timestamp())}-{index + 1}"
            # RUM: Riferimento Unico Mandato (obbligatorio)
            rum = row.get('rum', f'MNDT-{index + 1}')
            # Data firma mandato (obbligatorio)
            data_firma = row.get('data_firma_mandato', now.strftime('%Y-%m-%d'))
            # Tipo sequenza (FRST=primo, RCUR=ricorrente, OOFF=una tantum, FNAL=finale)
            tipo_seq = row.get('tipo_sequenza', 'RCUR').upper()
            
            xml += '      <DrctDbtTxInf>\n'
            xml += '        <PmtId>\n'
            xml += f'          <EndToEndId>{end_to_end_id}</EndToEndId>\n'
            xml += '        </PmtId>\n'
            xml += f'        <InstdAmt Ccy="EUR">{float(row.get("importo", 0)):.2f}</InstdAmt>\n'
            xml += '        <DrctDbtTx>\n'
            xml += '          <MndtRltdInf>\n'
            xml += f'            <MndtId>{rum}</MndtId>\n'
            xml += f'            <DtOfSgntr>{data_firma}</DtOfSgntr>\n'
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
        
        st.success("✅ File XML generato con successo!")
        
        st.download_button(
            label="💾 Scarica XML SEPA SDD",
            data=xml,
            file_name=f"SEPA_SDD_{int(now.timestamp())}.xml",
            mime="text/xml"
        )
        
    except Exception as e:
        st.error(f"❌ Errore nella generazione: {str(e)}")

if not can_generate:
    st.warning("⚠️ Completa i passi 1 e 2 prima di generare l'XML")

# Note in fondo
st.divider()
st.markdown("""
### 📝 Note importanti:

**Campi CSV obbligatori:**
- `nome`, `cognome`: nome e cognome del debitore
- `iban`: IBAN del debitore (formato IT + 25 caratteri)
- `importo`: importo in euro con punto decimale (es. 100.50)
- `causale`: descrizione del pagamento
- `data_scadenza`: data richiesta incasso (formato YYYY-MM-DD)
- `rum`: **Riferimento Unico Mandato** - codice univoco max 35 caratteri (es. CLIENTE-001-2024)
- `data_firma_mandato`: data firma del mandato (formato YYYY-MM-DD)
- `tipo_sequenza`: tipo incasso - valori possibili:
  - `FRST` = primo addebito di una serie
  - `RCUR` = addebito ricorrente (default)
  - `OOFF` = addebito una tantum
  - `FNAL` = ultimo addebito di una serie

**Cosa serve:**
1. **Creditor ID** (ICS): fornito dalla tua banca (es. IT00ZZZ000000000000)
2. **Mandato firmato** da ogni cliente con il RUM univoco
3. **Conservazione mandati**: sei responsabile della conservazione dei mandati firmati

**Standard:** XML compatibile con SEPA pain.008.001.02
""")