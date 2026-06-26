import os
import sys
import numpy as np

# Ensure module path is included
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.scam_classifier import train_scam_model, classify_text
from modules.currency_detector import analyze_banknote
from modules.fraud_graph import analyze_transactions, generate_interactive_graph, generate_pdf_report, generate_mock_transactions_csv

def test_nlp_module():
    print("\n--- TEST NLP SCAM CLASSIFIER ---")
    print("Training NLP models...")
    train_scam_model()
    
    test_cases = [
        "I am calling from CBI cyber investigation department. Your account is linked to drug money. Stay on call or you go to jail.",
        "Hi sweetheart, don't forget to buy milk on your way home. See you tonight!",
        "Congratulations! You won KBC lottery of 25 Lakh Rupees. Deposit 20000 processing tax via UPI now."
    ]
    
    for case in test_cases:
        res = classify_text(case)
        print(f"Transcript snippet: '{case[:50]}...'")
        print(f" -> Label: {res['label']} (Risk: {res['risk_score']}%), Subcategory: {res['category']}")
        if res['label'] == "SCAM":
            print(f" -> Keywords: {res['highlighted_phrases']}")
            print(" -> MHA complaint draft generated.")
            
def test_cv_module():
    print("\n--- TEST CV BANKNOTE ANALYZER ---")
    # Build a standard dummy canvas simulating a note
    dummy_img = np.ones((360, 800, 3), dtype=np.uint8) * 128
    
    # Run test
    analysis = analyze_banknote(dummy_img, "test_note_real.jpg")
    print(f"Denomination Detected: {analysis['denomination']}")
    print(f"Note status: {analysis['status']} (Confidence: {analysis['confidence']}%)")
    print("Checked features:")
    for feature, det in analysis['features'].items():
        print(f" - {feature}: {det['status']} ({det['details']})")
        
def test_graph_module():
    print("\n--- TEST GRAPH LINK ANALYSIS ---")
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    csv_path = os.path.join(data_dir, 'sample_transactions.csv')
    
    # Generate mock CSV if not exists
    generate_mock_transactions_csv(csv_path)
    
    # Analyze
    G, anom_df, cycling_paths = analyze_transactions(csv_path)
    print(f"Graph nodes loaded: {len(G.nodes())}, edges: {len(G.edges())}")
    print("Top anomalous nodes detected:")
    print(anom_df.head(4)[['account_id', 'risk_score', 'risk_label', 'reasons']])
    
    if len(cycling_paths) > 0:
        print(f"Detected {len(cycling_paths)} money laundering rapid loops. Example loop path:")
        print(f" - {cycling_paths[0][0]} -> {cycling_paths[0][1]} -> {cycling_paths[0][2]} in {cycling_paths[0][3]} mins")
        
    # Test file output
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    html_out = os.path.join(static_dir, 'fraud_graph.html')
    generate_interactive_graph(G, anom_df, html_out)
    
    pdf_out = os.path.join(data_dir, 'evidence_package.pdf')
    generate_pdf_report(anom_df, cycling_paths, pdf_out)
    print("PDF and HTML reports generated successfully.")

if __name__ == "__main__":
    print("=== STARTING FRAUD SHIELD MODULE DIAGNOSTICS ===")
    test_nlp_module()
    test_cv_module()
    test_graph_module()
    print("\n=== DIAGNOSTICS COMPLETED SUCCESSFULLY ===")
