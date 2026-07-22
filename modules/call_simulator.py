"""
Scam Call Simulator Module — Fraud Shield
==========================================
Generates realistic fake call metadata to simulate incoming scam/spoof calls.
Analyzes metadata for spoof indicators and prints rich terminal reports.
100% local — no Twilio billing, no external API calls.
"""

import sys
import os

# Add twilio package path (installed to short path to avoid Windows MAX_PATH limit)
_twilio_pkg_path = r'C:\twilio_pkg'
if os.path.isdir(_twilio_pkg_path) and _twilio_pkg_path not in sys.path:
    sys.path.insert(0, _twilio_pkg_path)

import random
import string
import uuid
import time
from datetime import datetime, timedelta


# ========================================================================
# SCAM SCENARIO DEFINITIONS
# ========================================================================

SCAM_SCENARIOS = {
    "digital_arrest": {
        "label": "Digital Arrest Scam",
        "caller_profiles": [
            {
                "from_number": "+86-138-{rand4}-{rand4}",
                "caller_name": "CBI Officer Vikram Sharma",
                "carrier": "China Unicom VoIP Gateway",
                "caller_city": "Shenzhen",
                "caller_state": "Guangdong",
                "caller_country": "CN",
                "caller_country_name": "China",
                "is_voip": True,
                "network_type": "VoIP / SIP Trunk",
            },
            {
                "from_number": "+1-929-{rand3}-{rand4}",
                "caller_name": "Customs Dept. Inspector",
                "carrier": "Bandwidth.com VoIP",
                "caller_city": "New York",
                "caller_state": "NY",
                "caller_country": "US",
                "caller_country_name": "United States",
                "is_voip": True,
                "network_type": "VoIP / Cloud PBX",
            },
            {
                "from_number": "+44-7911-{rand3}-{rand3}",
                "caller_name": "NCB Senior Officer",
                "carrier": "Skype Connect VoIP",
                "caller_city": "London",
                "caller_state": "England",
                "caller_country": "GB",
                "caller_country_name": "United Kingdom",
                "is_voip": True,
                "network_type": "VoIP / Microsoft Teams",
            }
        ],
        "transcripts": [
            "This is Officer Vikram Sharma calling from the Central Bureau of Investigation. We have intercepted a parcel in your name at Mumbai International Airport containing 500 grams of MDMA drugs and 3 fake passports. An FIR number 2024-CBI-48291 has been filed against you. You are under digital arrest effective immediately. Do not hang up this call or contact anyone. You must stay on video call for verification. Transfer Rs 2,50,000 to our RBI secure verification account within the next 30 minutes or a physical arrest warrant will be executed at your residence.",
            "Hello, I am calling from the Customs Department, Government of India. Your Aadhaar number has been linked to a suspicious international parcel containing illegal narcotics and counterfeit currency worth Rs 48 Lakhs. The Enforcement Directorate has issued a non-bailable arrest warrant in your name. You are now under digital arrest. Do not disconnect this call. To clear your name, you must transfer Rs 1,50,000 as a refundable security deposit to our investigation account via UPI immediately.",
            "This is the Narcotics Control Bureau cyber division. We have evidence that your bank account was used to launder Rs 15 Crore through hawala channels. The Supreme Court has approved your digital arrest under Section 420 IPC. You cannot leave your room or speak to anyone. Transfer Rs 4,90,000 bail amount to avoid immediate physical arrest. Any non-cooperation will result in a 7-year imprisonment.",
        ],
    },
    "kyc_fraud": {
        "label": "KYC / Banking Fraud",
        "caller_profiles": [
            {
                "from_number": "+44-20-{rand4}-{rand4}",
                "caller_name": "SBI Customer Care Executive",
                "carrier": "BT Group VoIP Gateway",
                "caller_city": "London",
                "caller_state": "England",
                "caller_country": "GB",
                "caller_country_name": "United Kingdom",
                "is_voip": True,
                "network_type": "VoIP / SIP Gateway",
            },
            {
                "from_number": "+971-50-{rand3}-{rand4}",
                "caller_name": "HDFC Bank KYC Dept",
                "carrier": "Etisalat VoIP",
                "caller_city": "Dubai",
                "caller_state": "Dubai",
                "caller_country": "AE",
                "caller_country_name": "United Arab Emirates",
                "is_voip": True,
                "network_type": "VoIP / Virtual Number",
            }
        ],
        "transcripts": [
            "Dear valued customer, this is an urgent call from the State Bank of India KYC verification department. Your savings account number ending in 4829 has been temporarily suspended due to incomplete KYC documentation. If you do not update your PAN card and Aadhaar details within the next 15 minutes, your account will be permanently blocked and a penalty of Rs 25,000 will be charged. Please share the 6-digit OTP sent to your registered mobile number to verify your identity and reactivate your account immediately.",
            "Hello, I am speaking from the HDFC Bank security operations center. We have detected unauthorized transactions of Rs 85,000 from your credit card ending in 7721. To block your card and reverse these transactions, please confirm your card CVV number, expiry date, and the OTP we just sent. If you do not verify within 10 minutes, the fraudulent transactions will be processed and your liability will be Rs 85,000.",
        ],
    },
    "investment_scam": {
        "label": "Investment / Trading Scam",
        "caller_profiles": [
            {
                "from_number": "+1-415-{rand3}-{rand4}",
                "caller_name": "Goldman Wealth VIP Advisor",
                "carrier": "Google Voice VoIP",
                "caller_city": "San Francisco",
                "caller_state": "CA",
                "caller_country": "US",
                "caller_country_name": "United States",
                "is_voip": True,
                "network_type": "VoIP / Google Voice",
            },
            {
                "from_number": "+852-{rand4}-{rand4}",
                "caller_name": "Bull Market Trading Expert",
                "carrier": "HKT VoIP Services",
                "caller_city": "Hong Kong",
                "caller_state": "Hong Kong",
                "caller_country": "HK",
                "caller_country_name": "Hong Kong",
                "is_voip": True,
                "network_type": "VoIP / WhatsApp Business",
            }
        ],
        "transcripts": [
            "Welcome to the exclusive VIP Stock Trading Channel by Goldman Wealth Partners. I am your personal investment advisor. We use advanced AI-powered algorithms that guarantee 500% returns within one week on the Indian stock market. Our top clients earned Rs 8,00,000 last month alone. To join our premium WhatsApp group and start receiving daily stock signals, simply invest Rs 50,000 as an initial deposit via UPI to our registered trading account. This is a limited time offer available only to 10 selected investors today.",
            "Hi there! You have been specially selected for our crypto trading masterclass. Our AI trading bot has generated Rs 45 Lakh profit for our members this quarter. We guarantee daily returns of 10% on your investment with absolutely zero risk. Deposit a minimum of Rs 10,000 via UPI to get started today. Your money is 100% safe and you can withdraw anytime. Join our exclusive Telegram group now before all slots fill up.",
        ],
    },
    "lottery_scam": {
        "label": "Lottery / Prize Scam",
        "caller_profiles": [
            {
                "from_number": "+234-803-{rand3}-{rand4}",
                "caller_name": "KBC Lucky Draw Claims Dept",
                "carrier": "MTN Nigeria VoIP",
                "caller_city": "Lagos",
                "caller_state": "Lagos",
                "caller_country": "NG",
                "caller_country_name": "Nigeria",
                "is_voip": True,
                "network_type": "VoIP / Asterisk PBX",
            },
            {
                "from_number": "+233-24-{rand3}-{rand4}",
                "caller_name": "Jio Anniversary Prize Office",
                "carrier": "Vodafone Ghana VoIP",
                "caller_city": "Accra",
                "caller_state": "Greater Accra",
                "caller_country": "GH",
                "caller_country_name": "Ghana",
                "is_voip": True,
                "network_type": "VoIP / FreeSWITCH",
            }
        ],
        "transcripts": [
            "Congratulations! Bahut bahut badhaai ho! Your mobile number has won the Kaun Banega Crorepati Season 15 Mega Lucky Draw of Rs 25 Lakh! You are our grand winner! To claim this cash prize directly in your bank account, you must pay a government processing tax of Rs 12,500 and a one-time registration fee of Rs 5,000 via UPI to our authorized lottery agent within the next 1 hour. This prize is fully sponsored by Jio and SBI. Please do not share this information with anyone else.",
            "Dear winner, this is a call from the Tata Motors Anniversary Celebration Department. Your phone number was randomly selected from 50 million entries and you have won a brand new Tata Nexon SUV worth Rs 15 Lakhs plus Rs 5 Lakhs cash! To process the dispatch of your vehicle and cash prize, transfer Rs 45,000 registration and insurance fee to our authorized account. This amount is 100% refundable and will be added to your prize money.",
        ],
    }
}

# Target phone numbers (Indian format — simulated receiver)
TARGET_PROFILES = [
    {"number": "+91-98765-43210", "name": "Victim - Rahul Mehta", "city": "Mumbai", "state": "Maharashtra"},
    {"number": "+91-87654-32109", "name": "Victim - Priya Sharma", "city": "Delhi", "state": "Delhi"},
    {"number": "+91-99887-76655", "name": "Victim - Amit Patel", "city": "Ahmedabad", "state": "Gujarat"},
]

# Known scam country codes for detection
HIGH_RISK_COUNTRIES = {
    "NG": "Nigeria — High fraud origin",
    "GH": "Ghana — Known scam hub",
    "CN": "China — VoIP spoofing origin",
    "PH": "Philippines — Call center scam hub",
    "AE": "UAE — Spoofed banking calls origin",
}

MODERATE_RISK_COUNTRIES = {
    "US": "United States — VoIP masking common",
    "GB": "United Kingdom — Impersonation calls",
    "HK": "Hong Kong — Financial fraud origin",
}


# ========================================================================
# METADATA GENERATOR
# ========================================================================

def _rand_digits(n):
    return ''.join(random.choices(string.digits, k=n))


def simulate_incoming_call(scam_type="digital_arrest"):
    """
    Generates a complete fake call metadata dict simulating an incoming scam call.
    Returns metadata dict with all fields that a real telephony system would capture.
    """
    scenario = SCAM_SCENARIOS.get(scam_type, SCAM_SCENARIOS["digital_arrest"])
    profile = random.choice(scenario["caller_profiles"])
    target = random.choice(TARGET_PROFILES)
    transcript = random.choice(scenario["transcripts"])

    # Generate realistic phone number from template
    from_number = profile["from_number"]
    from_number = from_number.replace("{rand4}", _rand_digits(4))
    from_number = from_number.replace("{rand3}", _rand_digits(3))

    # Simulate call timing
    call_start = datetime.now()
    ring_duration = random.uniform(2.0, 6.0)
    call_duration = random.uniform(45.0, 180.0)

    # Build metadata
    metadata = {
        # Call identification
        "call_sid": f"CA{uuid.uuid4().hex[:32]}",
        "account_sid": f"AC{uuid.uuid4().hex[:32]}",
        "api_version": "2010-04-01",

        # Caller info
        "from_number": from_number,
        "caller_name": profile["caller_name"],
        "caller_city": profile["caller_city"],
        "caller_state": profile["caller_state"],
        "caller_country": profile["caller_country"],
        "caller_country_name": profile["caller_country_name"],
        "caller_carrier": profile["carrier"],
        "caller_network_type": profile["network_type"],
        "is_voip": profile["is_voip"],

        # Receiver info
        "to_number": target["number"],
        "to_name": target["name"],
        "to_city": target["city"],
        "to_state": target["state"],
        "to_country": "IN",
        "to_country_name": "India",

        # Call details
        "call_direction": "inbound",
        "call_status": "completed",
        "call_start_time": call_start.strftime("%Y-%m-%d %H:%M:%S"),
        "ring_duration_sec": round(ring_duration, 1),
        "call_duration_sec": round(call_duration, 1),
        "call_end_time": (call_start + timedelta(seconds=call_duration)).strftime("%Y-%m-%d %H:%M:%S"),

        # Scam scenario info
        "scam_type": scam_type,
        "scam_label": scenario["label"],
        "transcript": transcript,

        # Technical fingerprinting
        "sip_domain": f"sip.{profile['carrier'].split()[0].lower()}.voip.net",
        "user_agent": random.choice([
            "Opal/2.4.0 (Linux)",
            "Opal/3.18.8 (FreeSWITCH)",
            "Opal/2.18.7 (Opal VoIP)",
            "OPAL/4.5.6 (Opal VoIP)",
            "Opal/3.10.11 (Opal VoIP)",
        ]),
        "codec": random.choice(["G.711 μ-law", "G.729", "Opus"]),
        "encryption": random.choice(["None", "SRTP (weak)", "None"]),
    }

    return metadata


# ========================================================================
# SPOOF DETECTION ENGINE
# ========================================================================

def analyze_spoof_indicators(metadata):
    """
    Analyzes call metadata for spoof/scam indicators.
    Returns a detailed risk assessment with individual indicator scores.
    """
    indicators = []
    total_risk = 0

    country = metadata.get("caller_country", "")
    caller_name = metadata.get("caller_name", "").lower()
    is_voip = metadata.get("is_voip", False)
    network_type = metadata.get("caller_network_type", "")
    encryption = metadata.get("encryption", "")

    # 1. Foreign origin check (caller is outside India calling Indian number)
    if country != "IN":
        if country in HIGH_RISK_COUNTRIES:
            risk = 30
            indicators.append({
                "indicator": "HIGH-RISK FOREIGN ORIGIN",
                "detail": f"Caller from {metadata['caller_country_name']} ({country}) — {HIGH_RISK_COUNTRIES[country]}",
                "risk_delta": risk,
                "severity": "CRITICAL"
            })
        elif country in MODERATE_RISK_COUNTRIES:
            risk = 20
            indicators.append({
                "indicator": "FOREIGN ORIGIN",
                "detail": f"Caller from {metadata['caller_country_name']} ({country}) — {MODERATE_RISK_COUNTRIES[country]}",
                "risk_delta": risk,
                "severity": "HIGH"
            })
        else:
            risk = 15
            indicators.append({
                "indicator": "FOREIGN ORIGIN",
                "detail": f"International call from {metadata['caller_country_name']} ({country})",
                "risk_delta": risk,
                "severity": "MEDIUM"
            })
        total_risk += risk

    # 2. VoIP carrier detection
    if is_voip:
        risk = 25
        indicators.append({
            "indicator": "VoIP CARRIER DETECTED",
            "detail": f"Carrier: {metadata['caller_carrier']} | Network: {network_type}",
            "risk_delta": risk,
            "severity": "HIGH"
        })
        total_risk += risk

    # 3. Authority impersonation in caller name
    authority_keywords = ["cbi", "customs", "officer", "inspector", "police", "ncb", "bank", "sbi", "hdfc",
                          "icici", "rbi", "dept", "department", "government", "ministry"]
    matched_authorities = [kw for kw in authority_keywords if kw in caller_name]
    if matched_authorities:
        risk = 20
        indicators.append({
            "indicator": "AUTHORITY IMPERSONATION",
            "detail": f"Caller name '{metadata['caller_name']}' impersonates authority ({', '.join(matched_authorities)})",
            "risk_delta": risk,
            "severity": "CRITICAL"
        })
        total_risk += risk

    # 4. Caller name vs location mismatch (Indian name but foreign location)
    indian_name_indicators = ["sharma", "patel", "singh", "kumar", "gupta", "mehta", "verma", "joshi", "reddy"]
    has_indian_name = any(name in caller_name for name in indian_name_indicators)
    if has_indian_name and country != "IN":
        risk = 15
        indicators.append({
            "indicator": "NAME-LOCATION MISMATCH",
            "detail": f"Indian name '{metadata['caller_name']}' calling from {metadata['caller_country_name']}",
            "risk_delta": risk,
            "severity": "HIGH"
        })
        total_risk += risk

    # 5. No encryption / weak encryption
    if encryption in ["None", "SRTP (weak)"]:
        risk = 10
        indicators.append({
            "indicator": "WEAK/NO ENCRYPTION",
            "detail": f"Call encryption: {encryption} — suggests unregulated VoIP trunk",
            "risk_delta": risk,
            "severity": "MEDIUM"
        })
        total_risk += risk

    # 6. SIP domain analysis
    sip_domain = metadata.get("sip_domain", "")
    if "voip" in sip_domain.lower() or "sip" in sip_domain.lower():
        risk = 5
        indicators.append({
            "indicator": "SUSPICIOUS SIP DOMAIN",
            "detail": f"SIP Origin: {sip_domain}",
            "risk_delta": risk,
            "severity": "LOW"
        })
        total_risk += risk

    # Cap at 100
    total_risk = min(total_risk, 100)

    # Verdict
    if total_risk >= 70:
        verdict = "SPOOF / SCAM CALL"
        verdict_color = "RED"
    elif total_risk >= 40:
        verdict = "SUSPICIOUS CALL"
        verdict_color = "YELLOW"
    else:
        verdict = "LOW RISK"
        verdict_color = "GREEN"

    return {
        "total_risk_score": total_risk,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "indicators": indicators,
        "indicators_count": len(indicators),
    }


# ========================================================================
# TERMINAL METADATA REPORT PRINTER
# ========================================================================

# ANSI color codes for terminal
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def print_terminal_metadata(metadata, spoof_result, classification_result=None):
    """
    Prints a rich, color-coded metadata report to the terminal.
    Designed for hackathon demo visibility.
    """
    w = 80  # terminal width

    # Header
    print()
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}{'FRAUD SHIELD — INCOMING CALL METADATA ANALYSIS':^{w}}{C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print()

    # Call Identification
    print(f"  {C.CYAN}{C.BOLD}╔══ CALL IDENTIFICATION ══════════════════════════════════════════╗{C.RESET}")
    print(f"  {C.CYAN}║{C.RESET}  Call SID      : {C.DIM}{metadata['call_sid']}{C.RESET}")
    print(f"  {C.CYAN}║{C.RESET}  Direction     : {C.YELLOW}{metadata['call_direction'].upper()}{C.RESET}")
    print(f"  {C.CYAN}║{C.RESET}  Status        : {C.GREEN}{metadata['call_status'].upper()}{C.RESET}")
    print(f"  {C.CYAN}║{C.RESET}  Start Time    : {metadata['call_start_time']}")
    print(f"  {C.CYAN}║{C.RESET}  Duration      : {metadata['call_duration_sec']}s")
    print(f"  {C.CYAN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # Caller Metadata
    print(f"  {C.RED}{C.BOLD}╔══ CALLER METADATA (SUSPECT) ═══════════════════════════════════╗{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  From Number   : {C.RED}{C.BOLD}{metadata['from_number']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  Caller Name   : {C.RED}{C.BOLD}{metadata['caller_name']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  Carrier       : {C.YELLOW}{metadata['caller_carrier']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  Network Type  : {C.YELLOW}{metadata['caller_network_type']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  Is VoIP       : {C.RED if metadata['is_voip'] else C.GREEN}{C.BOLD}{'YES ⚠' if metadata['is_voip'] else 'NO'}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  City          : {metadata['caller_city']}")
    print(f"  {C.RED}║{C.RESET}  State         : {metadata['caller_state']}")
    print(f"  {C.RED}║{C.RESET}  Country       : {C.RED}{C.BOLD}{metadata['caller_country_name']} ({metadata['caller_country']}){C.RESET}")
    print(f"  {C.RED}║{C.RESET}  SIP Domain    : {C.DIM}{metadata['sip_domain']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  User Agent    : {C.DIM}{metadata['user_agent']}{C.RESET}")
    print(f"  {C.RED}║{C.RESET}  Codec         : {metadata['codec']}")
    print(f"  {C.RED}║{C.RESET}  Encryption    : {C.RED if metadata['encryption'] == 'None' else C.YELLOW}{metadata['encryption']}{C.RESET}")
    print(f"  {C.RED}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # Receiver Metadata
    print(f"  {C.GREEN}{C.BOLD}╔══ RECEIVER METADATA (TARGET) ══════════════════════════════════╗{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  To Number     : {C.GREEN}{metadata['to_number']}{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  Name          : {metadata['to_name']}")
    print(f"  {C.GREEN}║{C.RESET}  Location      : {metadata['to_city']}, {metadata['to_state']}")
    print(f"  {C.GREEN}║{C.RESET}  Country       : {metadata['to_country_name']} ({metadata['to_country']})")
    print(f"  {C.GREEN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # Spoof Detection Analysis
    verdict_color = C.RED if spoof_result['verdict_color'] == 'RED' else (C.YELLOW if spoof_result['verdict_color'] == 'YELLOW' else C.GREEN)
    print(f"  {C.MAGENTA}{C.BOLD}╔══ SPOOF DETECTION ANALYSIS ════════════════════════════════════╗{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  {C.BOLD}SPOOF RISK SCORE: {verdict_color}{C.BOLD}{spoof_result['total_risk_score']}% — {spoof_result['verdict']}{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}")

    for ind in spoof_result['indicators']:
        sev = ind['severity']
        sev_color = C.RED if sev == 'CRITICAL' else (C.YELLOW if sev == 'HIGH' else (C.BLUE if sev == 'MEDIUM' else C.DIM))
        icon = "🔴" if sev == 'CRITICAL' else ("🟡" if sev == 'HIGH' else ("🔵" if sev == 'MEDIUM' else "⚪"))
        print(f"  {C.MAGENTA}║{C.RESET}  {icon} [{sev_color}{C.BOLD}{sev:8s}{C.RESET}] {C.BOLD}{ind['indicator']}{C.RESET} (+{ind['risk_delta']}%)")
        print(f"  {C.MAGENTA}║{C.RESET}     {C.DIM}{ind['detail']}{C.RESET}")

    print(f"  {C.MAGENTA}║{C.RESET}")
    print(f"  {C.MAGENTA}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # NLP Classification Result
    if classification_result:
        label_color = C.RED if classification_result['label'] == 'SCAM' else C.GREEN
        print(f"  {C.YELLOW}{C.BOLD}╔══ NLP SCAM CLASSIFICATION ═════════════════════════════════════╗{C.RESET}")
        print(f"  {C.YELLOW}║{C.RESET}  Verdict       : {label_color}{C.BOLD}{classification_result['label']}{C.RESET}")
        print(f"  {C.YELLOW}║{C.RESET}  Risk Score    : {label_color}{C.BOLD}{classification_result['risk_score']}%{C.RESET}")
        print(f"  {C.YELLOW}║{C.RESET}  Category      : {C.BOLD}{classification_result.get('category', 'N/A')}{C.RESET}")
        if classification_result.get('highlighted_phrases'):
            phrases = ", ".join(classification_result['highlighted_phrases'][:10])
            print(f"  {C.YELLOW}║{C.RESET}  Key Phrases   : {C.RED}{phrases}{C.RESET}")
        print(f"  {C.YELLOW}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
        print()

    # Transcript excerpt
    transcript = metadata.get('transcript', '')
    if transcript:
        excerpt = transcript[:200] + "..." if len(transcript) > 200 else transcript
        print(f"  {C.DIM}╔══ CALL TRANSCRIPT (EXCERPT) ═══════════════════════════════════╗{C.RESET}")
        # Word-wrap the excerpt
        words = excerpt.split()
        line = "  " + C.DIM + "║" + C.RESET + "  "
        for word in words:
            if len(line) + len(word) > w + 15:  # account for ANSI codes
                print(line)
                line = "  " + C.DIM + "║" + C.RESET + "  "
            line += word + " "
        if line.strip():
            print(line)
        print(f"  {C.DIM}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
        print()

    # Footer
    alert_status = "🚨 ALERT SENT TO DASHBOARD" if spoof_result['total_risk_score'] >= 40 else "ℹ️  LOW RISK — NO ALERT"
    print(f"  {C.BOLD}{verdict_color}{alert_status}{C.RESET}")
    print(f"  {C.DIM}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Fraud Shield v1.0{C.RESET}")
    print(f"{C.BG_BLUE}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print()


# ========================================================================
# RESPONSE ACTION 1: WHATSAPP ALERT TO VICTIM
# ========================================================================

def generate_whatsapp_alert(metadata, spoof_result, classification):
    """
    Generates a simulated WhatsApp warning message that would be sent
    to the victim's phone via Twilio WhatsApp API BEFORE they pick up
    the scam call.
    """
    victim_number = metadata['to_number']
    victim_name = metadata['to_name'].replace("Victim - ", "")
    caller_number = metadata['from_number']
    risk_score = spoof_result['total_risk_score']
    scam_type = metadata['scam_label']
    country = metadata['caller_country_name']

    # 1. Summary WhatsApp alert (matching the screenshot exactly)
    message_body_summary = (
        f"🚨 *FRAUD SHIELD – SCAM ALERT* 🚨\n\n"
        f"Dear *{victim_name}*, an incoming call from *{caller_number}* ({country}) is flagged as "
        f"*{scam_type} – {risk_score}% risk*.\n\n"
        f"🛑 *DO NOT answer, share OTP/Aadhaar, or transfer money.*\n"
        f"No govt agency demands money over phone.\n\n"
        f"📞 *Report: 1930 | cybercrime.gov.in*\n"
        f"🔒 *Fraud Shield AI | {datetime.now().strftime('%H:%M:%S IST')}*"
    )

    # 2. Detailed safety checklist and backup steps
    message_body_detailed = (
        f"🚨 *FRAUD SHIELD — SCAM CALL ALERT* 🚨\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Dear *{victim_name}*,\n\n"
        f"⚠️ An incoming call from *{caller_number}* "
        f"(Origin: *{country}*) has been flagged as a "
        f"*{scam_type}* with *{risk_score}% risk score*.\n\n"
        f"🛑 *DO NOT:*\n"
        f"  • Answer or return this call\n"
        f"  • Share any OTP, Aadhaar, or PAN details\n"
        f"  • Transfer money to any account\n"
        f"  • Stay on video call with strangers\n\n"
        f"✅ *REMEMBER:*\n"
        f"  • No govt agency calls to \"digitally arrest\" you\n"
        f"  • CBI/Police never demand money over phone\n"
        f"  • Banks never ask for OTP or CVV on call\n\n"
        f"📞 *Report this number immediately:*\n"
        f"  • National Cybercrime Helpline: *1930*\n"
        f"  • Online: cybercrime.gov.in\n"
        f"  • Local Police: 100\n\n"
        f"🔒 This alert was auto-generated by Fraud Shield AI\n"
        f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}\n"
        f"   Ref: {metadata['call_sid'][:16]}"
    )

    # Simulated Twilio WhatsApp API response
    whatsapp_response = {
        "api": "Twilio WhatsApp Business API",
        "endpoint": "https://api.twilio.com/2010-04-01/Accounts/ACXXXX/Messages.json",
        "method": "POST",
        "status": "DELIVERED",
        "status_code": 201,
        "from_number": "whatsapp:+14155238886",  # Twilio sandbox
        "to_number": f"whatsapp:{victim_number}",
        "message_sid": f"SM{uuid.uuid4().hex[:32]}",
        "message_body": message_body_summary,
        "message_body_detail": message_body_detailed,
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "delivery_status": "delivered",
        "price": "-0.0084",
        "price_unit": "USD",
    }

    return whatsapp_response


def send_real_whatsapp_alert(whatsapp_data):
    """
    Sends REAL WhatsApp messages via Twilio API using credentials from .env.
    Sends both the summary alert and the detailed warning message.
    Returns updated whatsapp_data dict with real delivery status.
    Falls back gracefully if credentials are missing.
    
    NOTE: Twilio's HTTP client uses 'requests' which conflicts with eventlet's
    monkey-patched green threads. We run the actual API calls in a native OS
    thread via concurrent.futures to avoid greenlet errors.
    """
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        to_number = os.environ.get('TWILIO_WHATSAPP_TO', '')
        from_number = os.environ.get('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

        if not account_sid or not auth_token or not to_number:
            print(f"  {C.YELLOW}[WHATSAPP] Twilio credentials not found in .env — skipping real send{C.RESET}")
            whatsapp_data['real_delivery'] = False
            whatsapp_data['real_delivery_note'] = "Credentials not configured in .env"
            return whatsapp_data

        to_formatted = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number

        def _send_via_twilio():
            """Runs in a native OS thread to avoid eventlet/greenlet conflicts."""
            from twilio.rest import Client
            client = Client(account_sid, auth_token)

            # 1. Send the summary WhatsApp message
            msg_summary = client.messages.create(
                from_=from_number,
                to=to_formatted,
                body=whatsapp_data['message_body']
            )
            print(f"  {C.GREEN}[WHATSAPP] summary alert sent: {msg_summary.sid}{C.RESET}")

            # 2. Send the detailed WhatsApp message
            detail_body = whatsapp_data.get('message_body_detail', '')
            if detail_body:
                msg_detail = client.messages.create(
                    from_=from_number,
                    to=to_formatted,
                    body=detail_body
                )
                print(f"  {C.GREEN}[WHATSAPP] detailed alert sent: {msg_detail.sid}{C.RESET}")

            return msg_summary

        # Run Twilio calls in a native thread to bypass eventlet green threading
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_send_via_twilio)
            message_summary = future.result(timeout=30)  # 30s timeout

        # Update response with real data from summary message
        whatsapp_data['real_delivery'] = True
        whatsapp_data['message_sid'] = message_summary.sid
        whatsapp_data['status'] = message_summary.status.upper() if message_summary.status else "QUEUED"
        whatsapp_data['delivery_status'] = message_summary.status or "queued"
        whatsapp_data['to_number'] = to_formatted
        whatsapp_data['from_number'] = from_number

        print(f"  {C.GREEN}{C.BOLD}[WHATSAPP] ✓ BOTH messages sent successfully!{C.RESET}")

        return whatsapp_data

    except Exception as e:
        print(f"  {C.RED}[WHATSAPP] Failed to send real message: {e}{C.RESET}")
        whatsapp_data['real_delivery'] = False
        whatsapp_data['real_delivery_error'] = str(e)
        return whatsapp_data

# ========================================================================
# RESPONSE ACTION 2: TELECOM PROVIDER FLAGGING
# ========================================================================

def generate_telecom_flag(metadata, spoof_result, classification):
    """
    Generates a structured payload to be posted to the telecom provider's
    fraud management API. For hackathon demo, this appears as a live log.
    """
    risk_score = spoof_result['total_risk_score']

    # Determine recommended action based on risk
    if risk_score >= 80:
        action = "IMMEDIATE_BLOCK"
        priority = "P1 — CRITICAL"
        action_desc = "Block number immediately across all networks. Add to national DND blacklist."
    elif risk_score >= 60:
        action = "FLAG_AND_MONITOR"
        priority = "P2 — HIGH"
        action_desc = "Flag number for monitoring. Rate-limit outgoing calls. Alert fraud team."
    else:
        action = "MONITOR"
        priority = "P3 — MEDIUM"
        action_desc = "Add to watchlist. Monitor call patterns for 72 hours."

    # Build telecom API payload
    telecom_payload = {
        "api": "Telecom Fraud Management API (TRAI-CFCFRMS)",
        "endpoint": "https://api.telecom-fraud.gov.in/v2/flag-number",
        "method": "POST",
        "request_id": f"TRAI-{uuid.uuid4().hex[:12].upper()}",
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "status": "ACCEPTED",
        "status_code": 202,
        "payload": {
            "flagged_number": metadata['from_number'],
            "caller_name_claimed": metadata['caller_name'],
            "origin_country": metadata['caller_country'],
            "origin_country_name": metadata['caller_country_name'],
            "origin_city": metadata['caller_city'],
            "carrier": metadata['caller_carrier'],
            "network_type": metadata['caller_network_type'],
            "is_voip": metadata['is_voip'],
            "sip_domain": metadata['sip_domain'],
            "risk_score": risk_score,
            "risk_verdict": spoof_result['verdict'],
            "scam_category": metadata['scam_label'],
            "nlp_classification": classification['label'],
            "nlp_risk_score": classification['risk_score'],
            "evidence_indicators": [ind['indicator'] for ind in spoof_result['indicators']],
            "recommended_action": action,
            "action_description": action_desc,
            "priority": priority,
            "target_victim_number": metadata['to_number'],
            "target_victim_location": f"{metadata['to_city']}, {metadata['to_state']}",
            "call_sid": metadata['call_sid'],
            "reporting_system": "Fraud Shield AI v1.0",
            "legal_basis": "TRAI Regulations on Unsolicited Communications 2018, IT Act Section 66D",
        },
        "response": {
            "acknowledgment": f"ACK-{uuid.uuid4().hex[:8].upper()}",
            "action_taken": action,
            "block_effective_from": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "block_scope": "PAN-India (All Telecom Operators)" if risk_score >= 80 else "Originating Circle",
            "notification_sent_to": ["TRAI NOC", "DoT Cyber Cell", "Originating TSP"],
        }
    }

    return telecom_payload


# ========================================================================
# RESPONSE ACTION 3: MHA INCIDENT REPORT + SHA-256 AUDIT LOG
# ========================================================================

import hashlib
import json
import os

# Audit log file path
AUDIT_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "audit_log.jsonl")


def _compute_sha256(data_str):
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()


def _get_previous_hash():
    """Read the last hash from the audit log for chain linking."""
    try:
        if os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1].strip())
                    return last_entry.get('evidence_hash', '0' * 64)
    except Exception:
        pass
    return '0' * 64  # Genesis hash


def generate_mha_report(metadata, spoof_result, classification):
    """
    Auto-generates a structured MHA (Ministry of Home Affairs) incident report
    with legal sections, SHA-256 hash-chained evidence for legal admissibility.
    """
    report_id = f"MHA-IR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    # Determine applicable legal sections based on scam type
    scam_type = metadata.get('scam_type', 'digital_arrest')
    legal_sections = [
        {
            "section": "IT Act Section 66D",
            "title": "Punishment for cheating by personation using computer resource",
            "applicability": "Caller impersonated government authority using VoIP technology",
            "penalty": "Imprisonment up to 3 years + fine up to ₹1,00,000"
        },
        {
            "section": "IPC Section 420",
            "title": "Cheating and dishonestly inducing delivery of property",
            "applicability": "Attempted to induce victim to transfer money under false pretenses",
            "penalty": "Imprisonment up to 7 years + fine"
        },
        {
            "section": "IPC Section 170",
            "title": "Personating a public servant",
            "applicability": f"Caller identified as '{metadata['caller_name']}' impersonating law enforcement",
            "penalty": "Imprisonment up to 2 years + fine + both"
        }
    ]

    # Add additional sections based on scam type
    if scam_type == "kyc_fraud":
        legal_sections.append({
            "section": "IT Act Section 43",
            "title": "Penalty for unauthorized access to computer system",
            "applicability": "Attempted to obtain banking credentials (OTP, CVV) through social engineering",
            "penalty": "Compensation up to ₹5,00,00,000"
        })
    elif scam_type == "investment_scam":
        legal_sections.append({
            "section": "SEBI Act Section 12A",
            "title": "Prohibition of manipulative and deceptive devices",
            "applicability": "False promises of guaranteed stock market returns to defraud investors",
            "penalty": "Imprisonment up to 10 years + fine up to ₹25,00,00,000"
        })

    # Build evidence package
    evidence_items = {
        "call_metadata": {
            "call_sid": metadata['call_sid'],
            "from_number": metadata['from_number'],
            "to_number": metadata['to_number'],
            "caller_name": metadata['caller_name'],
            "origin": f"{metadata['caller_city']}, {metadata['caller_state']}, {metadata['caller_country_name']}",
            "carrier": metadata['caller_carrier'],
            "network_type": metadata['caller_network_type'],
            "is_voip": metadata['is_voip'],
            "call_duration": metadata['call_duration_sec'],
            "call_start": metadata['call_start_time'],
        },
        "spoof_analysis": {
            "risk_score": spoof_result['total_risk_score'],
            "verdict": spoof_result['verdict'],
            "indicators": spoof_result['indicators'],
        },
        "nlp_classification": {
            "label": classification['label'],
            "risk_score": classification['risk_score'],
            "category": classification.get('category', 'N/A'),
        },
        "transcript_excerpt": metadata['transcript'][:500],
    }

    # SHA-256 hash chain
    previous_hash = _get_previous_hash()
    evidence_json = json.dumps(evidence_items, sort_keys=True, default=str)
    evidence_hash = _compute_sha256(evidence_json)
    chain_input = f"{previous_hash}:{evidence_hash}:{report_id}:{timestamp}"
    chain_hash = _compute_sha256(chain_input)

    # Build the MHA report
    mha_report = {
        "report_id": report_id,
        "report_type": "CYBER CRIME INCIDENT REPORT",
        "reporting_authority": "Fraud Shield AI — Automated Threat Intelligence Platform",
        "submitted_to": "Ministry of Home Affairs — Indian Cyber Crime Coordination Centre (I4C)",
        "portal": "National Cyber Crime Reporting Portal (cybercrime.gov.in)",
        "timestamp": timestamp,

        "incident_details": {
            "incident_type": metadata['scam_label'],
            "incident_subtype": f"Telephonic Impersonation — {metadata['caller_name']}",
            "severity": "HIGH" if spoof_result['total_risk_score'] >= 70 else "MEDIUM",
            "financial_loss": "₹0.00 (Prevented by Fraud Shield AI)",
            "financial_loss_prevented": True,
            "status": "INTERCEPTED — No victim harm occurred",
        },

        "legal_sections": legal_sections,

        "suspect_details": {
            "phone_number": metadata['from_number'],
            "claimed_identity": metadata['caller_name'],
            "actual_origin": f"{metadata['caller_city']}, {metadata['caller_state']}, {metadata['caller_country_name']} ({metadata['caller_country']})",
            "carrier": metadata['caller_carrier'],
            "network_type": metadata['caller_network_type'],
            "voip_detected": metadata['is_voip'],
            "sip_domain": metadata['sip_domain'],
            "spoof_risk_score": f"{spoof_result['total_risk_score']}%",
        },

        "victim_details": {
            "phone_number": metadata['to_number'],
            "name": metadata['to_name'].replace("Victim - ", ""),
            "location": f"{metadata['to_city']}, {metadata['to_state']}, India",
            "financial_loss_occurred": False,
            "alert_delivered": True,
            "alert_method": "WhatsApp Business API + Dashboard SocketIO",
        },

        "evidence_package": {
            "evidence_hash_sha256": evidence_hash,
            "previous_chain_hash": previous_hash,
            "chain_hash_sha256": chain_hash,
            "hash_algorithm": "SHA-256",
            "chain_method": "Sequential hash chain: SHA256(prev_hash:evidence_hash:report_id:timestamp)",
            "evidence_items": list(evidence_items.keys()),
            "evidence_count": len(evidence_items),
            "tamper_proof": True,
            "legal_admissibility": "Evidence package hash-chained per IT Act Section 65B(4) — Certificate requirements for electronic records",
        },

        "recommended_actions": [
            "Block caller number across all Indian telecom networks via TRAI CFCFRMS",
            "Initiate trace-back to VoIP originating gateway via INTERPOL channels",
            "Add caller pattern to national scam number database",
            f"File FIR under sections: {', '.join([s['section'] for s in legal_sections])}",
        ],
    }

    return mha_report


def append_audit_log(mha_report, metadata, spoof_result, classification):
    """
    Appends the incident to a tamper-proof JSONL audit log with SHA-256 hash chaining.
    Each entry links to the previous via hash chain for legal admissibility.
    """
    previous_hash = _get_previous_hash()

    log_entry = {
        "log_id": mha_report['report_id'],
        "timestamp": mha_report['timestamp'],
        "incident_type": metadata['scam_label'],
        "caller_number": metadata['from_number'],
        "caller_country": metadata['caller_country'],
        "victim_number": metadata['to_number'],
        "spoof_score": spoof_result['total_risk_score'],
        "nlp_label": classification['label'],
        "nlp_score": classification['risk_score'],
        "legal_sections": [s['section'] for s in mha_report['legal_sections']],
        "financial_loss_prevented": True,
        "evidence_hash": mha_report['evidence_package']['evidence_hash_sha256'],
        "previous_hash": previous_hash,
        "chain_hash": mha_report['evidence_package']['chain_hash_sha256'],
    }

    try:
        os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)
        with open(AUDIT_LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, default=str) + '\n')
    except Exception as e:
        print(f"  {C.RED}[ERROR] Failed to write audit log: {e}{C.RESET}")

    return log_entry


def print_response_actions(whatsapp, telecom, mha_report, audit_entry):
    """Prints all three response actions to the terminal."""
    w = 80

    print()
    print(f"{C.BG_RED}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print(f"{C.BG_RED}{C.WHITE}{C.BOLD}{'FRAUD SHIELD — AUTOMATED RESPONSE ACTIONS':^{w}}{C.RESET}")
    print(f"{C.BG_RED}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print()

    # 1. WhatsApp Alert
    print(f"  {C.GREEN}{C.BOLD}╔══ ACTION 1: WHATSAPP VICTIM ALERT ═════════════════════════════╗{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  API          : {C.CYAN}Twilio WhatsApp Business API{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  To           : {C.GREEN}{C.BOLD}{whatsapp['to_number']}{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  Status       : {C.GREEN}{C.BOLD}✓ {whatsapp['delivery_status'].upper()}{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  Message SID  : {C.DIM}{whatsapp['message_sid']}{C.RESET}")
    print(f"  {C.GREEN}║{C.RESET}  Sent At      : {whatsapp['sent_at']}")
    print(f"  {C.GREEN}║{C.RESET}  Content      : {C.YELLOW}\"⚠️ SCAM CALL ALERT — Do NOT answer {whatsapp['to_number'].split(':')[1]}...\"{C.RESET}")
    print(f"  {C.GREEN}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # 2. Telecom Flagging
    print(f"  {C.YELLOW}{C.BOLD}╔══ ACTION 2: TELECOM PROVIDER FLAG ═════════════════════════════╗{C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  API          : {C.CYAN}TRAI CFCFRMS Fraud Management API{C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  Endpoint     : {C.DIM}{telecom['endpoint']}{C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  Request ID   : {telecom['request_id']}")
    print(f"  {C.YELLOW}║{C.RESET}  Status       : {C.GREEN}{C.BOLD}✓ {telecom['status']} ({telecom['status_code']}){C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  Flagged #    : {C.RED}{C.BOLD}{telecom['payload']['flagged_number']}{C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  Action       : {C.RED}{C.BOLD}{telecom['payload']['recommended_action']}{C.RESET}")
    print(f"  {C.YELLOW}║{C.RESET}  Priority     : {telecom['payload']['priority']}")
    print(f"  {C.YELLOW}║{C.RESET}  Block Scope  : {telecom['response']['block_scope']}")
    print(f"  {C.YELLOW}║{C.RESET}  Notified     : {', '.join(telecom['response']['notification_sent_to'])}")
    print(f"  {C.YELLOW}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # 3. MHA Report
    print(f"  {C.MAGENTA}{C.BOLD}╔══ ACTION 3: MHA INCIDENT REPORT ═══════════════════════════════╗{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  Report ID    : {C.CYAN}{C.BOLD}{mha_report['report_id']}{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  Type         : {mha_report['incident_details']['incident_type']}")
    print(f"  {C.MAGENTA}║{C.RESET}  Severity     : {C.RED}{C.BOLD}{mha_report['incident_details']['severity']}{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  Status       : {C.GREEN}{mha_report['incident_details']['status']}{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  Loss         : {C.GREEN}{C.BOLD}{mha_report['incident_details']['financial_loss']}{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  {C.BOLD}Legal Sections:{C.RESET}")
    for sec in mha_report['legal_sections']:
        print(f"  {C.MAGENTA}║{C.RESET}    {C.RED}▸ {sec['section']}{C.RESET} — {sec['title']}")
    print(f"  {C.MAGENTA}║{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}  {C.BOLD}Evidence Hash Chain:{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}    Evidence SHA-256 : {C.DIM}{mha_report['evidence_package']['evidence_hash_sha256'][:32]}...{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}    Chain SHA-256    : {C.DIM}{mha_report['evidence_package']['chain_hash_sha256'][:32]}...{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}    Prev Hash        : {C.DIM}{mha_report['evidence_package']['previous_chain_hash'][:32]}...{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}    Tamper-Proof     : {C.GREEN}{C.BOLD}✓ YES{C.RESET}")
    print(f"  {C.MAGENTA}║{C.RESET}    Legal Basis      : {C.DIM}IT Act Section 65B(4){C.RESET}")
    print(f"  {C.MAGENTA}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()

    # Audit log
    print(f"  {C.DIM}╔══ TAMPER-PROOF AUDIT LOG ══════════════════════════════════════╗{C.RESET}")
    print(f"  {C.DIM}║{C.RESET}  Log Entry     : {audit_entry['log_id']}")
    print(f"  {C.DIM}║{C.RESET}  Chain Hash    : {C.DIM}{audit_entry['chain_hash'][:40]}...{C.RESET}")
    print(f"  {C.DIM}║{C.RESET}  Written To    : {C.DIM}data/audit_log.jsonl{C.RESET}")
    print(f"  {C.DIM}╚══════════════════════════════════════════════════════════════════╝{C.RESET}")
    print()
    print(f"{C.BG_RED}{C.WHITE}{C.BOLD}{'=' * w}{C.RESET}")
    print()
