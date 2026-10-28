import base64
import hashlib
import random
import secrets
import time
from datetime import datetime, date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Optional project dependencies. The dashboard remains usable if Qiskit is not installed,
# but quantum-circuit demonstrations will be marked as simulated fallback.
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import Aer
    QISKIT_AVAILABLE = True
except Exception:
    QISKIT_AVAILABLE = False

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except Exception:
    CRYPTO_AVAILABLE = False

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

# ------------------------------ Page and styling ------------------------------
st.set_page_config(page_title="QSB • Quantum Secure Banking", page_icon="⚛️", layout="wide", initial_sidebar_state="expanded")

st.markdown(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700;800&display=swap');
:root { --bg:#080d19; --panel:#111a2b; --line:#25344d; --cyan:#4de3e8; --violet:#9b8cff; --muted:#9baac1; }
.stApp { background: radial-gradient(ellipse at 12% 0%, #142342 0%, #080d19 45%, #070b14 100%); color:#edf4ff; font-family:Inter,sans-serif; }
[data-testid="stSidebar"] { background:#0b1220; border-right:1px solid #243149; }
[data-testid="stSidebar"] * { color:#eaf1ff; }
.block-container { padding-top:1.4rem; padding-bottom:3rem; max-width:1500px; }
h1,h2,h3 { letter-spacing:-.035em; }
.qsb-eyebrow { color:#4de3e8; font-family:'DM Mono',monospace; font-size:.75rem; letter-spacing:.17em; text-transform:uppercase; }
.qsb-title { font-size:2.25rem; font-weight:800; letter-spacing:-.06em; margin:.2rem 0 .3rem; }
.qsb-sub { color:#9baac1; margin-bottom:1.4rem; }
.metric-card { background:linear-gradient(145deg,rgba(21,33,54,.95),rgba(13,21,36,.95)); border:1px solid #263753; border-radius:16px; padding:18px 19px; min-height:115px; }
.metric-label { color:#9baac1; font-size:.79rem; margin-bottom:10px; }
.metric-value { color:#f4f7ff; font-size:1.75rem; font-weight:750; letter-spacing:-.04em; }
.metric-note { color:#4de3e8; font-size:.75rem; margin-top:6px; }
.panel { background:rgba(17,26,43,.78); border:1px solid #263753; border-radius:16px; padding:18px; }
.pill { display:inline-block; border:1px solid #31536b; border-radius:99px; padding:4px 9px; color:#70edf0; background:#102b37; font-size:.72rem; font-family:'DM Mono',monospace; }
.small-muted { color:#9baac1; font-size:.82rem; }
div[data-testid="stButton"] button { border-radius:10px; font-weight:650; border:1px solid #38516f; }
div[data-testid="stButton"] button[kind="primary"] { background:linear-gradient(90deg,#0f9ca8,#6b63df); border:0; color:white; }
[data-testid="stDataFrame"] { border:1px solid #263753; border-radius:12px; }
hr { border-color:#25344d; }
</style>
""", unsafe_allow_html=True)

# ------------------------------ Core demo logic ------------------------------
def init_state():
    defaults = {
        "user": "ayush", "authenticated": False, "balance": 10000.0,
        "transactions": [
            {"id":"TXN-001","time":"09:42:12","beneficiary":"Priya Stores","amount":1200,"status":"SUCCESS","risk":"LOW","category":"Shopping","note":"Demo opening transaction"},
            {"id":"TXN-002","time":"10:18:05","beneficiary":"Electricity Board","amount":2500,"status":"SUCCESS","risk":"LOW","category":"Bills","note":"Demo opening transaction"},
            {"id":"TXN-003","time":"11:06:31","beneficiary":"New Beneficiary","amount":7000,"status":"BLOCKED","risk":"HIGH","category":"Transfer","note":"High-value rule triggered"},
        ],
        "security_events": [], "generated_otp": None, "otp_expiry": 0,
        "login_attempts": 0, "account_locked": False, "active_case": None,
        "budget_overrides": {"Food":5000,"Shopping":4000,"Transport":2500,"Bills":5000,"Entertainment":2000,"Health":2500},
        "beneficiaries": {
            "Priya Stores":{"average":1200,"maximum":2200,"count":25},
            "Electricity Board":{"average":1800,"maximum":2500,"count":10},
            "Rahul Sharma":{"average":900,"maximum":1500,"count":18},
            "Family Account":{"average":3000,"maximum":8500,"count":8},
        },
        "incidents": []
    }
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

@st.cache_resource
def make_fraud_model():
    if not SKLEARN_AVAILABLE: return None
    training = np.array([[500,120],[1000,60],[200,300],[1500,90],[800,180],[300,240],[100,600],[2000,45],[600,150],[400,200]], dtype=float)
    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(training)
    return model

fraud_model = make_fraud_model()

def quantum_bits(n_bits=8):
    """Generate bits using a Qiskit Aer circuit when available; otherwise label fallback clearly."""
    if QISKIT_AVAILABLE:
        qc = QuantumCircuit(n_bits, n_bits)
        qc.h(range(n_bits))
        qc.measure(range(n_bits), range(n_bits))
        backend = Aer.get_backend("aer_simulator")
        compiled = transpile(qc, backend)
        result = backend.run(compiled, shots=1).result()
        bits = next(iter(result.get_counts().keys())).replace(" ", "")
        return bits[-n_bits:], qc.draw(output="text")
    return "".join(secrets.choice("01") for _ in range(n_bits)), "Qiskit not installed — secure-random fallback used for this demo."

def bb84_demo(n_bits=32, eve=False):
    alice_bits = [random.randint(0,1) for _ in range(n_bits)]
    alice_bases = [random.randint(0,1) for _ in range(n_bits)]
    bob_bases = [random.randint(0,1) for _ in range(n_bits)]
    eve_bases = [random.randint(0,1) for _ in range(n_bits)] if eve else None
    bob_results=[]
    for i in range(n_bits):
        sent = alice_bits[i]
        if eve and eve_bases[i] != alice_bases[i]: sent = random.randint(0,1)
        if bob_bases[i] == (eve_bases[i] if eve else alice_bases[i]):
            bob_results.append(sent)
        else:
            bob_results.append(random.randint(0,1))
    matched=[i for i in range(n_bits) if alice_bases[i] == bob_bases[i]]
    shared=[alice_bits[i] for i in matched]
    errors=sum(1 for i in matched if bob_results[i] != alice_bits[i])
    qber=(errors/len(matched)*100) if matched else 0
    return {"alice":"".join(map(str,alice_bits)),"alice_bases":"".join(map(str,alice_bases)),"bob_bases":"".join(map(str,bob_bases)),"key":"".join(map(str,shared)),"matched":len(matched),"errors":errors,"qber":qber,"eve":eve}

def encrypt_demo(text, key_bytes):
    if not CRYPTO_AVAILABLE: return "Unavailable: install pycryptodome", "", ""
    cipher=AES.new(key_bytes, AES.MODE_CBC)
    ciphertext=cipher.encrypt(pad(text.encode(), AES.block_size))
    return base64.b64encode(ciphertext).decode(), base64.b64encode(cipher.iv).decode(), cipher.decrypt(pad(text.encode(), AES.block_size))[:0].decode(errors="ignore")

def fraud_check(amount, seconds_since_last, beneficiary="", recent_count=0):
    reasons=[]; score=12
    if amount > 5000: reasons.append("Transfer exceeds ₹5,000 demo rule"); score += 45
    if seconds_since_last < 5: reasons.append("Unusually rapid transaction"); score += 25
    if beneficiary and beneficiary not in st.session_state.beneficiaries: reasons.append("New or unfamiliar beneficiary"); score += 18
    if fraud_model is not None:
        try:
            pred=int(fraud_model.predict([[float(amount), max(1,float(seconds_since_last))]])[0])
            if pred == -1: reasons.append("Isolation Forest flagged an anomaly"); score += 20
        except Exception: pass
    if recent_count >= 3: reasons.append("High transaction velocity"); score += 15
    score=min(99,score)
    return score, reasons

def money(x): return f"₹{x:,.0f}"

def header(kicker, title, subtitle):
    st.markdown(f'<div class="qsb-eyebrow">{kicker}</div><div class="qsb-title">{title}</div><div class="qsb-sub">{subtitle}</div>', unsafe_allow_html=True)

def metric(label, value, note=""):
    st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)

def log_event(event, status="INFO"):
    st.session_state.security_events.insert(0,{"time":datetime.now().strftime("%H:%M:%S"),"event":event,"status":status})

# ------------------------------ Sidebar navigation ------------------------------
with st.sidebar:
    st.markdown('<div class="qsb-eyebrow">QSB / LAB 01</div>', unsafe_allow_html=True)
    st.markdown("# ⚛️ QSB **Banking**")
    st.caption("Quantum-inspired secure banking demonstrator")
    st.markdown('<span class="pill">● DEMO ENVIRONMENT</span>', unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("NAVIGATION", ["Command Centre","Quantum Security Lab","Secure Banking","AI Fraud Detection","Personal Finance","Beneficiary Safety","Fraud Response Centre","System & About"], label_visibility="visible")
    st.markdown("---")
    st.markdown("**SESSION**")
    st.write("👤", st.session_state.user.title())
    st.write("💳", money(st.session_state.balance))
    if st.button("Reset demo session", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.caption("Research prototype • No real funds moved")

# ------------------------------ Command Centre ------------------------------
if page == "Command Centre":
    header("OVERVIEW / 00", "Quantum Secure Banking System", "A unified live simulation of quantum-assisted key generation, secure transfers and intelligent fraud response.")
    tx=pd.DataFrame(st.session_state.transactions)
    success=int((tx["status"]=="SUCCESS").sum()) if not tx.empty else 0
    blocked=int((tx["status"]=="BLOCKED").sum()) if not tx.empty else 0
    total=float(tx.loc[tx.status=="SUCCESS","amount"].sum()) if not tx.empty else 0
    a,b,c,d=st.columns(4)
    with a: metric("AVAILABLE BALANCE",money(st.session_state.balance),"Demo account")
    with b: metric("SUCCESSFUL TRANSFERS",str(success),"Session activity")
    with c: metric("BLOCKED / FLAGGED",str(blocked),"Security intervention")
    with d: metric("SECURITY MODULES","06","Quantum • AES • ML • Rules")
    st.write("")
    left,right=st.columns([1.35,1])
    with left:
        st.markdown("### Transaction activity")
        if not tx.empty:
            chart=tx.copy(); chart["amount"]=pd.to_numeric(chart["amount"])
            fig=px.bar(chart,x="id",y="amount",color="status",color_discrete_map={"SUCCESS":"#4de3e8","BLOCKED":"#ff6b8a"},template="plotly_dark",labels={"id":"Transaction","amount":"Amount (₹)","status":"Status"})
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=10,r=10,t=20,b=10),legend_title_text="")
            st.plotly_chart(fig,use_container_width=True)
        else: st.info("No transaction activity yet. Visit Secure Banking to run a transfer.")
    with right:
        st.markdown("### Security posture")
        checks=[("Quantum RNG",QISKIT_AVAILABLE,"Qiskit Aer simulator" if QISKIT_AVAILABLE else "Fallback mode"),("AES encryption",CRYPTO_AVAILABLE,"AES-CBC demo" if CRYPTO_AVAILABLE else "Install pycryptodome"),("ML anomaly model",fraud_model is not None,"Isolation Forest" if fraud_model is not None else "Rules-only mode"),("BB84 simulation",True,"Protocol demonstration")]
        for name,ok,desc in checks:
            st.markdown(f'<div class="panel" style="padding:12px 14px;margin-bottom:9px"><b>{"🟢" if ok else "🟠"} {name}</b><div class="small-muted">{desc}</div></div>',unsafe_allow_html=True)
    st.markdown("### Recent transaction ledger")
    if not tx.empty:
        show=tx[["id","time","beneficiary","amount","status","risk","category"]].copy()
        show["amount"]=show["amount"].map(money)
        st.dataframe(show,hide_index=True,use_container_width=True)
    else: st.info("Ledger is empty.")
    st.caption("All displayed balances and transactions are local demo data stored in the current Streamlit session.")

# ------------------------------ Quantum Security Lab ------------------------------
elif page == "Quantum Security Lab":
    header("QUANTUM LAYER / 01", "Quantum Security Lab", "Explore quantum-circuit randomness and a simplified BB84 key-distribution demonstration.")
    st.warning("Simulation only: Qiskit Aer models quantum circuits on a classical computer. This is not a live quantum-hardware connection or a production QKD link.")
    t1,t2,t3=st.tabs(["Random bit generator","BB84 key distribution","Randomness comparison"])
    with t1:
        st.markdown("### Hadamard measurement")
        n=st.slider("Number of measured bits",4,32,8,step=4,key="qrng_n")
        if st.button("Generate quantum-simulated bits",type="primary"):
            bits,circuit=quantum_bits(n); st.session_state.last_bits=bits; st.session_state.last_circuit=circuit; log_event(f"Generated {n} simulated random bits","OK")
        if "last_bits" in st.session_state:
            st.markdown("**Measured bit string**")
            st.code(st.session_state.last_bits,language="text")
            st.markdown("**Circuit representation**")
            st.code(st.session_state.last_circuit,language="text")
            st.caption("The circuit applies an H gate to each qubit before measurement.")
        st.markdown("### How it works")
        st.write("A Hadamard gate places each ideal qubit into an equal superposition of |0⟩ and |1⟩. Measurement produces a bit string in the simulator.")
    with t2:
        st.markdown("### BB84 protocol sandbox")
        eve=st.toggle("Simulate an intercept-resend eavesdropper (Eve)",value=False)
        nbits=st.slider("Transmission bits",16,128,32,step=16,key="bb84_n")
        if st.button("Run BB84 simulation",type="primary"):
            result=bb84_demo(nbits,eve); st.session_state.bb84_result=result; log_event("BB84 simulation run"+(" with Eve" if eve else " without Eve"),"ALERT" if eve else "OK")
        if "bb84_result" in st.session_state:
            r=st.session_state.bb84_result
            x1,x2,x3=st.columns(3)
            with x1: metric("MATCHED BASES",str(r["matched"]),"Sifted positions")
            with x2: metric("SIFTED KEY LENGTH",str(len(r["key"])),"Bits in demo key")
            with x3: metric("MEASURED QBER",f'{r["qber"]:.1f}%',"Illustrative error rate")
            st.write("**Alice bits**"); st.code(r["alice"])
            st.write("**Alice bases**"); st.code(r["alice_bases"])
            st.write("**Bob bases**"); st.code(r["bob_bases"])
            st.write("**Sifted demonstration key**"); st.code(r["key"] or "No matched positions")
            if eve: st.error("Eve mode is enabled. Compare the measured errors; this simplified teaching simulation is not a complete security proof.")
            else: st.success("Eve mode is off. This run is a protocol illustration, not a guarantee of a secure real-world channel.")
        st.caption("The BB84 implementation is a simplified educational model; it does not implement authenticated classical communication or full parameter-estimation/key-reconciliation procedures.")
    with t3:
        if st.button("Sample quantum-simulated and classical bits",type="primary"):
            qbits=[]
            for _ in range(25): qbits.extend(map(int,quantum_bits(8)[0]))
            cbits=[random.randint(0,1) for _ in range(200)]
            st.session_state.random_compare=pd.DataFrame([{"Generator":"Classical Python RNG","0 bits":cbits.count(0),"1 bits":cbits.count(1)},{"Generator":"Qiskit Aer / fallback","0 bits":qbits.count(0),"1 bits":qbits.count(1)}])
            log_event("Randomness comparison sampled","OK")
        if "random_compare" in st.session_state:
            df=st.session_state.random_compare
            fig=go.Figure()
            fig.add_bar(name="0 bits",x=df.Generator,y=df["0 bits"],marker_color="#4de3e8")
            fig.add_bar(name="1 bits",x=df.Generator,y=df["1 bits"],marker_color="#9b8cff")
            fig.update_layout(barmode="group",template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",yaxis_title="Count",margin=dict(l=10,r=10,t=15,b=10))
            st.plotly_chart(fig,use_container_width=True); st.dataframe(df,hide_index=True,use_container_width=True)
            st.caption("A single sample does not prove that one generator is more random or secure. Results naturally fluctuate.")

# ------------------------------ Secure Banking ------------------------------
elif page == "Secure Banking":
    header("TRANSACTION LAYER / 02", "Secure Banking", "Run a controlled transfer simulation with authentication, risk checks and encryption demonstration.")
    st.info("Demo credentials from the project: username `ayush`, password `1234`; username `admin`, password `0000`. Do not reuse these credentials outside this local demonstration.")
    with st.expander("Authentication simulator",expanded=not st.session_state.authenticated):
        with st.form("login_form"):
            username=st.text_input("Username",value="ayush")
            password=st.text_input("Password",type="password")
            submitted=st.form_submit_button("Verify credentials",type="primary")
        if submitted:
            valid={"ayush":hashlib.sha256("1234".encode()).hexdigest(),"admin":hashlib.sha256("0000".encode()).hexdigest()}
            if st.session_state.account_locked: st.error("Demo account locked after three failed attempts. Reset the demo session to try again.")
            elif valid.get(username)==hashlib.sha256(password.encode()).hexdigest():
                st.session_state.user=username; st.session_state.authenticated=False; st.session_state.login_attempts=0
                otp,_=quantum_bits(6); st.session_state.generated_otp=otp; st.session_state.otp_expiry=time.time()+180
                log_event(f"Login accepted for {username}; demo OTP generated","OK"); st.success("Credentials accepted. A demonstration OTP has been generated below.")
            else:
                st.session_state.login_attempts+=1; log_event("Failed login attempt","ALERT")
                if st.session_state.login_attempts>=3: st.session_state.account_locked=True; st.error("Account locked: maximum of three failed attempts reached.")
                else: st.error(f"Invalid credentials. {3-st.session_state.login_attempts} attempt(s) remaining.")
        if st.session_state.generated_otp:
            st.markdown("**Demo OTP** (shown here for classroom demonstration; a real system would deliver it through a separate trusted channel)")
            st.code(st.session_state.generated_otp)
            with st.form("otp_form"):
                entered=st.text_input("Enter the displayed demo OTP",max_chars=6)
                verify=st.form_submit_button("Verify OTP")
            if verify:
                if time.time()<=st.session_state.otp_expiry and entered==st.session_state.generated_otp:
                    st.session_state.authenticated=True; log_event("Demo OTP verified","OK"); st.success("OTP verified for this demo session.")
                else: st.error("OTP mismatch or expired.")
    st.markdown("### Make a demo transfer")
    st.metric("Current demo balance",money(st.session_state.balance))
    with st.form("transfer_form"):
        c1,c2=st.columns(2)
        with c1:
            beneficiary=st.text_input("Beneficiary / merchant",value="Priya Stores")
            amount=st.number_input("Transfer amount (₹)",min_value=1,max_value=1000000,value=1200,step=100)
        with c2:
            category=st.selectbox("Category",["Food","Shopping","Transport","Bills","Entertainment","Health","Transfer"])
            elapsed=st.number_input("Seconds since previous transaction",min_value=0,max_value=3600,value=100,step=5)
        otp_check=st.text_input("Demo OTP (optional if session already verified)",max_chars=6)
        pin_check=st.text_input("Extra transaction PIN for ₹3,000–₹5,000 transfers",max_chars=4)
        st.caption("For demonstration, use the OTP displayed in the authentication section. The extra PIN is generated when required and shown in the result after pressing submit.")
        go_transfer=st.form_submit_button("Analyse & process transfer",type="primary")
    if go_transfer:
        if not st.session_state.authenticated:
            st.error("Verify login and OTP first.")
        elif amount>st.session_state.balance:
            st.error("Insufficient demo balance.")
        elif st.session_state.generated_otp and time.time()<=st.session_state.otp_expiry and otp_check and otp_check!=st.session_state.generated_otp:
            st.error("OTP mismatch. Transfer not processed.")
        else:
            score,reasons=fraud_check(amount,elapsed,beneficiary)
            extra_pin_required=3000<=amount<=5000
            pin_ok=True
            if extra_pin_required:
                if not st.session_state.get("latest_pin"):
                    generated_pin,_=quantum_bits(4); st.session_state.latest_pin=generated_pin
                if pin_check!=st.session_state.latest_pin: pin_ok=False
            allowed=(score<65 and amount<=5000 and elapsed>=5 and pin_ok)
            txid=f"TXN-{len(st.session_state.transactions)+1:03d}"
            if allowed:
                st.session_state.balance-=float(amount)
                status="SUCCESS"; risk="LOW" if score<35 else "MEDIUM"
                if CRYPTO_AVAILABLE:
                    key_bits,_key_circuit=quantum_bits(128)
                    key=int(key_bits,2).to_bytes(16,"big")
                    cipher=AES.new(key,AES.MODE_CBC); ct=cipher.encrypt(pad(str(int(amount)).encode(),AES.block_size))
                    iv_b64=base64.b64encode(cipher.iv).decode(); ct_b64=base64.b64encode(ct).decode()
                    dec=unpad(AES.new(key,AES.MODE_CBC,base64.b64decode(iv_b64)).decrypt(base64.b64decode(ct_b64)),AES.block_size).decode()
                    st.success(f"Transfer approved. AES-CBC demo encryption/decryption verified: ₹{dec}.")
                    with st.expander("Encryption trace"):
                        st.write("Cipher: AES-128-CBC (demonstration)"); st.write("IV (Base64):"); st.code(iv_b64); st.write("Ciphertext (Base64):"); st.code(ct_b64); st.caption("The ephemeral key is not displayed or stored. Production systems should use authenticated encryption and robust key management.")
                else: st.success("Transfer approved by demo rules. Install pycryptodome to enable encryption trace.")
            else:
                status="BLOCKED"; risk="HIGH"; st.error("Transfer blocked by demo security controls.")
            if extra_pin_required and not pin_ok: st.warning(f"Extra PIN required. Demo PIN for this run: {st.session_state.latest_pin}")
            if reasons: st.write("**Risk signals:** " + " • ".join(reasons))
            st.progress(score/100,text=f"Illustrative risk score: {score}/100")
            st.session_state.transactions.insert(0,{"id":txid,"time":datetime.now().strftime("%H:%M:%S"),"beneficiary":beneficiary,"amount":int(amount),"status":status,"risk":risk,"category":category,"note":"; ".join(reasons) or "No demo rule triggered"})
            if status=="BLOCKED":
                st.session_state.incidents.insert(0,{"case_id":f"CASE-{datetime.now().strftime('%H%M%S')}","transaction_id":txid,"beneficiary":beneficiary,"amount":int(amount),"score":score,"status":"OPEN","reason":"; ".join(reasons) or "Additional PIN / rule check failed","time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            log_event(f"{status} {txid}: {money(amount)} to {beneficiary}","OK" if status=="SUCCESS" else "ALERT")
            st.rerun()
    if st.session_state.get("latest_pin"):
        st.caption("Most recent generated extra transaction PIN (demo display): " + st.session_state.latest_pin)
    st.markdown("### Transaction ledger")
    st.dataframe(pd.DataFrame(st.session_state.transactions),hide_index=True,use_container_width=True)

# ------------------------------ Fraud Detection ------------------------------
elif page == "AI Fraud Detection":
    header("RISK ENGINE / 03", "AI Fraud Detection", "Test the project's rule-based checks and Isolation Forest anomaly model with adjustable transaction inputs.")
    c1,c2=st.columns([1,1])
    with c1:
        with st.form("fraud_form"):
            amount=st.number_input("Transaction amount (₹)",min_value=1,max_value=1000000,value=7000,step=500)
            gap=st.slider("Seconds since previous transfer",0,600,3)
            beneficiary=st.text_input("Beneficiary",value="New Beneficiary")
            recent=st.slider("Transactions in the last 10 minutes",0,10,1)
            run=st.form_submit_button("Run fraud analysis",type="primary")
    with c2:
        st.markdown("### Model components")
        st.markdown('<div class="panel"><b>01 / Rule engine</b><p class="small-muted">High transfer amount and rapid transaction checks.</p><b>02 / Isolation Forest</b><p class="small-muted">Flags feature combinations that differ from the small demo training set.</p><b>03 / Beneficiary context</b><p class="small-muted">Adds risk for an unfamiliar payee and high recent transaction velocity.</p></div>',unsafe_allow_html=True)
    if run:
        score,reasons=fraud_check(amount,gap,beneficiary,recent)
        decision="BLOCK" if score>=65 or amount>5000 or gap<5 else "REVIEW" if score>=35 else "ALLOW"
        st.markdown("---")
        m1,m2,m3=st.columns(3)
        with m1: metric("RISK SCORE",f"{score}/100","Illustrative composite score")
        with m2: metric("MODEL OUTPUT","ANOMALY" if fraud_model is not None and fraud_model.predict([[float(amount),max(1,float(gap))]])[0]==-1 else "NO ANOMALY","Isolation Forest result")
        with m3: metric("DEMO DECISION",decision,"Rules + risk signals")
        st.progress(score/100)
        if reasons:
            for reason in reasons: st.warning(reason)
        else: st.success("No configured demo risk signal was triggered.")
        log_event(f"Fraud analysis: {decision} for {money(amount)}","ALERT" if decision=="BLOCK" else "OK")
    st.caption("The displayed score is a classroom-oriented heuristic, not a calibrated probability of fraud. The training set is small and synthetic.")

# ------------------------------ Personal Finance ------------------------------
elif page == "Personal Finance":
    header("CUSTOMER INTELLIGENCE / 04", "Personal Finance Insights", "Explore category-level spending, adjust budgets and view automated budget alerts using editable demonstration data.")
    demo=[
        ("2026-10-02","Food","Groceries",1200),("2026-10-05","Food","Restaurant",850),("2026-10-11","Food","Groceries",1250),("2026-10-20","Food","Food delivery",900),
        ("2026-10-06","Shopping","Clothing",1600),("2026-10-18","Shopping","Accessories",1000),("2026-10-03","Transport","Fuel",500),("2026-10-09","Transport","Cab fare",600),("2026-10-21","Transport","Fuel",700),
        ("2026-10-04","Bills","Electricity bill",2500),("2026-10-15","Bills","Internet bill",1400),("2026-10-12","Entertainment","Movie",800),("2026-10-19","Entertainment","Games",600),("2026-10-08","Health","Pharmacy",650)]
    if "finance_data" not in st.session_state:
        st.session_state.finance_data=pd.DataFrame(demo,columns=["Date","Category","Description","Amount"])
    df=st.session_state.finance_data.copy()
    with st.expander("Add a demo expense",expanded=False):
        with st.form("expense_form"):
            x1,x2=st.columns(2)
            with x1: edate=st.date_input("Date",value=date.today()); ecat=st.selectbox("Category",["Food","Shopping","Transport","Bills","Entertainment","Health"])
            with x2: edesc=st.text_input("Description",value="New expense"); eamount=st.number_input("Amount (₹)",min_value=1,max_value=100000,value=500,step=50)
            add=st.form_submit_button("Add expense")
        if add:
            new=pd.DataFrame([[edate.isoformat(),ecat,edesc,int(eamount)]],columns=["Date","Category","Description","Amount"])
            st.session_state.finance_data=pd.concat([st.session_state.finance_data,new],ignore_index=True); st.success("Expense added to this session."); st.rerun()
    df["Amount"]=pd.to_numeric(df["Amount"])
    total=df.Amount.sum(); budget_total=sum(st.session_state.budget_overrides.values()); remaining=budget_total-total
    a,b,c=st.columns(3)
    with a: metric("TOTAL SPENDING",money(total),"Demo transaction dataset")
    with b: metric("MONTHLY BUDGET",money(budget_total),"Editable category budgets")
    with c: metric("BUDGET REMAINING",money(remaining),"Across all listed categories")
    left,right=st.columns([1.2,1])
    with left:
        bycat=df.groupby("Category",as_index=False).Amount.sum().sort_values("Amount",ascending=False)
        fig=px.pie(bycat,names="Category",values="Amount",hole=.66,template="plotly_dark")
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=5,r=5,t=10,b=10),legend_title_text="Category")
        st.plotly_chart(fig,use_container_width=True)
    with right:
        st.markdown("### Budget controls")
        for cat,old in list(st.session_state.budget_overrides.items()):
            st.session_state.budget_overrides[cat]=st.number_input(f"{cat} budget (₹)",min_value=0,max_value=100000,value=int(old),step=250,key=f"budget_{cat}")
    spend=bycat.set_index("Category").Amount.to_dict()
    budget_rows=[]
    for cat,bud in st.session_state.budget_overrides.items():
        actual=float(spend.get(cat,0)); pct=(actual/bud*100) if bud else (100 if actual else 0)
        status="OVER BUDGET" if actual>bud else "NEAR LIMIT" if pct>=80 else "ON TRACK"
        budget_rows.append({"Category":cat,"Spent":actual,"Budget":bud,"Used %":round(pct,1),"Status":status})
    bdf=pd.DataFrame(budget_rows)
    st.markdown("### Budget utilization")
    fig=px.bar(bdf,x="Category",y="Used %",color="Status",text="Used %",color_discrete_map={"OVER BUDGET":"#ff6b8a","NEAR LIMIT":"#ffcc70","ON TRACK":"#4de3e8"},template="plotly_dark")
    fig.add_hline(y=100,line_dash="dash",line_color="#ff6b8a")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=5,r=5,t=10,b=10),yaxis_title="Budget used (%)")
    st.plotly_chart(fig,use_container_width=True)
    for _,r in bdf.iterrows():
        if r.Status=="OVER BUDGET": st.error(f"{r.Category}: spending exceeded budget by {money(r.Spent-r.Budget)}.")
        elif r.Status=="NEAR LIMIT": st.warning(f"{r.Category}: {r['Used %']:.1f}% of budget used.")
    st.markdown("### Expense records")
    st.dataframe(df,hide_index=True,use_container_width=True)
    st.download_button("Download expense data (CSV)",df.to_csv(index=False).encode(),file_name="qsb_demo_expenses.csv",mime="text/csv")

# ------------------------------ Beneficiary Safety ------------------------------
elif page == "Beneficiary Safety":
    header("PAYEE TRUST / 05", "Smart Beneficiary Safety Check", "Assess a transfer using the known-payee profile, historical amount range and transaction velocity.")
    profiles=st.session_state.beneficiaries
    st.markdown("### Known beneficiary profiles")
    prof=pd.DataFrame([{"Beneficiary":k,"Typical transfer (₹)":v["average"],"Historical max (₹)":v["maximum"],"Past transactions":v["count"]} for k,v in profiles.items()])
    st.dataframe(prof,hide_index=True,use_container_width=True)
    with st.form("beneficiary_form"):
        name=st.text_input("Beneficiary name",value="New Beneficiary")
        amount=st.number_input("Transfer amount (₹)",min_value=1,max_value=1000000,value=15000,step=500)
        recent=st.slider("Transactions to this beneficiary in last 10 minutes",0,10,0)
        analyse=st.form_submit_button("Run beneficiary safety check",type="primary")
    if analyse:
        profile=profiles.get(name)
        reasons=[]; score=10
        if not profile: reasons.append("Beneficiary is not in the known list"); score+=35
        elif amount>profile["maximum"]: reasons.append("Amount exceeds the beneficiary's historical maximum"); score+=30
        elif amount>profile["average"]*2: reasons.append("Amount is more than twice the typical transfer"); score+=20
        if amount>5000: reasons.append("High-value transfer rule triggered"); score+=25
        if recent>=3: reasons.append("Rapid repeat transfers detected"); score+=20
        score=min(99,score); decision="ADDITIONAL VERIFICATION" if score>=55 else "REVIEW" if score>=30 else "LOW RISK"
        a,b=st.columns(2)
        with a: metric("BENEFICIARY RISK",f"{score}/100","Heuristic score")
        with b: metric("RECOMMENDATION",decision,"Not a guarantee")
        if reasons:
            for reason in reasons: st.warning(reason)
        else: st.success("No configured beneficiary risk signal was triggered.")
        st.info("Suggested next step: verify beneficiary details independently before authorizing an unfamiliar or unusually large payment.")
        log_event(f"Beneficiary check for {name}: {decision}","ALERT" if score>=55 else "OK")
    st.caption("This is a rule-based safety demonstration; beneficiary records are local sample data and are not connected to a bank.")

# ------------------------------ Fraud Response Centre ------------------------------
elif page == "Fraud Response Centre":
    header("INCIDENT MANAGEMENT / 06", "Customer Fraud Response Centre", "Record a disputed transfer, simulate a protective hold and track incident status for the presentation.")
    st.info("Payment holds and disputes here are simulated. No real payment network is connected.")
    with st.form("incident_form"):
        c1,c2=st.columns(2)
        with c1:
            case_id=st.text_input("Incident case ID",value=f"CASE-{datetime.now().strftime('%y%m%d')}-001")
            txn_id=st.text_input("Transaction ID",value="TXN-003")
            merchant=st.text_input("Beneficiary / merchant",value="New Beneficiary")
        with c2:
            amount=st.number_input("Transaction amount (₹)",min_value=1,max_value=100000000,value=15000,step=500)
            score=st.slider("Fraud risk score",0,100,90)
            customer_action=st.radio("Customer response",["I recognise this transaction","I do NOT recognise this transaction"],index=1)
        notes=st.text_area("Additional details",value="Customer reported suspicious activity during demonstration.")
        submit=st.form_submit_button("Create incident record",type="primary")
    if submit:
        disputed=customer_action.startswith("I do NOT")
        item={"case_id":case_id,"transaction_id":txn_id,"beneficiary":merchant,"amount":int(amount),"score":score,"status":"PAYMENT HOLD SIMULATED" if disputed or score>=70 else "UNDER REVIEW","reason":notes,"customer_response":customer_action,"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        st.session_state.incidents.insert(0,item); log_event(f"Incident {case_id} created", "ALERT" if disputed or score>=70 else "INFO")
        if disputed or score>=70: st.error("Incident flagged. A protective hold is simulated for this demonstration.")
        else: st.success("Incident recorded for review.")
    st.markdown("### Incident queue")
    if st.session_state.incidents:
        idf=pd.DataFrame(st.session_state.incidents)
        st.dataframe(idf,hide_index=True,use_container_width=True)
        csv=idf.to_csv(index=False).encode()
        st.download_button("Export incident queue (CSV)",csv,file_name="qsb_incidents.csv",mime="text/csv")
        choices=[x["case_id"] for x in st.session_state.incidents]
        selected=st.selectbox("Update incident status",choices)
        new_status=st.selectbox("New status",["OPEN","INVESTIGATING","CUSTOMER CONTACTED","RESOLVED - DEMO"])
        if st.button("Update selected incident"):
            for item in st.session_state.incidents:
                if item["case_id"]==selected: item["status"]=new_status
            log_event(f"Incident {selected} status changed to {new_status}","INFO"); st.success("Incident status updated for this session."); st.rerun()
    else: st.info("No incidents recorded yet. Submit the form above to create a case.")
    st.markdown("### Recommended response workflow")
    st.markdown("1. Confirm whether the customer recognises the transaction.\n2. Simulate a protective hold when the transaction is disputed or high-risk.\n3. Record case details and preserve the transaction reference.\n4. Contact the customer through a verified channel and escalate according to bank policy.")

# ------------------------------ System & About ------------------------------
elif page == "System & About":
    header("SYSTEM INFORMATION / 07", "Architecture & Demonstration Notes", "A presentation-ready map of the modules included in this unified application.")
    modules=[
        ("Quantum random number generation","Qiskit QuantumCircuit + Hadamard gates + measurement on Aer simulator."),
        ("BB84 QKD demonstration","Random Alice/Bob bases, basis sifting, optional simplified intercept-resend Eve mode and measured error rate."),
        ("Encryption demonstration","AES-128-CBC using PyCryptodome, with a displayed IV/ciphertext and local decryption verification."),
        ("Authentication","SHA-256 comparison against demo credentials, three-attempt lockout and demonstration OTP flow."),
        ("Fraud detection","Isolation Forest on a small synthetic dataset plus explicit high-value and rapid-transfer rules."),
        ("Finance insights","Editable expense dataset, category charts, budget utilization alerts and CSV export."),
        ("Beneficiary safety","Known-payee profiles, unusual amount checks and velocity warnings."),
        ("Fraud response","Incident records, simulated protective holds, status updates and CSV export."),
    ]
    for i,(name,desc) in enumerate(modules,1):
        st.markdown(f'<div class="panel" style="margin-bottom:10px"><span class="pill">MODULE {i:02d}</span><h4 style="margin:.55rem 0 .25rem">{name}</h4><div class="small-muted">{desc}</div></div>',unsafe_allow_html=True)
    st.markdown("### Runtime dependency status")
    status=pd.DataFrame([{"Component":"Qiskit + Qiskit Aer","Available":QISKIT_AVAILABLE,"Purpose":"Quantum circuit simulation"},{"Component":"PyCryptodome","Available":CRYPTO_AVAILABLE,"Purpose":"AES encryption demonstration"},{"Component":"scikit-learn","Available":SKLEARN_AVAILABLE,"Purpose":"Isolation Forest model"},{"Component":"Plotly","Available":True,"Purpose":"Interactive charts"}])
    st.dataframe(status,hide_index=True,use_container_width=True)
    st.markdown("### Security and academic limitations")
    st.warning("This is a teaching prototype. It uses synthetic data, demo credentials, session-only state and simplified protocol models. Do not use it to handle real accounts, credentials, payments or sensitive customer information.")
    st.markdown("- The BB84 module is an educational simplification, not a complete QKD implementation.\n- Qiskit Aer is a classical simulator; it does not demonstrate quantum hardware access.\n- AES-CBC is used to match the project demonstration; a production design should prefer authenticated encryption such as AES-GCM and a proper key-management system.\n- The fraud model is trained on a tiny synthetic sample and its score is not a calibrated probability.\n- Data and incident updates are stored in Streamlit session state and may disappear when the session resets.")

# ------------------------------ Global footer and event trail ------------------------------
st.markdown("---")
with st.expander("Security event trail",expanded=False):
    if st.session_state.security_events:
        st.dataframe(pd.DataFrame(st.session_state.security_events),hide_index=True,use_container_width=True)
    else: st.caption("No events recorded in this session yet.")
st.markdown('<div class="small-muted" style="text-align:center;padding:12px 0">QSB • Quantum Secure Banking System · Academic simulation · No real financial services connected</div>',unsafe_allow_html=True)
