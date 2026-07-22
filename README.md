# FraudShield – AI-Powered Digital Public Safety Platform

FraudShield is an AI-powered digital public safety command center built to combat India's cyber fraud epidemic. It unifies four intelligent modules — Counterfeit Currency Detection, Digital Arrest Call Classification, Fraud Network Graph Analysis, and Scam Call Simulation — into a single real-time dashboard for law enforcement, banks, and telecom operators to detect, investigate, and neutralize fraud at scale.

**Screenshots:** https://drive.google.com/drive/folders/1dzq1CeopUIEve8uNqn2Zf0nYYRiHbQ15?usp=drive_link
**Demo Video:** https://drive.google.com/drive/folders/1OJD6RnQt58myxG5Enn8wqzgOY8tq0tqu

## Overview

India reported over ₹11,333 crore lost to cyber fraud in the first nine months of 2024 alone, with Digital Arrest scams — where fraudsters impersonate CBI/Customs/Police officials and coerce victims into transferring money under threat of arrest — accounting for a significant share. Counterfeit currency, money mule networks, and phishing scams compound the problem further.

Existing solutions are fragmented: banks run basic transaction monitoring, telecom operators maintain DND lists, and law enforcement relies on manual complaint filing. FraudShield ties these threads together into one AI-driven command center combining Computer Vision, NLP, Graph Theory, and real-time alerting.

## Modules

### 1. Currency Authenticator (Counterfeit Detection)
A 10-stage Computer Vision pipeline verifies Indian banknotes (₹100, ₹200, ₹500) from webcam or uploaded images — entirely offline:
- Note localization via contour detection and perspective warp normalization
- Denomination classification via HSV color histogram analysis
- Security thread and microprint sharpness checks
- Serial number OCR (EasyOCR, 6 preprocessing methods, RBI format validation)
- Color-shift ink and bleed-line geometry checks
- Fake/novelty bank name detection (15+ known fake issuer keywords)

### 2. Digital Arrest Call Classifier (NLP Engine)
Classifies call transcripts (text or audio) as SCAM or LEGITIMATE using a TF-IDF + Logistic Regression pipeline trained on 240+ synthetic transcripts, with keyword-based categorization across four scam types: Digital Arrest, KYC Fraud, Investment Scam, and Lottery Scam. Supports direct audio upload with a multi-tier transcription pipeline (Whisper tiny model → PocketSphinx → Google Speech API fallback). Auto-generates an MHA Cybercrime Portal complaint draft for flagged transcripts.

### 3. Fraud Network Graph Analyzer
Builds directed financial flow graphs from transaction CSVs and applies graph-theoretic anomaly detection — degree centrality, rapid cycling detection, temporal burst detection, velocity ratio asymmetry, and Louvain community detection — to identify money mule networks and pooling hubs. Results render as interactive PyVis network graphs and export as ReportLab PDF evidence packages.

### 4. Scam Call Simulator & Response Actions
Simulates an end-to-end interception: generates realistic fake call metadata, runs 6 spoof indicators (foreign origin, VoIP carrier, authority impersonation, etc.), classifies the transcript, and triggers three automated response actions — WhatsApp victim alert (via Twilio), telecom provider fraud flag (TRAI CFCFRMS format), and an MHA incident report with SHA-256 hash-chained audit logging for legal admissibility (IT Act Section 65B(4)).

## Real-Time Dashboard

A single-page dashboard (HTML5 + Tailwind CSS + vanilla JS) with a dark-mode command center aesthetic:
- Live scrolling threat ticker powered by SocketIO
- Executive stats panel (investigations logged, threats intercepted, capital protected)
- Tabbed module navigation (Currency, Scam Call, Graph)
- Glassmorphism panel styling throughout

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Flask, Flask-SocketIO |
| Computer Vision | OpenCV, EasyOCR, Pillow, NumPy |
| NLP / ML | Scikit-learn (TF-IDF + Logistic Regression) |
| Audio Transcription | OpenAI Whisper (tiny), SpeechRecognition |
| Graph Analysis | NetworkX (Louvain community detection), PyVis |
| PDF Generation | ReportLab |
| Messaging | Twilio WhatsApp Business API |
| Data Processing | Pandas, NumPy |
| Storage | SQLite3, JSONL (SHA-256 hash-chained audit log) |
| Frontend | Tailwind CSS, Socket.IO Client |

## Architecture

```
                     ┌─────────────────────────┐
   Currency Images →  │  OpenCV + EasyOCR       │──┐
                     └─────────────────────────┘  │
                                                    │
   Call Transcripts/  │  Whisper + TF-IDF/LogReg  │──┤
   Audio →            └─────────────────────────┘  │
                                                    ├──▶ Flask + Flask-SocketIO ──▶ Real-Time Dashboard
   Transaction CSVs → │  NetworkX + PyVis         │──┤        │
                     └─────────────────────────┘  │        ├──▶ SQLite (complaints/stats)
                                                    │        └──▶ SHA-256 Audit Log (JSONL)
   Simulated Calls →  │  Spoof Detection Engine   │──┘
                     └─────────────────────────┘
                              │
                              ▼
              WhatsApp Alert · Telecom Flag · MHA Report
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard home page |
| POST | `/detect-currency` | Counterfeit note analysis |
| POST | `/classify_scam` | Scam transcript classification |
| POST | `/visualize_graph` | Fraud graph analysis from CSV |
| GET | `/download_report` | Download evidence PDF |
| POST | `/download_scam_pdf` | Download MHA complaint PDF |
| GET | `/get_dashboard_stats` | Refresh dashboard statistics |
| POST | `/simulate-scam-call` | Run full scam call simulation |

## Installation

```bash
git clone https://github.com/ERMRG444/fraud-shield.git
cd fraud-shield
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Optional: configure a `.env` file with Twilio credentials for real WhatsApp alert delivery.

## Usage

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in your browser to access the live dashboard.

## Project Structure

```
fraud-shield/
├── app.py                  # Flask application entry point
├── data/                    # Sample CSVs, audit logs (SHA-256 hash-chained JSONL)
├── lib/                     # Shared utility functions
├── models/                  # Serialized ML models (TF-IDF vectorizer, LogReg classifier)
├── modules/                 # Currency, scam call, and fraud graph detection pipelines
├── static/                  # Dashboard frontend assets (CSS, JS)
├── templates/                # Flask HTML templates
├── validate_modules.py      # Module validation/testing script
├── requirements.txt
└── .gitignore
```

## Legal & Compliance

- All ML models run locally — no user data sent to external APIs (Whisper and EasyOCR run offline)
- Evidence integrity via SHA-256 hash-chained audit logs, compliant with IT Act Section 65B(4)
- Legal sections referenced: IT Act 66D, IPC 420, IPC 170, PMLA Section 3
- Telecom payloads follow TRAI's CFCFRMS format
- All generated reports marked CONFIDENTIAL — Law Enforcement Internal Use Only

## Future Improvements

- Replace heuristic CV pipeline with a CNN/ViT model trained on real banknote datasets
- Upgrade scam classifier from TF-IDF+LogReg to fine-tuned BERT/DistilBERT
- Real-time SIP trunk integration for live call interception (beyond simulation)
- Multi-language transcript support (Hindi, Tamil, Telugu) via multilingual Whisper
- UPI payment gateway integration for real-time transaction blocking
