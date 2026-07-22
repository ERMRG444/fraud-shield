import os
import networkx as nx
import pandas as pd
import numpy as np
from pyvis.network import Network
import matplotlib
matplotlib.use('Agg') # Thread-safe backend for headless servers
import matplotlib.pyplot as plt

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

class NumberedCanvas(canvas.Canvas):
    """Canvas class to dynamically calculate page numbers in PDF."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 750, 558, 750)
        self.drawString(54, 755, "FRAUD SHIELD | DIGITAL CYBER CRIME INVESTIGATION REPORT")
        
        # Footer
        self.line(54, 50, 558, 50)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 38, page_text)
        self.drawString(54, 38, "CONFIDENTIAL - LAW ENFORCEMENT INTERNAL USE ONLY")
        self.restoreState()


def analyze_transactions(csv_path):
    """
    Parses transaction CSV, builds NetworkX graph, executes anomaly detection,
    and returns risk-ranked results.
    """
    # 1. Load Data
    df = pd.read_csv(csv_path)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # Ensure standard datatypes
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # 2. Build Directed Graph
    G = nx.DiGraph()
    for _, row in df.iterrows():
        sender = str(row['sender_id'])
        receiver = str(row['receiver_id'])
        amount = float(row['amount'])
        
        # Add edge with transaction attributes
        if G.has_edge(sender, receiver):
            G[sender][receiver]['amount'] += amount
            G[sender][receiver]['tx_count'] += 1
            G[sender][receiver]['timestamps'].append(row['timestamp'])
        else:
            G.add_edge(sender, receiver, 
                       amount=amount, 
                       tx_count=1, 
                       timestamps=[row['timestamp']],
                       location=row.get('location', 'N/A'),
                       device_id=row.get('device_id', 'N/A'))
            
    # Also guarantee all single nodes have initial properties
    for node in G.nodes():
        G.nodes[node]['in_volume'] = 0
        G.nodes[node]['out_volume'] = 0
        
    for u, v, data in G.edges(data=True):
        G.nodes[u]['out_volume'] += data['amount']
        G.nodes[v]['in_volume'] += data['amount']

    # 3. Community Detection (Louvain)
    # Convert to undirected graph for community detection
    undirected_G = G.to_undirected()
    try:
        from networkx.community import louvain_communities
        communities = louvain_communities(undirected_G, seed=42)
    except Exception:
        # Fallback if NetworkX version is older
        communities = [set(undirected_G.nodes())]
        
    community_map = {}
    for idx, comm in enumerate(communities):
        for node in comm:
            community_map[node] = idx

    # 4. Anomaly Detection & Scoring
    anomalies = {}
    
    # Calculate degree indices
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    # Identify Rapid Cycling (Money Mule chains: A -> B -> C with short delay)
    # We search for paths where a node receives money and then sends it out quickly
    rapid_cyclers = set()
    cycling_paths = []
    
    for middle_node in G.nodes():
        # Find predecessors and successors
        preds = list(G.predecessors(middle_node))
        succs = list(G.successors(middle_node))
        
        if preds and succs:
            # Check timestamps of in-transacts and out-transacts
            for p in preds:
                in_times = G[p][middle_node]['timestamps']
                for s in succs:
                    out_times = G[middle_node][s]['timestamps']
                    
                    # Verify if any out-transact happens quickly after in-transact
                    for t_in in in_times:
                        if pd.isna(t_in):
                            continue
                        for t_out in out_times:
                            if pd.isna(t_out):
                                continue
                            # Time difference in minutes
                            time_diff = (t_out - t_in).total_seconds() / 60.0
                            # Money cycle check (incoming is sent out within 180 minutes)
                            if 0 <= time_diff <= 180:
                                rapid_cyclers.add(middle_node)
                                cycling_paths.append((p, middle_node, s, round(time_diff, 1)))
                                break

    # Identify Temporal Clustering (burst transactions from node)
    temporal_bursts = set()
    for node in G.nodes():
        node_timestamps = []
        for u, v, data in G.edges(node, data=True): # out edges
            node_timestamps.extend([t for t in data['timestamps'] if not pd.isna(t)])
        for u, v, data in G.in_edges(node, data=True): # in edges
            node_timestamps.extend([t for t in data['timestamps'] if not pd.isna(t)])
            
        if len(node_timestamps) >= 4:
            sorted_times = sorted(node_timestamps)
            # Check if any window of N transactions is very tight
            for i in range(len(sorted_times) - 3):
                diff = (sorted_times[i+3] - sorted_times[i]).total_seconds() / 60.0
                if diff <= 15: # 4 transactions within 15 minutes
                    temporal_bursts.add(node)
                    break

    # Calculate Anomaly Score (0 - 100)
    for node in G.nodes():
        score = 0.0
        reasons = []
        
        deg_in = in_degrees.get(node, 0)
        deg_out = out_degrees.get(node, 0)
        total_deg = deg_in + deg_out
        
        # Rule 1: High In-degree (Money Pooler / Hub node)
        if deg_in >= 4:
            score += 35
            reasons.append(f"Hub Account ({deg_in} incoming victims)")
        elif deg_in >= 2:
            score += 15
            reasons.append("Incoming Hub tendency")
            
        # Rule 2: Money Mule Rapid Cycling
        if node in rapid_cyclers:
            score += 45
            reasons.append("Mule Activity (Rapid funds cycling)")
            
        # Rule 3: Burst Activity
        if node in temporal_bursts:
            score += 20
            reasons.append("Temporal Transaction Burst")
            
        # Rule 4: High velocity ratio asymmetry
        in_vol = G.nodes[node]['in_volume']
        out_vol = G.nodes[node]['out_volume']
        if in_vol > 100000 and out_vol > 0:
            ratio = abs(in_vol - out_vol) / max(in_vol, out_vol)
            if ratio < 0.05: # Receives high amount, drains almost completely
                score += 15
                reasons.append("High Liquidity Draining (Mule profile)")
                
        score = min(score, 100.0)
        
        # Classify node type
        if score >= 70:
            risk_label = "CRITICAL / MULE"
        elif score >= 40:
            risk_label = "HIGH RISK"
        elif score >= 15:
            risk_label = "SUSPICIOUS"
        else:
            risk_label = "LOW RISK"
            
        anomalies[node] = {
            "account_id": node,
            "in_degree": deg_in,
            "out_degree": deg_out,
            "in_volume": round(in_vol, 2),
            "out_volume": round(out_vol, 2),
            "community_id": community_map.get(node, 0),
            "risk_score": score,
            "risk_label": risk_label,
            "reasons": ", ".join(reasons) if reasons else "Normal account activities"
        }

    # Convert to dataframe and sort by score
    anom_df = pd.DataFrame(anomalies.values())
    anom_df = anom_df.sort_values(by="risk_score", ascending=False)
    
    return G, anom_df, cycling_paths


def generate_interactive_graph(G, anom_df, output_html_path):
    """Generates a premium PyVis interactive network visualization HTML file."""
    # Create pyvis network
    net = Network(height="550px", width="100%", bgcolor="#0b0f19", font_color="#e2e8f0", directed=True)
    
    # Configure physics engine for high-tech spacing
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -60,
          "centralGravity": 0.015,
          "springLength": 110,
          "springConstant": 0.08
        },
        "maxVelocity": 45,
        "solver": "forceAtlas2Based",
        "timestep": 0.35,
        "stabilization": {"iterations": 100}
      },
      "edges": {
        "smooth": {"type": "dynamic"}
      }
    }
    """)
    
    # Color palette for communities
    community_colors = [
        "#3B82F6", # Neon Blue
        "#10B981", # Emerald
        "#8B5CF6", # Purple
        "#F59E0B", # Amber
        "#EC4899", # Pink
        "#14B8A6", # Teal
        "#06B6D4", # Cyan
        "#84CC16"  # Lime
    ]
    
    # Populate pyvis nodes
    for _, row in anom_df.iterrows():
        node_id = str(row['account_id'])
        score = row['risk_score']
        comm_id = row['community_id']
        
        # Color nodes: High risk are solid glowing red/orange, others match community
        if score >= 70:
            color = "#EF4444" # Red
            size = 35
        elif score >= 40:
            color = "#F97316" # Orange
            size = 28
        else:
            # Map community ID to color palette
            color = community_colors[comm_id % len(community_colors)]
            size = 18 + int(row['in_degree'] * 3)
            
        hover_title = f"""
        <b>Account ID:</b> {node_id}<br/>
        <b>Risk Level:</b> {row['risk_label']} ({score}%)<br/>
        <b>In-Volume:</b> Rs {row['in_volume']:,}<br/>
        <b>Out-Volume:</b> Rs {row['out_volume']:,}<br/>
        <b>Connections:</b> In: {row['in_degree']}, Out: {row['out_degree']}<br/>
        <b>Flagged Reasons:</b> {row['reasons']}
        """
        
        net.add_node(node_id, 
                     label=f"Acc: {node_id}", 
                     title=hover_title, 
                     color=color, 
                     size=size,
                     borderWidth=2)
                     
    # Populate pyvis edges
    for u, v, data in G.edges(data=True):
        volume = data['amount']
        # Scaled thickness based on log of volume
        thickness = int(np.log10(volume + 1) * 1.5) + 1
        
        # Hover title for edge
        edge_title = f"Transacted Amount: Rs {volume:,}<br/>Count: {data['tx_count']}"
        
        net.add_edge(u, v, 
                     value=volume, 
                     title=edge_title, 
                     width=thickness, 
                     color="#475569", 
                     arrowStrikethrough=False)
                     
    # Generate and save HTML
    net.save_graph(output_html_path)
    print(f"Interactive fraud graph generated at {output_html_path}.")


def generate_pdf_report(anom_df, cycling_paths, output_pdf_path):
    """Generates a professional PDF evidence package report using ReportLab."""
    doc = SimpleDocTemplate(
        output_pdf_path, 
        pagesize=letter,
        rightMargin=54, leftMargin=54, 
        topMargin=80, bottomMargin=60
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Palette
    primary_color = colors.HexColor("#0f172a") # Dark Slate
    accent_color = colors.HexColor("#ef4444")  # Crimson Red
    text_color = colors.HexColor("#334155")
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=25
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=primary_color,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=text_color,
        spaceAfter=10
    )
    
    danger_body = ParagraphStyle(
        'DangerBodyText',
        parent=body_style,
        textColor=accent_color,
        fontName='Helvetica-Bold'
    )
    
    # Table styles
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )
    
    table_body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=text_color
    )
    
    table_body_bold_style = ParagraphStyle(
        'TableBodyBold',
        parent=table_body_style,
        fontName='Helvetica-Bold',
        textColor=primary_color
    )

    story = []
    
    # --- Page 1: COVER & EXECUTIVE SUMMARY ---
    story.append(Spacer(1, 15))
    story.append(Paragraph("FRAUD GRAPH EVIDENCE REPORT", title_style))
    story.append(Paragraph("CYBER CRIME LINK ANALYSIS & MONEY LAUNDERING INVESTIGATION", subtitle_style))
    
    summary_text = (
        "<b>Executive Summary:</b> This document contains formal evidence compiled by the "
        "Fraud Shield Network Analysis Engine. A transaction ledger was analyzed to build a directed "
        "graph showing financial flow. Using degree-centrality profiles, rapid loop checks, and "
        "community detection (Louvain), specific accounts have been flagged as showing anomalous "
        "behavior consistent with <b>money mule operations</b> and <b>pooling hubs</b>. "
        "Action is recommended to freeze critical accounts listed below."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 15))
    
    # Network metrics table
    total_nodes = len(anom_df)
    critical_nodes = len(anom_df[anom_df['risk_score'] >= 70])
    high_nodes = len(anom_df[(anom_df['risk_score'] >= 40) & (anom_df['risk_score'] < 70)])
    
    metrics_data = [
        [Paragraph("<b>Investigation Parameter</b>", table_body_bold_style), Paragraph("<b>Observed Metrics</b>", table_body_bold_style)],
        ["Total Investigated Accounts", f"{total_nodes} nodes"],
        ["Mule / Critical Accounts Flagged", f"{critical_nodes} nodes (Score >= 70%)"],
        ["High-Risk Accounts", f"{high_nodes} nodes (Score 40-70%)"],
        ["Suspicious Money Chains Detected", f"{len(cycling_paths)} chains"]
    ]
    
    t_metrics = Table(metrics_data, colWidths=[230, 230])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#F1F5F9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 20))
    
    # --- Section: Flagged Nodes List ---
    story.append(Paragraph("Risk-Ranked Suspect Accounts", section_style))
    
    node_table_data = [[
        Paragraph("Account ID", table_header_style),
        Paragraph("Risk Score", table_header_style),
        Paragraph("Risk Level", table_header_style),
        Paragraph("In/Out Volume (Rs)", table_header_style),
        Paragraph("Anomaly Signature", table_header_style)
    ]]
    
    # Add top 12 riskiest nodes to report
    top_risky = anom_df.head(12)
    for _, r in top_risky.iterrows():
        score_val = r['risk_score']
        score_text = f"{score_val}%"
        
        # Color code label based on risk
        lbl = r['risk_label']
        if score_val >= 70:
            lbl_p = Paragraph(f"<b>{lbl}</b>", ParagraphStyle('crit', parent=table_body_style, textColor=colors.HexColor("#EF4444")))
        elif score_val >= 40:
            lbl_p = Paragraph(f"<b>{lbl}</b>", ParagraphStyle('high', parent=table_body_style, textColor=colors.HexColor("#F97316")))
        else:
            lbl_p = Paragraph(lbl, table_body_style)
            
        node_table_data.append([
            Paragraph(str(r['account_id']), table_body_bold_style),
            Paragraph(score_text, table_body_bold_style),
            lbl_p,
            Paragraph(f"In: {r['in_volume']:,}<br/>Out: {r['out_volume']:,}", table_body_style),
            Paragraph(r['reasons'], table_body_style)
        ])
        
    t_nodes = Table(node_table_data, colWidths=[65, 55, 75, 110, 155])
    t_nodes.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
    ]))
    
    story.append(t_nodes)
    
    # --- Page 2: SUSPICIOUS LOOPS & EVIDENCE ---
    if len(cycling_paths) > 0:
        story.append(PageBreak())
        story.append(Spacer(1, 10))
        story.append(Paragraph("Money Laundering Rapid Cycling Details", section_style))
        story.append(Paragraph(
            "Rapid cycling represents automated or manual split-second routing of funds "
            "where an account immediately drains incoming funds to a third account, acting "
            "as a classic money-mule layering step to evade detection. The following paths were flagged:", 
            body_style
        ))
        
        path_table_data = [[
            Paragraph("Source Acct (Victim/Sender)", table_header_style),
            Paragraph("Mule Acct (Layering)", table_header_style),
            Paragraph("Destination Acct (Pooling)", table_header_style),
            Paragraph("Time Gap (Minutes)", table_header_style)
        ]]
        
        # Display top 15 paths
        for idx, path in enumerate(cycling_paths[:15]):
            path_table_data.append([
                Paragraph(path[0], table_body_style),
                Paragraph(f"<b>{path[1]}</b>", ParagraphStyle('mule', parent=table_body_style, textColor=colors.HexColor("#EF4444"))),
                Paragraph(path[2], table_body_style),
                Paragraph(f"{path[3]} min", table_body_bold_style)
            ])
            
        t_paths = Table(path_table_data, colWidths=[115, 115, 115, 115])
        t_paths.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t_paths)
        
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Evidence report generated at {output_pdf_path}.")


def generate_mock_transactions_csv(output_csv_path):
    """Generates a synthetic transaction CSV for testing and demo purposes."""
    np.random.seed(42)
    # Generate 15 nodes (users)
    # Node 101, 102, 103 are victims
    # Node 500 is a Hub Node (pooling funds)
    # Node 201, 202, 203 are money mules that cycle money immediately to 900
    
    rows = [
        # Victim -> Hub transfers
        ["101", "500", 45000, "2026-06-23 10:00:00", "New Delhi", "D-Android-01"],
        ["102", "500", 62000, "2026-06-23 10:15:00", "Mumbai", "D-iPhone-03"],
        ["103", "500", 125000, "2026-06-23 10:30:00", "Bengaluru", "D-Android-05"],
        ["104", "500", 30000, "2026-06-23 10:45:00", "Kolkata", "D-Android-09"],
        
        # Victim -> Mule -> Pool transfers (Rapid Cycling)
        # Victim 105 pays Mule 201, who pays Pool 900 in 5 minutes
        ["105", "201", 80000, "2026-06-23 11:00:00", "Chennai", "D-Android-11"],
        ["201", "900", 79000, "2026-06-23 11:05:00", "Delhi", "D-Nokia-02"],
        
        # Victim 106 pays Mule 202, who pays Pool 900 in 12 minutes
        ["106", "202", 50000, "2026-06-23 11:15:00", "Hyderabad", "D-iPhone-04"],
        ["202", "900", 49500, "2026-06-23 11:27:00", "Pune", "D-Nokia-07"],
        
        # Victim 107 pays Mule 203, who pays Pool 900 in 2 minutes
        ["107", "203", 250000, "2026-06-23 11:40:00", "Ahmedabad", "D-Android-20"],
        ["203", "900", 249000, "2026-06-23 11:42:00", "Surat", "D-Samsung-15"],
        
        # Temporal cluster / Burst (Hub Node 888 receives 5 rapid transactions)
        ["108", "888", 15000, "2026-06-23 12:00:00", "Jaipur", "D-Web-99"],
        ["109", "888", 12000, "2026-06-23 12:01:00", "Lucknow", "D-Web-99"],
        ["110", "888", 18000, "2026-06-23 12:02:00", "Patna", "D-Web-99"],
        ["111", "888", 14000, "2026-06-23 12:03:00", "Bhopal", "D-Web-99"],
        ["112", "888", 20000, "2026-06-23 12:04:00", "Indore", "D-Web-99"],
        
        # Legitimate regular transactions
        ["301", "302", 1500, "2026-06-23 09:30:00", "Dehradun", "D-Android-15"],
        ["302", "303", 800, "2026-06-23 14:15:00", "Noida", "D-iPhone-09"],
        ["304", "305", 2500, "2026-06-23 15:45:00", "Gurugram", "D-Android-88"],
        ["305", "306", 1200, "2026-06-23 18:22:00", "Faridabad", "D-Web-01"]
    ]
    
    df = pd.DataFrame(rows, columns=["sender_id", "receiver_id", "amount", "timestamp", "location", "device_id"])
    df.to_csv(output_csv_path, index=False)
    print(f"Mock transactions CSV generated at {output_csv_path}.")


def generate_layering_sample_csv(output_csv_path):
    """Generates a synthetic transaction CSV demonstrating rapid layering/cycling (multi-hop)."""
    rows = [
        # Chain 1: 401 -> 402 -> 403 -> 404 -> 900 (Rapid cycling)
        ["401", "402", 100000, "2026-06-23 10:00:00", "New Delhi", "D-Android-01"],
        ["402", "403", 99000, "2026-06-23 10:15:00", "Gurugram", "D-Android-02"],
        ["403", "404", 98000, "2026-06-23 10:30:00", "Noida", "D-Android-03"],
        ["404", "900", 97000, "2026-06-23 10:45:00", "Delhi", "D-Android-04"],
        
        # Chain 2: 411 -> 412 -> 413 -> 900 (Rapid cycling)
        ["411", "412", 50000, "2026-06-23 11:00:00", "Mumbai", "D-iPhone-01"],
        ["412", "413", 49500, "2026-06-23 11:10:00", "Thane", "D-iPhone-02"],
        ["413", "900", 49000, "2026-06-23 11:20:00", "Pune", "D-iPhone-03"],

        # Normal activity in background
        ["501", "502", 1200, "2026-06-23 09:15:00", "Kolkata", "D-Web-05"],
        ["502", "503", 850, "2026-06-23 13:40:00", "Patna", "D-Web-06"],
        ["504", "505", 2200, "2026-06-23 14:00:00", "Bengaluru", "D-Android-08"],
        ["505", "506", 1900, "2026-06-23 15:30:00", "Mysuru", "D-Android-09"]
    ]
    df = pd.DataFrame(rows, columns=["sender_id", "receiver_id", "amount", "timestamp", "location", "device_id"])
    df.to_csv(output_csv_path, index=False)
    print(f"Layering sample CSV generated at {output_csv_path}.")


def generate_burst_sample_csv(output_csv_path):
    """Generates a synthetic transaction CSV demonstrating high-velocity temporal bursts and pooling."""
    rows = [
        # Rapid pooling into Node 600 from 6 victims in 10 minutes
        ["801", "600", 25000, "2026-06-23 12:00:00", "Kolkata", "D-Web-10"],
        ["802", "600", 30000, "2026-06-23 12:02:00", "Patna", "D-Web-11"],
        ["803", "600", 15000, "2026-06-23 12:04:00", "Ranchi", "D-Web-12"],
        ["804", "600", 40000, "2026-06-23 12:06:00", "Bhubaneswar", "D-Web-13"],
        ["805", "600", 35000, "2026-06-23 12:08:00", "Guwahati", "D-Web-14"],
        ["806", "600", 20000, "2026-06-23 12:10:00", "Siliguri", "D-Web-15"],
        
        # Immediate draining of Node 600
        ["600", "999", 160000, "2026-06-23 12:15:00", "Delhi", "D-Android-99"],
        
        # Background legitimate transactions
        ["710", "711", 1500, "2026-06-23 13:00:00", "Mumbai", "D-iPhone-10"],
        ["711", "712", 1200, "2026-06-23 14:00:00", "Pune", "D-iPhone-11"],
        ["713", "714", 3000, "2026-06-23 15:00:00", "Bengaluru", "D-Android-21"]
    ]
    df = pd.DataFrame(rows, columns=["sender_id", "receiver_id", "amount", "timestamp", "location", "device_id"])
    df.to_csv(output_csv_path, index=False)
    print(f"Burst sample CSV generated at {output_csv_path}.")



if __name__ == "__main__":
    csv_out = os.path.join(DATA_DIR, "sample_transactions.csv")
    generate_mock_transactions_csv(csv_out)
    
    # Run analysis test
    G, anom_df, cycling_paths = analyze_transactions(csv_out)
    print("Risk-Ranked Nodes:")
    print(anom_df.head(5))
    
    html_out = os.path.join(STATIC_DIR, "fraud_graph.html")
    generate_interactive_graph(G, anom_df, html_out)
    
    pdf_out = os.path.join(DATA_DIR, "evidence_report.pdf")
    generate_pdf_report(anom_df, cycling_paths, pdf_out)
