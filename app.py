import os
import sys
import io

# Force stdout/stderr to use UTF-8 on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()  # Load .env credentials before anything else
import re
import sqlite3
import random
import time
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit

# Import modules
from modules.currency_detector import detect_note, analyze_banknote
from modules.scam_classifier import classify_text, transcribe_audio, train_scam_model
from modules.fraud_graph import analyze_transactions, generate_interactive_graph, generate_pdf_report, generate_mock_transactions_csv
from modules.call_simulator import (simulate_incoming_call, analyze_spoof_indicators, print_terminal_metadata,
                                     generate_whatsapp_alert, generate_telecom_flag, generate_mha_report,
                                     append_audit_log, print_response_actions, send_real_whatsapp_alert)

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DB_PATH = os.path.join(DATA_DIR, 'complaints.db')
MODEL_PATH = os.path.join(MODELS_DIR, 'scam_model.pkl')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Initialize Flask & SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hackathon_super_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            module_type TEXT,
            status TEXT,
            details TEXT,
            risk_score REAL,
            amount_protected REAL
        )
    ''')
    # If empty, pre-populate with mock data for visuals
    c.execute("SELECT COUNT(*) FROM complaints")
    if c.fetchone()[0] == 0:
        mock_data = [
            ("Scam Call", "SCAM", "CBI Impersonation call flagged in Delhi. Digital arrest threat neutralized.", 94.2, 350000.0),
            ("Counterfeit Note", "FAKE", "Rs 500 note flagged at bank vault. Missing security thread.", 83.5, 500.0),
            ("Fraud Graph", "MULE", "Loop anomaly flagged. Money mule chain moving Rs 2,49,000 to accounts.", 88.0, 249000.0),
            ("Scam Call", "SCAM", "KYC suspension alert SMS targeting SBI cardholder.", 78.9, 85000.0),
            ("Counterfeit Note", "FAKE", "Rs 200 note flagged at retail counter. Low-quality ink shift.", 75.0, 200.0)
        ]
        c.executemany('''
            INSERT INTO complaints (module_type, status, details, risk_score, amount_protected) 
            VALUES (?, ?, ?, ?, ?)
        ''', mock_data)
        conn.commit()
    conn.close()

def get_stats():
    """Queries total stats from database for dashboard cards."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Complaints today
        c.execute("SELECT COUNT(*) FROM complaints")
        total_complaints = c.fetchone()[0]
        
        # Fraud detected
        c.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('SCAM', 'FAKE', 'MULE')")
        fraud_count = c.fetchone()[0]
        
        # Amount protected
        c.execute("SELECT SUM(amount_protected) FROM complaints")
        amt_protected = c.fetchone()[0] or 0.0
        
        conn.close()
        return {
            "complaints_today": total_complaints,
            "fraud_detected": fraud_count,
            "amount_protected": f"Rs {amt_protected:,.2f}"
        }
    except Exception as e:
        print(f"DB Stat reading error: {e}")
        return {
            "complaints_today": 5,
            "fraud_detected": 5,
            "amount_protected": "Rs 684,700.00"
        }

def add_complaint_log(module_type, status, details, risk_score, amount):
    """Inserts a new complaint log into SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO complaints (module_type, status, details, risk_score, amount_protected)
            VALUES (?, ?, ?, ?, ?)
        ''', (module_type, status, details, risk_score, amount))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging complaint: {e}")


# SocketIO Background Ticker Thread
# Emits real-time simulated cyber alerts to frontend every 8-12 seconds
def background_alert_ticker():
    alert_templates = [
        "ALERT: Suspected CBI Digital Arrest call flagged in Mumbai. Incident reported.",
        "ALERT: ATM Vault in Kolkata reported 3 counterfeit Rs 500 banknotes. Scanning signature updated.",
        "ALERT: Bank Fraud Detection Engine flagged rapid cycling loop of Rs 1,80,000 in HDFC Accounts.",
        "ALERT: Phishing SMS signature detected: 'Aadhaar update required, click link to prevent cell block'.",
        "ALERT: Large cash transaction alert: Rs 5,00,000 pooled from 4 victims into suspected Noida mule node.",
        "ALERT: WhatsApp Stock VIP Group fraud reported in Pune. UPI target account blocked.",
        "ALERT: Counterfeit Rs 200 banknote detected at petrol pump in Delhi. Serial pattern 9BC 549301.",
        "ALERT: KYC Suspended warning call classifier triggered. Risk score: 87.5% scam probability.",
        "ALERT: Customs Department parcel fraud reported. Victim stayed on call for 3 hours. Account secured."
    ]
    
    while True:
        socketio.sleep(random.randint(8, 14))
        alert = random.choice(alert_templates)
        socketio.emit('new_alert', {
            'message': alert,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

# Initialize background task on connection
@socketio.on('connect')
def handle_connect():
    print("Dashboard client connected.")
    emit('status', {'msg': 'Connected to live feed.'})


# ROUTES
@app.route('/')
def index():
    stats = get_stats()
    # Read latest logs to render initial table
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, module_type, status, details, risk_score, amount_protected FROM complaints ORDER BY id DESC LIMIT 5")
    logs = []
    for r in c.fetchall():
        logs.append({
            "timestamp": r[0],
            "type": r[1],
            "status": r[2],
            "details": r[3],
            "score": r[4],
            "amount": f"Rs {r[5]:,}"
        })
    conn.close()
    return render_template('index.html', stats=stats, logs=logs)


@app.route('/detect-currency', methods=['POST'])
def detect_currency():
    """Processes uploaded banknote file or webcam JSON base64 frame, runs CV pipeline, logs fake notes, and alerts user."""
    try:
        filename_hint = ""
        image_input = None
        
        # Check if JSON payload (webcam frame)
        if request.is_json and 'frame' in request.json:
            frame_data = request.json['frame']
            image_input = frame_data
            filename_hint = "webcam_capture.jpg"
        # Otherwise check if file upload
        elif 'note' in request.files:
            file = request.files['note']
            if file.filename == '':
                return jsonify({"error": "No file selected"}), 400
                
            os.makedirs("uploads", exist_ok=True)
            path = f"uploads/{file.filename}"
            file.save(path)
            image_input = path
            filename_hint = file.filename
        else:
            return jsonify({"error": "No note image file or webcam frame received"}), 400
            
        result = analyze_banknote(image_input, filename_hint)
        
        if "error" in result:
            return jsonify(result), 500

        # Log to database and alert if counterfeit (FAKE / SUSPECTED FAKE) and is a supported denomination
        if result["status"] != "REAL" and result["denomination"] != "Unsupported denomination":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO complaints (module_type, status, details, risk_score, amount_protected) VALUES (?, ?, ?, ?, ?)",
                      ("Currency Authenticator", result["status"], f"Fake {result['denomination']} note detected. Confidence: {result['confidence']}%", 85.0, 0.0))
            conn.commit()
            conn.close()
            
            # Emit SocketIO alert
            socketio.emit('new_alert', {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'message': f"ATM Vault reported fake {result['denomination']} banknote scanned."
            })

        # Dashboard JS compatibility mapping:
        denom_val = None
        if "500" in result["denomination"]:
            denom_val = 500
        elif "200" in result["denomination"]:
            denom_val = 200
        elif "100" in result["denomination"]:
            denom_val = 100

        ui_result = {
            "denomination": denom_val if denom_val else result["denomination"],
            "status": "DETECTED" if result["status"] == "REAL" else "NOT DETECTED",
            "verdict": result["status"],
            "confidence": result["confidence"],
            "checks_passed": result["checks_passed"],
            "total_checks": result["total_checks"],
            "features": result["features"],
            "annotated_img": result["annotated_img"]
        }
        
        return jsonify(ui_result)
        
    except Exception as e:
        print(f"Currency detection error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/classify_scam', methods=['POST'])
def classify_scam():
    """Classifies call text transcript or WAV/MP3 audio."""
    try:
        text = request.form.get('text', '')
        
        # 1. Check if audio file uploaded
        if 'audio' in request.files:
            audio_file = request.files['audio']
            # Save audio temporarily
            temp_path = os.path.join(DATA_DIR, f"temp_{int(time.time())}_{audio_file.filename}")
            audio_file.save(temp_path)
            
            # Transcribe
            text = transcribe_audio(temp_path)
            
            # Clean temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        if not text:
            return jsonify({"error": "No text or audio file supplied"}), 400
            
        # Classify text
        result = classify_text(text)
        result["transcript"] = text
        
        # Log if Scam
        if result["label"] == "SCAM":
            # Default mock amount
            amt_protected = 150000.0
            # Try to read amount from text
            amt_match = re.search(r'(\d+)\s*(?:thousand|lakh|rupees|inr|rs)', text.lower())
            if amt_match:
                try:
                    amt_protected = float(amt_match.group(1).replace(',', ''))
                    if "lakh" in text.lower():
                        amt_protected *= 100000
                except ValueError:
                    pass
                    
            add_complaint_log(
                "Scam Call", 
                "SCAM", 
                f"Call classified as {result['category']}. Impersonation suspected.", 
                result['risk_score'], 
                amt_protected
            )
            
            # Emit SocketIO alert
            socketio.emit('new_alert', {
                'message': f"ALERT: High Risk {result['category']} (Risk: {result['risk_score']}%) neutralized.",
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })
            
        return jsonify(result)

    except Exception as e:
        print(f"Scam classification error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/visualize_graph', methods=['POST'])
def visualize_graph():
    """Accepts uploaded transactions CSV, executes graph models, renders PyVis view."""
    try:
        if 'csv_file' not in request.files:
            return jsonify({"error": "No CSV file uploaded"}), 400
            
        csv_file = request.files['csv_file']
        csv_path = os.path.join(DATA_DIR, "uploaded_transactions.csv")
        csv_file.save(csv_path)
        
        # Process and build graph
        G, anom_df, cycling_paths = analyze_transactions(csv_path)
        
        # Generate PyVis visualization file
        html_out_path = os.path.join(STATIC_DIR, "fraud_graph.html")
        generate_interactive_graph(G, anom_df, html_out_path)
        
        # Save accounts report to pkl for report download
        report_cache = os.path.join(DATA_DIR, "latest_graph_analysis.pkl")
        import pickle
        with open(report_cache, 'wb') as f:
            pickle.dump((anom_df, cycling_paths), f)
            
        # Log to Database for high-risk mule count
        mule_count = len(anom_df[anom_df['risk_score'] >= 70])
        total_vol = anom_df['in_volume'].sum()
        
        if mule_count > 0:
            add_complaint_log(
                "Fraud Graph", 
                "MULE", 
                f"Analyzed {len(anom_df)} nodes. Flagged {mule_count} money mule nodes and {len(cycling_paths)} chains.", 
                90.0, 
                total_vol * 0.1 # Estimate 10% volume saved by block
            )
            
            # Emit SocketIO alert
            socketio.emit('new_alert', {
                'message': f"CRITICAL: Graph Analyzer flagged {mule_count} money-mule nodes in ledger.",
                'timestamp': datetime.now().strftime("%H:%M:%S")
            })

        # Return table payload for frontend display
        table_rows = anom_df.to_dict(orient='records')
        
        return jsonify({
            "nodes_count": len(G.nodes()),
            "edges_count": len(G.edges()),
            "flagged_count": mule_count,
            "total_volume": float(total_vol),
            "accounts": table_rows
        })

    except Exception as e:
        print(f"Graph analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/download_report', methods=['GET'])
def download_report():
    """Triggers download of the latest PDF evidence package report."""
    try:
        report_cache = os.path.join(DATA_DIR, "latest_graph_analysis.pkl")
        if not os.path.exists(report_cache):
            # Generate sample data and run to make sure a report exists
            sample_csv = os.path.join(DATA_DIR, "sample_transactions.csv")
            if not os.path.exists(sample_csv):
                generate_mock_transactions_csv(sample_csv)
            G, anom_df, cycling_paths = analyze_transactions(sample_csv)
            # Cache it
            import pickle
            with open(report_cache, 'wb') as f:
                pickle.dump((anom_df, cycling_paths), f)
                
        import pickle
        with open(report_cache, 'rb') as f:
            anom_df, cycling_paths = pickle.load(f)
            
        pdf_path = os.path.join(DATA_DIR, "evidence_package.pdf")
        generate_pdf_report(anom_df, cycling_paths, pdf_path)
        
        return send_file(pdf_path, as_attachment=True, download_name="Fraud_Shield_Evidence_Report.pdf")

    except Exception as e:
        print(f"Report download error: {e}")
        return f"Error compiling report: {e}", 500


@app.route('/download_scam_pdf', methods=['POST'])
def download_scam_pdf():
    """Generates a PDF download of the MHA Scam complaint draft."""
    try:
        data = request.json
        complaint_text = data.get('complaint_text', '')
        
        if not complaint_text:
            return "No content", 400
            
        pdf_path = os.path.join(DATA_DIR, "mha_complaint.pdf")
        
        # Build a neat ReportLab PDF for MHA Complaint
        doc = SimpleDocTemplate(
            pdf_path, 
            pagesize=letter,
            rightMargin=54, leftMargin=54, 
            topMargin=54, bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'MHAtitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=15,
            alignment=1 # Center
        )
        
        body_style = ParagraphStyle(
            'MHABody',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=10
        )
        
        story = [
            Paragraph("MINISTRY OF HOME AFFAIRS (MHA) - REPORT DRAFT", title_style),
            Paragraph("NATIONAL CYBER CRIME REPORTING PORTAL EVIDENCE ATTACHMENT", ParagraphStyle('sub', parent=styles['Normal'], alignment=1, spaceAfter=20)),
            Spacer(1, 10)
        ]
        
        # Print block lines
        lines = complaint_text.split('\n')
        for line in lines:
            if line.strip():
                # Escape HTML special chars
                clean_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(clean_line, body_style))
            else:
                story.append(Spacer(1, 8))
                
        doc.build(story)
        return send_file(pdf_path, as_attachment=True, download_name="MHA_Cybercrime_Complaint.pdf")
        
    except Exception as e:
        print(f"Error compiling complaint PDF: {e}")
        return f"Error compiling complaint PDF: {e}", 500


@app.route('/get_dashboard_stats', methods=['GET'])
def get_dashboard_stats():
    """API endpoint to refresh dashboard stats dynamically."""
    return jsonify(get_stats())


@app.route('/simulate-scam-call', methods=['POST'])
def simulate_scam_call():
    """Simulates an incoming scam/spoof call with fake metadata. 100% local, no Twilio billing."""
    try:
        data = request.json or {}
        scam_type = data.get('scam_type', 'digital_arrest')
        
        # 1. Generate fake call metadata
        metadata = simulate_incoming_call(scam_type)
        
        # 2. Analyze metadata for spoof indicators
        spoof_result = analyze_spoof_indicators(metadata)
        
        # 3. Classify the scam transcript using NLP model
        classification = classify_text(metadata['transcript'])
        
        # 4. Print rich metadata report to terminal
        print_terminal_metadata(metadata, spoof_result, classification)
        
        # 5. Generate response actions
        whatsapp_alert = generate_whatsapp_alert(metadata, spoof_result, classification)
        
        # 5b. Send REAL WhatsApp message to victim's phone
        whatsapp_alert = send_real_whatsapp_alert(whatsapp_alert)
        
        telecom_flag = generate_telecom_flag(metadata, spoof_result, classification)
        mha_report = generate_mha_report(metadata, spoof_result, classification)
        audit_entry = append_audit_log(mha_report, metadata, spoof_result, classification)
        
        # 6. Print response actions to terminal
        print_response_actions(whatsapp_alert, telecom_flag, mha_report, audit_entry)
        
        # 7. Log to database
        if classification['label'] == 'SCAM' or spoof_result['total_risk_score'] >= 40:
            amt_protected = 150000.0
            import re as _re
            amt_match = _re.search(r'(\d[\d,]*)\s*(?:lakh|rupees|inr|rs)', metadata['transcript'].lower())
            if amt_match:
                try:
                    amt_protected = float(amt_match.group(1).replace(',', ''))
                    if 'lakh' in metadata['transcript'].lower():
                        amt_protected *= 100000
                except ValueError:
                    pass
            
            add_complaint_log(
                "Simulated Scam Call",
                "SCAM",
                f"[SIM] {metadata['scam_label']} from {metadata['from_number']} ({metadata['caller_country_name']}). Spoof score: {spoof_result['total_risk_score']}%",
                classification['risk_score'],
                amt_protected
            )
        
        # 8. Emit SocketIO alert to dashboard
        socketio.emit('new_alert', {
            'message': f"🚨 SCAM CALL INTERCEPTED: {metadata['scam_label']} from {metadata['from_number']} ({metadata['caller_country_name']}). Spoof: {spoof_result['total_risk_score']}% | NLP: {classification['label']} ({classification['risk_score']}%) | WhatsApp alert SENT to {metadata['to_number']} | Telecom flag POSTED | MHA Report #{mha_report['report_id']}",
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })
        
        # 9. Return full analysis + response actions to frontend
        return jsonify({
            'metadata': metadata,
            'spoof_analysis': spoof_result,
            'classification': classification,
            'response_actions': {
                'whatsapp_alert': whatsapp_alert,
                'telecom_flag': telecom_flag,
                'mha_report': mha_report,
                'audit_entry': audit_entry,
            }
        })
        
    except Exception as e:
        print(f"Scam call simulation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# MAIN
if __name__ == '__main__':
    print("Fraud Shield Initializing...")
    
    # 1. Database Init
    init_db()
    
    # 2. Pre-train NLP model on startup if missing (takes 0.5 sec)
    if not os.path.exists(MODEL_PATH):
        print("Scam classification model not found. Training model...")
        train_scam_model()
        
    # 3. Pre-generate transaction sample if missing
    sample_csv = os.path.join(DATA_DIR, "sample_transactions.csv")
    if not os.path.exists(sample_csv):
        print("Generating mock transaction CSV...")
        generate_mock_transactions_csv(sample_csv)
        
    # 4. Pre-build PyVis graph visualization if missing
    html_out_path = os.path.join(STATIC_DIR, "fraud_graph.html")
    if not os.path.exists(html_out_path):
        G, anom_df, cycling_paths = analyze_transactions(sample_csv)
        generate_interactive_graph(G, anom_df, html_out_path)

    # 5. Start background SocketIO ticker
    ticker_thread = threading.Thread(target=background_alert_ticker)
    ticker_thread.daemon = True
    ticker_thread.start()
    
    print("Initialization complete. Starting server...")
    socketio.run(app, debug=True, host='127.0.0.1', port=5000)
