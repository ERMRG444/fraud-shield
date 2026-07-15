# FraudShield – AI-Powered Public Safety Platform

FraudShield is a unified defense platform that intercepts financial fraud across three attack vectors — scam calls, counterfeit currency, and money mule networks — by combining computer vision, natural language processing, and graph analysis into a single real-time system.

**Demo Video:** https://drive.google.com/drive/folders/1dzq1CeopUIEve8uNqn2Zf0nYYRiHbQ15?usp=drive_link

## Overview

Financial fraud today spans multiple channels simultaneously: voice-based scam calls, physical counterfeit currency, and layered money-laundering networks. Most detection tools address only one of these in isolation. FraudShield brings all three into one platform with a live monitoring dashboard, so patterns that span channels can be spotted and acted on faster.

## Features

- **Scam Call Detection** — Transcribes calls in real time using Whisper AI and runs the transcript through NLP classifiers to flag scam patterns, automatically triggering threat alerts and drafting MHA (Ministry of Home Affairs) cybercrime complaints.
- **Counterfeit Currency Detection** — An OpenCV-based image processing pipeline analyzes currency images for signs of counterfeiting.
- **Fraudulent Transaction Mapping** — Uses NetworkX and PyVis to build interactive graphs of transaction networks, helping visually identify money mule chains and suspicious clusters.
- **Real-Time Dashboard** — Flask-SocketIO streams live alerts from all three modules into a synchronized dashboard, so vision, language, and graph-theory outputs update together as events happen.

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Flask-SocketIO |
| Computer Vision | OpenCV |
| Speech-to-Text | Whisper AI |
| NLP | Scikit-Learn based classifiers |
| Graph Analysis | NetworkX, PyVis |
| Real-Time Communication | Socket.IO |

## Architecture

```
                 ┌───────────────────┐
   Scam Calls →  │  Whisper AI + NLP │──┐
                 └───────────────────┘  │
                                         │
Counterfeit Notes → │ OpenCV Pipeline │──┼──▶ Flask-SocketIO ──▶ Real-Time Dashboard
                                         │
Transactions →   │ NetworkX / PyVis  │──┘
                 └───────────────────┘
```

## Installation

```bash
git clone https://github.com/ERMRG444/fraud-shield.git
cd fraud-shield
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

Then open `http://localhost:5000` in your browser to access the live dashboard.

## Project Structure

```
fraud-shield/
├── app.py                 # Flask application entry point
├── modules/
│   ├── scam_call/          # Whisper AI + NLP classification
│   ├── currency_detection/ # OpenCV counterfeit detection pipeline
│   └── transaction_graph/  # NetworkX/PyVis fraud network mapping
├── static/                # Dashboard frontend assets
├── templates/              # Flask HTML templates
└── requirements.txt
```

## Future Improvements

- Expand scam-call classifier training data for regional language support
- Add automated evidence packaging for cybercrime complaint filing
- Introduce anomaly scoring across all three modules combined
