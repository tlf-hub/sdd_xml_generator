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
    page_title="Generatore XML SEPA SDD CBI",
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
if 'id_flusso' not in st.session_state:
    st.session_state.id_flusso = None

def pulisci_iban(iban):
    """Rimuove spazi dall'IBAN"""
    return re.sub(r'\s+', '', iban.upper())

def normalizza_data(data_str):
    """Normalizza una data nel formato YYYY-MM-DD"""
    if pd.isna(data_str) or str(data_str).strip() == '':
        return datetime.now().strftime('%Y-%m-%d')
    
    data_str = str(data_str).strip()
    
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
    
    return datetime.now().strftime('%Y-%m-%d')

def normalizza_importo(importo_str):
    """Normalizza un importo nel formato xxxx.xx"""
    if pd.isna(importo_str):
        return "0.00"
    
    importo_str = str(importo_str).strip()
    importo_str = importo_str.replace(' ', '').replace(',', '.')
    
    try:
        importo_float = float(importo_str)
        return f"{importo_float:.2f}"
    except ValueError:
        return "0.00"

def aggrega_incassi(df):
    """Aggrega le righe per lo stesso debitore"""
    df_aggregato = df.groupby('iban').agg({
        'nome_debitore': 'first',
        'codice_fiscale': 'first',
        'importo': lambda x: sum(float(i) for i in x),
        'causale': lambda x: list(dict.fromkeys(x)),
        'data_firma_mandato': 'first'
    }).reset_index()
    
    df_aggregato['causale'] = df_aggregato['causale'].apply(
        lambda causali: "Ft. " + ", ".join(str(c) for c in causali)
    )
    
    df_aggregato['importo'] = df_aggregato['importo'].apply(lambda x: f"{x:.2f}")
    
    return df_aggregato

def genera_message_id(prefix):
    """Genera un Message ID"""
    timestamp = datetime.now().strftime('%H%M%S')
    return f"{prefix}{timestamp}"

def genera_end_to_end_id(msg_id, idx):
    """Genera un End-to-End ID"""
    return f"{msg_id}-{idx:07d}"

def genera_mandate_id(prefix, codice_fiscale):
    """Genera un Mandate ID basato sul CF"""
    return f"{prefix}{codice_fiscale}"

def crea_template_aziendale():
    """Crea il template CSV per i dati aziendali"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome_azienda', 'indirizzo_azienda', 'iban', 'abi', 'creditor_id', 'prefisso_mandato'])
    writer.writerow(['T.L.F. SRL', 'T.L.F. SRL', 'IT67R0569603211000011001X44', '05696', 'IT610010000006392981004', '9J3073'])
    return output.getvalue()

def crea_template_incassi():
    """Crea il template CSV per gli incassi"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['nome_debitore', 'codice_fiscale', 'iban', 'importo', 'causale', 'data_firma_mandato'])
    writer.writerow(['Amoruso Gennaro Maria', 'MRSGNR71M29C352M', 'IT13Z0558403204000000008289', '183.00', 
                    'Fattura 802/1 del 29/12/2025', '02/01/2012'])
    writer.writerow(['Amoruso Gennaro Maria', 'MRSGNR71M29C352M', 'IT13Z0558403204000000008289', '50.00', 
                    'Fattura 803/1 del 29/12/2025', '02/01/2012'])
    writer.writerow(['Arnone Gianluca', 'RNNGLC74C25C352J', 'IT45V0306942774100000005029', '116.91', 
                    'Fattura 805/1 del 29/12/2025', '05/03/2014'])
    return output.getvalue()

def valida_dati_aziendali(df):
    """Valida i dati aziendali"""
    required_fields = ['nome_azienda', 'indirizzo_azienda', 'iban', 'abi', 'creditor_id', 'prefisso_mandato']
    for field in required_fields:
        if field not in df.columns:
            return False, f"Campo mancante: {field}"
        if df[field].iloc[0] == '' or pd.isna(df[field].iloc[0]):
            return False, f"Campo vuoto: {field}"
    
    df['abi'] = df['abi'].astype(str).str.zfill(5)
    
    return True, "OK"

def processa_csv_incassi(df):
    """Processa il CSV degli incassi: normalizza date, importi e aggrega"""
    
    required_fields = ['nome_debitore', 'codice_fiscale', 'iban', 'importo', 'causale', 'data_firma_mandato']
    
    st.info(f"📊 CSV caricato: {len(df.columns)} colonne, {len(df)} righe")
    
    prima_colonna = str(df.columns[0]).lower().strip()
    
    if len(df.columns) == len(required_fields):
        colonne_valide = any(col.lower().strip() in ['nome_debitore', 'nome', 'debitore', 'codice_fiscale', 'iban', 'importo', 'causale', 'data_firma_mandato'] 
                           for col in df.columns)
        
        if not colonne_valide:
            df.columns = required_fields
            st.success("✅ Intestazioni colonne aggiunte automaticamente")
        else:
            mapping = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'nome' in col_lower or 'debitore' in col_lower:
                    mapping[col] = 'nome_debitore'
                elif 'codice' in col_lower or 'fiscale' in col_lower or 'cf' in col_lower or 'piva' in col_lower or 'partita' in col_lower:
                    mapping[col] = 'codice_fiscale'
                elif 'iban' in col_lower:
                    mapping[col] = 'iban'
                elif 'importo' in col_lower or 'ammontare' in col_lower or 'totale' in col_lower:
                    mapping[col] = 'importo'
                elif 'causale' in col_lower or 'descrizione' in col_lower or 'motivo' in col_lower:
                    mapping[col] = 'causale'
                elif 'data' in col_lower or 'firma' in col_lower or 'mandato' in col_lower:
                    mapping[col] = 'data_firma_mandato'
            
            if len(mapping) == len(required_fields):
                df = df.rename(columns=mapping)
                st.success("✅ Intestazioni colonne mappate automaticamente")
            else:
                df.columns = required_fields
                st.warning("⚠️ Alcune intestazioni non riconosciute, applicate intestazioni standard")
    else:
        return None, f"Il CSV deve avere {len(required_fields)} colonne, ne ha {len(df.columns)}"
    
    df['data_firma_mandato'] = df['data_firma_mandato'].apply(normalizza_data)
    df['importo'] = df['importo'].apply(normalizza_importo)
    
    for idx, row in df.iterrows():
        for field in ['nome_debitore', 'codice_fiscale', 'iban', 'importo', 'causale']:
            if pd.isna(row[field]) or str(row[field]).strip() == '':
                return None, f"Campo vuoto nella riga {idx+2}: {field}"
    
    df_aggregato = aggrega_incassi(df)
    
    return df_aggregato, "OK"

def genera_xml_cbi(dati_aziendali, incassi, data_addebito, id_flusso):
    """Genera il file XML SEPA SDD in formato CBI"""
    
    numero_transazioni = len(incassi)
    totale_importo = sum(float(inc['importo']) for inc in incassi)
    
    msg_id = genera_message_id(id_flusso)
    
    root = Element('CBIBdySDDReq')
    root.set('xmlns', 'urn:CBI:xsd:CBIBdySDDReq.00.01.00')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xsi:schemaLocation', 'urn:CBI:xsd:CBIBdySDDReq.00.01.00 CBIBdySDDReq.00.01.00.xsd')
    
    phy_msg_inf = SubElement(root, 'PhyMsgInf')
    SubElement(phy_msg_inf, 'PhyMsgTpCd').text = 'INC-SDDC-01'
    SubElement(phy_msg_inf, 'NbOfLogMsg').text = '1'
    
    cbi_envel = SubElement(root, 'CBIEnvelSDDReqLogMsg')
    cbi_sdd_req = SubElement(cbi_envel, 'CBISDDReqLogMsg')
    
    grp_hdr = SubElement(cbi_sdd_req, 'GrpHdr')
    grp_hdr.set('xmlns', 'urn:CBI:xsd:CBISDDReqLogMsg.00.01.00')
    
    SubElement(grp_hdr, 'MsgId').text = msg_id
    SubElement(grp_hdr, 'CreDtTm').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    SubElement(grp_hdr, 'NbOfTxs').text = str(numero_transazioni)
    SubElement(grp_hdr, 'CtrlSum').text = f'{totale_importo:.2f}'
    
    initg_pty = SubElement(grp_hdr, 'InitgPty')
    SubElement(initg_pty, 'Nm').text = dati_aziendali['nome_azienda']
    
    initg_pty_id = SubElement(initg_pty, 'Id')
    org_id = SubElement(initg_pty_id, 'OrgId')
    othr = SubElement(org_id, 'Othr')
    SubElement(othr, 'Id').text = id_flusso
    SubElement(othr, 'Issr').text = 'CBI'
    
    pmt_inf = SubElement(cbi_sdd_req, 'PmtInf')
    pmt_inf.set('xmlns', 'urn:CBI:xsd:CBISDDReqLogMsg.00.01.00')
    
    SubElement(pmt_inf, 'PmtInfId').text = 'SOTTODISTINTA1'
    SubElement(pmt_inf, 'PmtMtd').text = 'DD'
    
    pmt_tp_inf = SubElement(pmt_inf, 'PmtTpInf')
    svc_lvl = SubElement(pmt_tp_inf, 'SvcLvl')
    SubElement(svc_lvl, 'Cd').text = 'SEPA'
    lcl_instrm = SubElement(pmt_tp_inf, 'LclInstrm')
    SubElement(lcl_instrm, 'Cd').text = 'CORE'
    SubElement(pmt_tp_inf, 'SeqTp').text = 'RCUR'
    
    SubElement(pmt_inf, 'ReqdColltnDt').text = data_addebito
    
    cdtr = SubElement(pmt_inf, 'Cdtr')
    SubElement(cdtr, 'Nm').text = dati_aziendali['nome_azienda']
    
    pstl_adr = SubElement(cdtr, 'PstlAdr')
    SubElement(pstl_adr, 'Ctry').text = 'IT'
    SubElement(pstl_adr, 'AdrLine').text = dati_aziendali['indirizzo_azienda']
    
    cdtr_acct = SubElement(pmt_inf, 'CdtrAcct')
    cdtr_acct_id = SubElement(cdtr_acct, 'Id')
    SubElement(cdtr_acct_id, 'IBAN').text = pulisci_iban(dati_aziendali['iban'])
    
    cdtr_agt = SubElement(pmt_inf, 'CdtrAgt')
    fin_instn_id = SubElement(cdtr_agt, 'FinInstnId')
    clr_sys_mmb_id = SubElement(fin_instn_id, 'ClrSysMmbId')
    SubElement(clr_sys_mmb_id, 'MmbId').text = str(dati_aziendali['abi']).zfill(5)
    
    cdtr_schme_id = SubElement(pmt_inf, 'CdtrSchmeId')
    SubElement(cdtr_schme_id, 'Nm').text = dati_aziendali['nome_azienda']
    
    cdtr_schme_id_id = SubElement(cdtr_schme_id, 'Id')
    prvt_id = SubElement(cdtr_schme_id_id, 'PrvtId')
    othr_schme = SubElement(prvt_id, 'Othr')
    SubElement(othr_schme, 'Id').text = dati_aziendali['creditor_id']
    schme_nm = SubElement(othr_schme, 'SchmeNm')
    SubElement(schme_nm, 'Prtry').text = 'SEPA'
    
    for idx, incasso in enumerate(incassi, 1):
        drct_dbt_tx_inf = SubElement(pmt_inf, 'DrctDbtTxInf')
        
        pmt_id = SubElement(drct_dbt_tx_inf, 'PmtId')
        SubElement(pmt_id, 'InstrId').text = f'{idx:07d}'
        SubElement(pmt_id, 'EndToEndId').text = genera_end_to_end_id(msg_id, idx)
        
        instd_amt = SubElement(drct_dbt_tx_inf, 'InstdAmt')
        instd_amt.set('Ccy', 'EUR')
        instd_amt.text = f'{float(incasso["importo"]):.2f}'
        
        drct_dbt_tx = SubElement(drct_dbt_tx_inf, 'DrctDbtTx')
        mndt_rltd_inf = SubElement(drct_dbt_tx, 'MndtRltdInf')
        SubElement(mndt_rltd_inf, 'MndtId').text = genera_mandate_id(
            dati_aziendali['prefisso_mandato'], 
            incasso['codice_fiscale']
        )
        SubElement(mndt_rltd_inf, 'DtOfSgntr').text = incasso['data_firma_mandato']
        
        dbtr = SubElement(drct_dbt_tx_inf, 'Dbtr')
        SubElement(dbtr, 'Nm').text = incasso['nome_debitore']
        
        dbtr_id = SubElement(dbtr, 'Id')
        dbtr_org_id = SubElement(dbtr_id, 'OrgId')
        dbtr_othr = SubElement(dbtr_org_id, 'Othr')
        SubElement(dbtr_othr, 'Id').text = incasso['codice_fiscale']
        SubElement(dbtr_othr, 'Issr').text = 'ADE'
        
        dbtr_acct = SubElement(drct_dbt_tx_inf, 'DbtrAcct')
        dbtr_acct_id = SubElement(dbtr_acct, 'Id')
        SubElement(dbtr_acct_id, 'IBAN').text = pulisci_iban(incasso['iban'])
        
        rmt_inf = SubElement(drct_dbt_tx_inf, 'RmtInf')
        causale_completa = f"{idx:019d} - {incasso['causale']}"
        SubElement(rmt_inf, 'Ustrd').text = causale_completa
    
    xml_str = minidom.parseString(tostring(root)).toprettyxml(indent="", encoding="UTF-8")
    
    xml_lines = xml_str.decode('utf-8').split('\n')
    xml_lines = [line for line in xml_lines if line.strip()]
    xml_str = '\n'.join(xml_lines).encode('utf-8')
    
    return xml_str

# UI principale
st.title("💰 Generatore XML SEPA SDD CBI per Incassi Bancari")
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
        try:
            df_aziendale = pd.read_csv(uploaded_aziendale, encoding='utf-8')
        except UnicodeDecodeError:
            uploaded_aziendale.seek(0)
            try:
                df_aziendale = pd.read_csv(uploaded_aziendale, encoding='utf-8-sig')
            except UnicodeDecodeError:
                uploaded_aziendale.seek(0)
                try:
                    df_aziendale = pd.read_csv(uploaded_aziendale, encoding='latin-1')
                except UnicodeDecodeError:
                    uploaded_aziendale.seek(0)
                    df_aziendale = pd.read_csv(uploaded_aziendale, encoding='cp1252')
        
        valido, messaggio = valida_dati_aziendali(df_aziendale)
        
        if valido:
            st.session_state.dati_azienda_caricati = df_aziendale.iloc[0].to_dict()
            st.success("✅ Dati Aziendali Caricati Correttamente!")
            
            with st.expander("🔍 Visualizza Dati Caricati"):
                st.write(f"**Nome Azienda:** {st.session_state.dati_azienda_caricati['nome_azienda']}")
                st.write(f"**IBAN:** {st.session_state.dati_azienda_caricati['iban']}")
                st.write(f"**ABI:** {st.session_state.dati_azienda_caricati['abi']}")
                st.write(f"**Creditor ID:** {st.session_state.dati_azienda_caricati['creditor_id']}")
                st.write(f"**Prefisso Mandato:** {st.session_state.dati_azienda_caricati['prefisso_mandato']}")
        else:
            st.error(f"❌ Errore: {messaggio}")
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 2: Data Addebito e CSV Incassi
st.header("💳 STEP 2: ID Flusso, Data Addebito e CSV Incassi")

st.subheader("🆔 ID Flusso")
id_flusso_input = st.text_input(
    "Inserisci l'ID Flusso",
    value="",
    max_chars=20,
    help="ID univoco per identificare il flusso (es. FLX9J372). Può essere cambiato per ogni invio."
)

if id_flusso_input:
    st.session_state.id_flusso = id_flusso_input
    st.success(f"✅ ID Flusso impostato: {st.session_state.id_flusso}")

st.markdown("---")

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
        def rileva_separatore(file_obj):
            file_obj.seek(0)
            sample = file_obj.read(1024).decode('utf-8', errors='ignore')
            file_obj.seek(0)
            separatori = [',', ';', '\t', '|']
            conteggi = {sep: sample.count(sep) for sep in separatori}
            sep_migliore = max(conteggi, key=conteggi.get)
            return sep_migliore if conteggi[sep_migliore] > 0 else ','
        
        df_incassi = None
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                uploaded_incassi.seek(0)
                sep = rileva_separatore(uploaded_incassi)
                uploaded_incassi.seek(0)
                df_incassi = pd.read_csv(uploaded_incassi, encoding=encoding, sep=sep)
                st.info(f"🔍 Rilevato separatore: '{sep}' | Encoding: {encoding}")
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        
        if df_incassi is not None:
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
        else:
            st.error("❌ Impossibile leggere il file CSV. Verifica il formato del file.")
                
    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")

st.markdown("---")

# STEP 3: Generazione XML
st.header("🚀 STEP 3: Generazione XML SEPA CBI")

if st.session_state.dati_azienda_caricati and st.session_state.lista_incassi and st.session_state.data_addebito and st.session_state.id_flusso:
    st.info("✅ Tutti i dati sono pronti! Puoi generare il file XML SEPA CBI.")
    
    if st.button("🚀 Genera XML SEPA CBI", type="primary", use_container_width=True):
        try:
            xml_content = genera_xml_cbi(
                st.session_state.dati_azienda_caricati,
                st.session_state.lista_incassi,
                st.session_state.data_addebito,
                st.session_state.id_flusso
            )
            
            filename = f"SEPA_SDD_CBI_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
            
            st.download_button(
                label="💾 Scarica File XML",
                data=xml_content,
                file_name=filename,
                mime="application/xml",
                use_container_width=True
            )
            
            st.success("✅ File XML SEPA CBI generato con successo!")
            st.balloons()
            
            with st.expander("📄 Anteprima XML"):
                st.code(xml_content.decode('utf-8'), language='xml')
            
        except Exception as e:
            st.error(f"❌ Errore nella generazione del file XML: {str(e)}")
else:
    messaggi = []
    if not st.session_state.dati_azienda_caricati:
        messaggi.append("- Dati aziendali")
    if not st.session_state.id_flusso:
        messaggi.append("- ID Flusso")
    if not st.session_state.data_addebito:
        messaggi.append("- Data addebito")
    if not st.session_state.lista_incassi:
        messaggi.append("- CSV incassi")
    
    st.warning(f"⚠️ Completa i seguenti passaggi:\n" + "\n".join(messaggi))

st.markdown("---")
st.info("ℹ️ Il file XML generato è compatibile con il formato CBI (Corporate Banking Interbancario) e pronto per essere caricato nel tuo sistema di home banking.")

# Footer
st.markdown("---")
st.caption("Generatore XML SEPA SDD CBI v3.0 | Formato: CBIBdySDDReq.00.01.00 | Aggregazione automatica debitori")