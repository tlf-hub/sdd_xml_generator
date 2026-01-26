import streamlit as st
import csv
import io
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import re
import pandas as pd

# Configurazione pagina
st.set_page_config(
    page_title="Generatore XML SEPA SDD",
    page_icon="💰",
    layout="wide"
)

# Inizializzazione session state
if 'dati_azienda_caricati' not in st.session_state:
    st.session_state.dati_azienda_caricati = {}
if 'lista_incassi' not in st.session_state:
    st.session_state.lista_incassi = []
if 'data_addebito' not in st.session_state:
    st.session_state.data_addebito = None

def pulisci_iban(iban):
    """Rimuove spazi dall'IBAN"""
    return re.sub(r'\s+', '', iban.upper())

def normalizza_data(data_str):
    """Normalizza una data nel formato YYYY-MM-DD"""
    if pd.isna(data_str):
        return None
    
    data_str = str(data_str).strip()
    
    # Prova vari formati comuni
    formati = [
        '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', 
        '%d.%m.%Y', '%Y/%m/%d', '%d/%m/%y',
        '%d-%m-%y', '%d.%m.%y'
    ]
    
    for formato in formati:
        try:
            data_obj = datetime.strptime(data_str, formato)
            return data_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return data_str

def normalizza_importo(importo_str):
    """Normalizza un importo nel formato xxxx.xx"""
    if pd.isna(importo_str):
        return "0.00"
    
    importo_str = str(importo_str).strip()
    
    # Rimuovi spazi e sostituisci virgola con punto
    importo_str = importo_str.replace(' ', '').replace(',', '.')
    
    try:
        importo_float = float(importo_str)
        return f"{importo_float:.2f}"
    except ValueError:
        return "0.00"

def aggrega_incassi(df):
    """Aggrega le righe per lo stesso debitore"""
    # Raggruppa per IBAN (che identifica univocamente il debitore)
    df_aggregato = df.groupby('iban').agg({
        'nome': 'first',
        'cognome': 'first',
        'codice_fiscale': 'first',
        'indirizzo': 'first',
        'cap': 'first',
        'citta': 'first',
        'provincia': 'first',
        'paese': 'first',
        'bic': 'first',
        'importo': lambda x: sum(float(i) for i in x),
        'causale': lambda x: list(dict.fromkeys(x)),  # Rimuove duplicati mantenendo l'ordine
        'data_firma_mandato': 'first'
    }).reset_index()
    
    # Formatta la causale aggregata
    df_aggregato['causale'] = df_aggregato['causale'].apply(
        lambda causali: "Ft. " + ", ".join(str(c) for c in causali)
    )
    
    # Formatta l'importo
    df_aggregato['importo'] = df_aggregato['importo'].apply(lambda x: f"{x:.2f}")
    
    return df_aggregato

def genera_message_id():
    """Genera un Message ID univoco"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"MSGID-{timestamp}"

def genera_payment_id(idx):
    """Genera un Payment ID univoco"""
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"PMT-{timestamp}-{idx:04d}"

def genera_end_to_end_id(idx):
    """Genera un End-to-End ID univoco"""
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"E2E-{timestamp}-{idx:04d}"

def genera_mandate_id(idx):
    """Genera un Mandate ID univoco"""
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"MNDT-{timestamp}-{idx:04d}"

def crea_template_aziendale():
    """Crea il template CSV per i dati aziendali"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome_azienda', 'iban', 'creditor_id'])
    writer.writerow(['La Mia Azienda SRL', 'IT60X0542811101000000123456', 'IT99ZZZ1234567890'])
    return output.getvalue()

def crea_template_incassi():
    """Crea il template CSV per gli incassi"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome', 'cognome', 'codice_fiscale', 'indirizzo', 'cap', 'citta', 'provincia', 'paese', 'iban', 'bic', 'importo', 'causale', 'data_firma_mandato'])
    writer.writerow(['Mario', 'Rossi', 'RSSMRA80A01H501Z', 'Via Roma 123', '20100', 'Milano', 'MI', 'IT', 'IT60X0542811101000000654321', 'BPMOIT22XXX', '150.00', 
                    'Servizio gennaio 2025', '15/01/2024'])
    writer.writerow(['Mario', 'Rossi', 'RSSMRA80A01H501Z', 'Via Roma 123', '20100', 'Milano', 'MI', 'IT', 'IT60X0542811101000000654321', 'BPMOIT22XXX', '75,50', 
                    'Servizio febbraio 2025', '15/01/2024'])
    writer.writerow(['Laura', 'Bianchi', 'BNCLRA85M45F205Y', 'Corso Italia 45', '00100', 'Roma', 'RM', 'IT', 'IT28W8000000292100645211111', 'UNCRITMM', '250.50', 
                    'Abbonamento annuale', '10/02/2024'])
    return output.getvalue()

def valida_dati_aziendali(df):
    """Valida i dati aziendali"""
    required_fields = ['nome_azienda', 'iban', 'creditor_id']
    for field in required_fields:
        if field not in df.columns:
            return False, f"Campo mancante: {field}"
        if df[field].iloc[0] == '' or pd.isna(df[field].iloc[0]):
            return False, f"Campo vuoto: {field}"
    return True, "OK"

def processa_csv_incassi(df):
    """Processa il CSV degli incassi: normalizza date, importi e aggrega"""
    
    # Lista dei campi richiesti
    required_fields = ['nome', 'cognome', 'codice_fiscale', 'indirizzo', 'cap', 'citta', 'provincia', 'paese', 'iban', 'bic', 'importo', 'causale', 'data_firma_mandato']
    
    # Se il CSV non ha intestazioni, le aggiungiamo
    if df.columns[0] not in required_fields:
        if len(df.columns) == len(required_fields):
            df.columns = required_fields
        else:
            return None, f"Il CSV deve avere {len(required_fields)} colonne"
    
    # Verifica che tutti i campi siano presenti
    for field in required_fields:
        if field not in df.columns:
            return None, f"Campo mancante: {field}"
    
    # Normalizza le date
    df['data_firma_mandato'] = df['data_firma_mandato'].apply(normalizza_data)
    
    # Normalizza gli importi
    df['importo'] = df['importo'].apply(normalizza_importo)
    
    # Verifica che tutti i campi obbligatori siano compilati
    for idx, row in df.iterrows():
        for field in required_fields:
            if pd.isna(row[field]) or str(row[field]).strip() == '':
                return None, f"Campo vuoto nella riga {idx+2}: {field}"
    
    # Aggrega le righe per lo stesso debitore
    df_aggregato = aggrega_incassi(df)
    
    return df_aggregato, "OK"

def genera_xml_sepa(dati_aziendali, incassi, data_addebito):
    """Genera il file XML SEPA SDD"""
    # Calcola totali
    numero_transazioni = len(incassi)
    totale_importo = sum(float(inc['importo']) for inc in incassi)
    
    # Crea la struttura XML
    root = Element('Document')
    root.set('xmlns', 'urn:iso:std:iso:20022:tech:xsd:pain.008.001.02')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    
    cstmr_drct_dbt_initn = SubElement(root, 'CstmrDrctDbtInitn')
    
    # Group Header
    grp_hdr = SubElement(cstmr_drct_dbt_initn, 'GrpHdr')
    SubElement(grp_hdr, 'MsgId').text = genera_message_id()
    SubElement(grp_hdr, 'CreDtTm').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    SubElement(grp_hdr, 'NbOfTxs').text = str(numero_transazioni)
    SubElement(grp_hdr, 'CtrlSum').text = f'{totale_importo:.2f}'
    
    initg_pty = SubElement(grp_hdr, 'InitgPty')
    SubElement(initg_pty, 'Nm').text = dati_aziendali['nome_azienda']
    
    # Payment Information
    pmt_inf = SubElement(cstmr_drct_dbt_initn, 'PmtInf')
    SubElement(pmt_inf, 'PmtInfId').text = genera_payment_id(1)
    SubElement(pmt_inf, 'PmtMtd').text = 'DD'
    SubElement(pmt_inf, 'BtchBookg').text = 'true'
    SubElement(pmt_inf, 'NbOfTxs').text = str(numero_transazioni)
    SubElement(pmt_inf, 'CtrlSum').text = f'{totale_importo:.2f}'
    
    # Payment Type Information
    pmt_tp_inf = SubElement(pmt_inf, 'PmtTpInf')
    svc_lvl = SubElement(pmt_tp_inf, 'SvcLvl')
    SubElement(svc_lvl, 'Cd').text = 'SEPA'
    lcl_instrm = SubElement(pmt_tp_inf, 'LclInstrm')
    SubElement(lcl_instrm, 'Cd').text = 'CORE'
    SubElement(pmt_tp_inf, 'SeqTp').text = 'RCUR'
    
    # Data addebito
    SubElement(pmt_inf, 'ReqdColltnDt').text = data_addebito
    
    # Creditor
    cdtr = SubElement(pmt_inf, 'Cdtr')
    SubElement(cdtr, 'Nm').text = dati_aziendali['nome_azienda']
    
    # Creditor Account
    cdtr_acct = SubElement(pmt_inf, 'CdtrAcct')
    cdtr_id = SubElement(cdtr_acct, 'Id')
    SubElement(cdtr_id, 'IBAN').text = pulisci_iban(dati_aziendali['iban'])
    
    # Creditor Agent
    cdtr_agt = SubElement(pmt_inf, 'CdtrAgt')
    fin_instn_id = SubElement(cdtr_agt, 'FinInstnId')
    SubElement(fin_instn_id, 'BIC').text = 'NOTPROVIDED'
    
    # Creditor Scheme Identification
    cdtr_schme_id = SubElement(pmt_inf, 'CdtrSchmeId')
    cdtr_id_obj = SubElement(cdtr_schme_id, 'Id')
    prvt_id = SubElement(cdtr_id_obj, 'PrvtId')
    othr = SubElement(prvt_id, 'Othr')
    SubElement(othr, 'Id').text = dati_aziendali['creditor_id']
    schme_nm = SubElement(othr, 'SchmeNm')
    SubElement(schme_nm, 'Prtry').text = 'SEPA'
    
    # Direct Debit Transaction Information per ogni incasso
    for idx, incasso in enumerate(incassi, 1):
        drct_dbt_tx_inf = SubElement(pmt_inf, 'DrctDbtTxInf')
        
        # Payment Identification
        pmt_id = SubElement(drct_dbt_tx_inf, 'PmtId')
        SubElement(pmt_id, 'EndToEndId').text = genera_end_to_end_id(idx)
        
        # Instructed Amount
        instd_amt = SubElement(drct_dbt_tx_inf, 'InstdAmt')
        instd_amt.set('Ccy', 'EUR')
        instd_amt.text = f'{float(incasso["importo"]):.2f}'
        
        # Direct Debit Transaction
        drct_dbt_tx = SubElement(drct_dbt_tx_inf, 'DrctDbtTx')
        mndt_rltd_inf = SubElement(drct_dbt_tx, 'MndtRltdInf')
        SubElement(mndt_rltd_inf, 'MndtId').text = genera_mandate_id(idx)
        SubElement(mndt_rltd_inf, 'DtOfSgntr').text = incasso['data_firma_mandato']
        
        # Debtor Agent
        dbtr_agt = SubElement(drct_dbt_tx_inf, 'DbtrAgt')
        dbtr_fin_instn_id = SubElement(dbtr_agt, 'FinInstnId')
        
        # Usa il BIC se fornito, altrimenti NOTPROVIDED
        bic_value = incasso.get('bic', '').strip()
        if bic_value and bic_value.upper() != 'NOTPROVIDED':
            SubElement(dbtr_fin_instn_id, 'BIC').text = bic_value
        else:
            SubElement(dbtr_fin_instn_id, 'BIC').text = 'NOTPROVIDED'
        
        # Debtor
        dbtr = SubElement(drct_dbt_tx_inf, 'Dbtr')
        SubElement(dbtr, 'Nm').text = f"{incasso['nome']} {incasso['cognome']}"
        
        # Debtor Postal Address
        pstl_adr = SubElement(dbtr, 'PstlAdr')
        SubElement(pstl_adr, 'Ctry').text = incasso['paese']
        adr_line1 = SubElement(pstl_adr, 'AdrLine')
        adr_line1.text = incasso['indirizzo']
        adr_line2 = SubElement(pstl_adr, 'AdrLine')
        adr_line2.text = f"{incasso['cap']} {incasso['citta']} ({incasso['provincia']})"
        
        # Debtor Identification
        dbtr_id_elem = SubElement(dbtr, 'Id')
        orgn_id = SubElement(dbtr_id_elem, 'OrgId')
        othr_id = SubElement(orgn_id, 'Othr')
        SubElement(othr_id, 'Id').text = incasso['codice_fiscale']
        
        # Debtor Account
        dbtr_acct = SubElement(drct_dbt_tx_inf, 'DbtrAcct')
        dbtr_acct_id = SubElement(dbtr_acct, 'Id')
        SubElement(dbtr_acct_id, 'IBAN').text = pulisci_iban(incasso['iban'])
        
        # Remittance Information
        rmt_inf = SubElement(drct_dbt_tx_inf, 'RmtInf')
        SubElement(rmt_inf, 'Ustrd').text = incasso['causale']
    
    # Converti in stringa XML formattata
    xml_str = minidom.parseString(tostring(root)).toprettyxml(indent="  ", encoding="UTF-8")
    
    return xml_str

# UI principale
st.title("💰 Generatore XML SEPA SDD per Incassi Bancari")
st.markdown("---")

# STEP 1: Dati Aziendali
st.header("📋 STEP 1: Dati Aziendali")

col1, col2 = st.columns(2)

with col1:
    template_aziendale = crea_template_aziendale()
    st.download_button(
        label="📥 Scarica Template Dati Aziendali",
        data=template_aziendale,
        file_name="template_dati_aziendali.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    uploaded_aziendale = st.file_uploader(
        "📂 Carica CSV Dati Aziendali",
        type=['csv'],
        key="upload_aziendale"
    )

if uploaded_aziendale is not None:
    try:
        df_aziendale = pd.read_csv(uploaded_aziendale)
        valido, messaggio = valida_dati_aziendali(df_aziendale)
        
        if valido:
            st.session_state.dati_azienda_caricati = df_aziendale.iloc[0].to_dict()
            st.success("✅ Dati Aziendali Caricati Correttamente!")
            
            with st.expander("🔍 Visualizza Dati Caricati"):
                st.write(f"**Nome Azienda:** {st.session_state.dati_azienda_caricati['nome_azienda']}")
                st.write(f"**IBAN:** {st.session_state.dati_azienda_caricati['iban']}")
                st.write(f"**Creditor ID:** {st.session_state.dati_azienda_caricati['creditor_id']}")
        else:
            st.error(f"❌ Errore: {messaggio}")
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 2: Data Addebito e CSV Incassi
st.header("💳 STEP 2: Data Addebito e CSV Incassi")

# Data addebito
st.subheader("📅 Data Addebito su Conto Corrente")
data_addebito_input = st.date_input(
    "Seleziona la data di addebito",
    value=None,
    min_value=datetime.now().date(),
    help="Data in cui i fondi saranno addebitati dai conti dei debitori"
)

if data_addebito_input:
    st.session_state.data_addebito = data_addebito_input.strftime('%Y-%m-%d')
    st.success(f"✅ Data addebito impostata: {st.session_state.data_addebito}")

st.markdown("---")

# CSV Incassi
st.subheader("📄 Caricamento CSV Incassi")

col1, col2 = st.columns(2)

with col1:
    template_incassi = crea_template_incassi()
    st.download_button(
        label="📥 Scarica Template CSV Incassi",
        data=template_incassi,
        file_name="template_incassi.csv",
        mime="text/csv",
        use_container_width=True
    )

with col2:
    uploaded_incassi = st.file_uploader(
        "📂 Carica CSV Incassi",
        type=['csv'],
        key="upload_incassi",
        help="Il CSV può avere o meno intestazioni. Date e importi saranno normalizzati automaticamente."
    )

if uploaded_incassi is not None:
    try:
        # Prova prima a leggere con header
        df_incassi = pd.read_csv(uploaded_incassi, header=0)
        
        # Processa il CSV: normalizza e aggrega
        df_processato, messaggio = processa_csv_incassi(df_incassi)
        
        if df_processato is not None:
            st.session_state.lista_incassi = df_processato.to_dict('records')
            
            totale = sum(float(inc['importo']) for inc in st.session_state.lista_incassi)
            
            st.success(f"✅ CSV processato! {len(st.session_state.lista_incassi)} debitori aggregati")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Numero Debitori", len(st.session_state.lista_incassi))
            with col_b:
                st.metric("Totale Incassi", f"€ {totale:.2f}")
            with col_c:
                st.metric("Media per Debitore", f"€ {totale/len(st.session_state.lista_incassi):.2f}")
            
            with st.expander("🔍 Visualizza Debitori Aggregati"):
                st.dataframe(df_processato, use_container_width=True)
            
            st.info("ℹ️ I debitori con lo stesso IBAN sono stati aggregati sommando gli importi e unendo le causali")
        else:
            st.error(f"❌ Errore: {messaggio}")
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 3: Generazione XML
st.header("🚀 STEP 3: Generazione XML SEPA")

if st.session_state.dati_azienda_caricati and st.session_state.lista_incassi and st.session_state.data_addebito:
    st.info("✅ Tutti i dati sono pronti! Puoi generare il file XML SEPA.")
    
    if st.button("🚀 Genera XML SEPA", type="primary", use_container_width=True):
        try:
            xml_content = genera_xml_sepa(
                st.session_state.dati_azienda_caricati,
                st.session_state.lista_incassi,
                st.session_state.data_addebito
            )
            
            filename = f"SEPA_SDD_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            
            st.download_button(
                label="💾 Scarica File XML",
                data=xml_content,
                file_name=filename,
                mime="application/xml",
                use_container_width=True
            )
            
            st.success("✅ File XML SEPA generato con successo!")
            st.balloons()
            
            with st.expander("📄 Anteprima XML"):
                st.code(xml_content.decode('utf-8'), language='xml')
            
        except Exception as e:
            st.error(f"❌ Errore nella generazione del file XML: {str(e)}")
else:
    messaggi = []
    if not st.session_state.dati_azienda_caricati:
        messaggi.append("- Dati aziendali")
    if not st.session_state.data_addebito:
        messaggi.append("- Data addebito")
    if not st.session_state.lista_incassi:
        messaggi.append("- CSV incassi")
    
    st.warning(f"⚠️ Completa i seguenti passaggi:\n" + "\n".join(messaggi))

st.markdown("---")
st.info("ℹ️ Il file XML generato è compatibile con il formato SEPA pain.008.001.02 e pronto per essere caricato nel tuo sistema di home banking.")

# Footer
st.markdown("---")
st.caption("Generatore XML SEPA SDD v2.0 | Formato: pain.008.001.02 | Aggregazione automatica debitori")