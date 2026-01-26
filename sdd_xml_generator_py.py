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
if 'dati_aziendali' not in st.session_state:
    st.session_state.dati_aziendali = {}
if 'incassi' not in st.session_state:
    st.session_state.incassi = []

def pulisci_iban(iban):
    """Rimuove spazi dall'IBAN"""
    return re.sub(r'\s+', '', iban.upper())

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
    writer.writerow(['nome', 'cognome', 'iban', 'importo', 'causale', 'data_scadenza'])
    writer.writerow(['Mario', 'Rossi', 'IT60X0542811101000000654321', '150.00', 
                    'Pagamento servizio gennaio 2025', '2025-02-15'])
    writer.writerow(['Laura', 'Bianchi', 'IT28W8000000292100645211111', '250.50', 
                    'Abbonamento annuale', '2025-02-20'])
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

def valida_incassi(df):
    """Valida i dati degli incassi"""
    required_fields = ['nome', 'cognome', 'iban', 'importo', 'causale', 'data_scadenza']
    for field in required_fields:
        if field not in df.columns:
            return False, f"Campo mancante: {field}"
    
    for idx, row in df.iterrows():
        for field in required_fields:
            if pd.isna(row[field]) or str(row[field]).strip() == '':
                return False, f"Campo vuoto nella riga {idx+2}: {field}"
        
        # Valida importo
        try:
            float(row['importo'])
        except:
            return False, f"Importo non valido nella riga {idx+2}"
    
    return True, "OK"

def genera_xml_sepa(dati_aziendali, incassi):
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
    
    # Data richiesta (usa la prima data scadenza)
    data_richiesta = incassi[0]['data_scadenza']
    SubElement(pmt_inf, 'ReqdColltnDt').text = data_richiesta
    
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
        SubElement(mndt_rltd_inf, 'DtOfSgntr').text = '2024-01-01'
        
        # Debtor Agent
        dbtr_agt = SubElement(drct_dbt_tx_inf, 'DbtrAgt')
        dbtr_fin_instn_id = SubElement(dbtr_agt, 'FinInstnId')
        SubElement(dbtr_fin_instn_id, 'BIC').text = 'NOTPROVIDED'
        
        # Debtor
        dbtr = SubElement(drct_dbt_tx_inf, 'Dbtr')
        SubElement(dbtr, 'Nm').text = f"{incasso['nome']} {incasso['cognome']}"
        
        # Debtor Account
        dbtr_acct = SubElement(drct_dbt_tx_inf, 'DbtrAcct')
        dbtr_id = SubElement(dbtr_acct, 'Id')
        SubElement(dbtr_id, 'IBAN').text = pulisci_iban(incasso['iban'])
        
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
        key="aziendale"
    )

if uploaded_aziendale is not None:
    try:
        df_aziendale = pd.read_csv(uploaded_aziendale)
        valido, messaggio = valida_dati_aziendali(df_aziendale)
        
        if valido:
            st.session_state.dati_aziendali = df_aziendale.iloc[0].to_dict()
            st.success("✅ Dati Aziendali Caricati Correttamente!")
            
            with st.expander("🔍 Visualizza Dati Caricati"):
                st.write(f"**Nome Azienda:** {st.session_state.dati_aziendali['nome_azienda']}")
                st.write(f"**IBAN:** {st.session_state.dati_aziendali['iban']}")
                st.write(f"**Creditor ID:** {st.session_state.dati_aziendali['creditor_id']}")
        else:
            st.error(f"❌ Errore: {messaggio}")
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 2: CSV Incassi
st.header("💳 STEP 2: CSV Incassi")

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
        key="incassi"
    )

if uploaded_incassi is not None:
    try:
        df_incassi = pd.read_csv(uploaded_incassi)
        valido, messaggio = valida_incassi(df_incassi)
        
        if valido:
            st.session_state.incassi = df_incassi.to_dict('records')
            
            totale = sum(float(inc['importo']) for inc in st.session_state.incassi)
            
            st.success(f"✅ Caricati {len(st.session_state.incassi)} incassi!")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Numero Transazioni", len(st.session_state.incassi))
            with col_b:
                st.metric("Totale Incassi", f"€ {totale:.2f}")
            with col_c:
                st.metric("Media per Transazione", f"€ {totale/len(st.session_state.incassi):.2f}")
            
            with st.expander("🔍 Visualizza Dettaglio Incassi"):
                st.dataframe(df_incassi, use_container_width=True)
        else:
            st.error(f"❌ Errore: {messaggio}")
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 3: Generazione XML
st.header("🚀 STEP 3: Generazione XML SEPA")

if st.session_state.dati_aziendali and st.session_state.incassi:
    st.info("✅ Tutti i dati sono pronti! Puoi generare il file XML SEPA.")
    
    if st.button("🚀 Genera XML SEPA", type="primary", use_container_width=True):
        try:
            xml_content = genera_xml_sepa(
                st.session_state.dati_aziendali,
                st.session_state.incassi
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
    st.warning("⚠️ Carica prima i dati aziendali e gli incassi per generare il file XML.")

st.markdown("---")
st.info("ℹ️ Il file XML generato è compatibile con il formato SEPA pain.008.001.02 e pronto per essere caricato nel tuo sistema di home banking.")

# Footer
st.markdown("---")
st.caption("Generatore XML SEPA SDD v1.0 | Formato: pain.008.001.02")