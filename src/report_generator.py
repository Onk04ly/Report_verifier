"""
Medical Report Generator
Generates professional PDF and HTML reports from verification results
"""

import json
import pandas as pd
from datetime import datetime
import os
from pathlib import Path

class MedicalReportGenerator:
    """Generates professional reports from medical verification results"""
    
    def __init__(self):
        self.template_styles = """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                margin: 40px;
                color: #333;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
            }
            .summary-card {
                background: #f8f9fa;
                border-left: 5px solid #007bff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .risk-low { border-left-color: #28a745; background: #d4edda; }
            .risk-medium { border-left-color: #ffc107; background: #fff3cd; }
            .risk-high { border-left-color: #dc3545; background: #f8d7da; }
            .claim-item {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .confidence-high { border-left: 4px solid #28a745; }
            .confidence-medium { border-left: 4px solid #ffc107; }
            .confidence-low { border-left: 4px solid #dc3545; }
            .certainty-negative { background: #f8d7da; border: 1px solid #dc3545; }
            .certainty-uncertain { background: #e2e3e5; border: 1px solid #6c757d; }
            .certainty-positive { background: #d4edda; border: 1px solid #28a745; }
            .enhanced-metrics {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .metric-card {
                padding: 15px;
                border-radius: 8px;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            .metric-value { font-size: 24px; font-weight: bold; color: #007bff; }
            .confidence-medium { border-left: 4px solid #ffc107; }
            .confidence-low { border-left: 4px solid #dc3545; }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .stat-number {
                font-size: 2.5em;
                font-weight: bold;
                color: #007bff;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #dee2e6;
            }
            th {
                background: #f8f9fa;
                font-weight: 600;
            }
            .footer {
                margin-top: 40px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 8px;
                text-align: center;
                color: #6c757d;
            }
        </style>
        """
    
    def generate_html_report(self, verification_results, output_path):
        """Generate a comprehensive HTML report"""
        
        # Calculate enhanced statistics
        total_summaries = len(verification_results)
        total_claims = sum(r['total_claims'] for r in verification_results)
        total_negated = sum(r['risk_assessment']['stats'].get('negated_claims', 0) for r in verification_results)
        total_uncertain = sum(r['risk_assessment']['stats'].get('uncertain_claims', 0) for r in verification_results)
        
        # Risk distribution
        risk_levels = [r['risk_assessment']['level'] for r in verification_results]
        risk_counts = pd.Series(risk_levels).value_counts()
        
        # Confidence distribution
        all_confidences = []
        for result in verification_results:
            for claim in result['claims']:
                all_confidences.append(claim['verification_confidence'])
        
        conf_counts = pd.Series(all_confidences).value_counts()
        
        high_risk_count = sum(1 for r in verification_results if 'HIGH_RISK' in r['risk_assessment']['level'])
        low_confidence_count = sum(1 for conf in all_confidences if conf == 'LOW')
        
        # Calculate enhanced ratios
        negation_ratio = (total_negated / total_claims * 100) if total_claims > 0 else 0
        uncertainty_ratio = (total_uncertain / total_claims * 100) if total_claims > 0 else 0
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Medical Report Verification Analysis</title>
            {self.template_styles}
        </head>
        <body>
            <div class="header">
                <h1> Medical Report Verification Analysis</h1>
                <p>AI-Powered Hallucination Detection Report</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{total_summaries}</div>
                    <div>Summaries Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_claims}</div>
                    <div>Medical Claims</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_claims/total_summaries:.1f}</div>
                    <div>Avg Claims/Summary</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{high_risk_count}</div>
                    <div>High Risk Summaries</div>
                </div>
            </div>
            
            <div class="enhanced-metrics">
                <div class="metric-card">
                    <div class="metric-value">{total_negated}</div>
                    <div> Negated Claims</div>
                    <div>({negation_ratio:.1f}%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_uncertain}</div>
                    <div> Uncertain Claims</div>
                    <div>({uncertainty_ratio:.1f}%)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{total_claims - total_negated - total_uncertain}</div>
                    <div> Positive Claims</div>
                    <div>({100 - negation_ratio - uncertainty_ratio:.1f}%)</div>
                </div>
            </div>
            
            <div class="summary-card">
                <h2> Overall Risk Assessment</h2>
                <div class="stats-grid">
        """
        
        # Add risk level cards
        for risk, count in risk_counts.items():
            risk_class = "risk-low" if "LOW" in risk else "risk-medium" if "MEDIUM" in risk else "risk-high"
            percentage = (count/total_summaries)*100
            emoji = "" if "LOW" in risk else "" if "MEDIUM" in risk else ""
            
            html_content += f"""
                    <div class="stat-card {risk_class}">
                        <div class="stat-number">{emoji}</div>
                        <div><strong>{risk}</strong></div>
                        <div>{count} summaries ({percentage:.1f}%)</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
            
            <div class="summary-card">
                <h2> Confidence Level Distribution</h2>
                <div class="stats-grid">
        """
        
        # Add confidence level cards
        for conf, count in conf_counts.items():
            conf_class = "risk-low" if conf == "HIGH" else "risk-medium" if conf == "MEDIUM" else "risk-high"
            percentage = (count/total_claims)*100
            emoji = "" if conf == "HIGH" else "" if conf == "MEDIUM" else ""
            
            html_content += f"""
                    <div class="stat-card {conf_class}">
                        <div class="stat-number">{emoji}</div>
                        <div><strong>{conf} Confidence</strong></div>
                        <div>{count} claims ({percentage:.1f}%)</div>
                    </div>
            """
        
        html_content += """
                </div>
            </div>
            
            <h2> Detailed Summary Analysis</h2>
        """
        
        # Add detailed summary analysis
        for i, result in enumerate(verification_results, 1):
            risk_level = result['risk_assessment']['level']
            risk_class = "risk-low" if "LOW_RISK" in risk_level else "risk-medium" if "MEDIUM" in risk_level else "risk-high"
            risk_emoji = "" if "LOW_RISK" in risk_level else "" if "MEDIUM" in risk_level else ""
            
            html_content += f"""
            <div class="summary-card {risk_class}">
                <h3>{risk_emoji} Summary {i}: {result['summary_id']}</h3>
                <p><strong>Original Text:</strong> {result['original_text']}</p>
                <p><strong>Risk Level:</strong> {risk_level}</p>
                <p><strong>Risk Reason:</strong> {result['risk_assessment']['reason']}</p>
                <p><strong>Total Claims:</strong> {result['total_claims']}</p>
                
                <h4> Extracted Claims:</h4>
            """
            
            if result['claims']:
                for j, claim in enumerate(result['claims'], 1):
                    conf_class = f"confidence-{claim['verification_confidence'].lower()}"
                    conf_emoji = "" if claim['verification_confidence'] == 'HIGH' else "" if claim['verification_confidence'] == 'MEDIUM' else ""
                    
                    # Enhanced certainty analysis
                    certainty_class = f"certainty-{claim.get('certainty_modifier', 'positive')}"
                    certainty_indicator = ""
                    if claim.get('has_negation', False):
                        certainty_indicator += " "
                    if claim.get('has_uncertainty', False):
                        certainty_indicator += " "

                    html_content += f"""
                    <div class="claim-item {conf_class} {certainty_class}">
                        <strong>Claim {j}:</strong> {claim['claim_text']}{certainty_indicator}<br>
                        <strong>Type:</strong> {claim['type']}<br>
                        <strong>Medical Entities:</strong> {', '.join(claim['medical_entities']) if claim['medical_entities'] else 'None'}<br>
                        <strong>{conf_emoji} Verification:</strong> {claim['verification_confidence']} (Score: {claim['verification_score']:.3f})<br>
                        <strong>Certainty:</strong> {claim.get('certainty_modifier', 'positive').upper()}<br>
                    """
                    
                    if claim['supporting_facts']:
                        top_fact = claim['supporting_facts'][0]
                        html_content += f"""
                        <strong> Supporting Evidence:</strong> {top_fact['text'][:150]}...<br>
                        <strong> Similarity:</strong> {top_fact['distance']:.3f}
                        """
                    
                    if claim['verification_confidence'] == 'LOW':
                        html_content += "<br><strong> WARNING:</strong> This claim may be hallucinated or unsupported!"
                    
                    html_content += "</div>"
            else:
                html_content += "<p> No medical claims extracted from this summary.</p>"
            
            html_content += "</div>"
        
        # Add recommendations
        html_content += f"""
            <div class="summary-card">
                <h2> Recommendations</h2>
        """
        
        if high_risk_count == 0 and (low_confidence_count / len(all_confidences) * 100 if all_confidences else 0) < 10:
            html_content += """
                <p><strong> EXCELLENT:</strong> All medical summaries show strong evidence support.</p>
                <ul>
                    <li>No high-risk summaries detected</li>
                    <li>Very low percentage of low-confidence claims</li>
                    <li>These summaries appear medically accurate and well-supported</li>
                </ul>
            """
        elif high_risk_count <= 1 and (low_confidence_count / len(all_confidences) * 100 if all_confidences else 0) < 20:
            html_content += f"""
                <p><strong> GOOD:</strong> Most summaries are well-supported with minor concerns.</p>
                <ul>
                    <li>{high_risk_count} high-risk summaries require review</li>
                    <li>{low_confidence_count / len(all_confidences) * 100 if all_confidences else 0:.1f}% of claims have low confidence</li>
                    <li>Recommend human review of flagged claims</li>
                </ul>
            """
        else:
            html_content += f"""
                <p><strong> CAUTION:</strong> Multiple summaries show potential hallucination risks.</p>
                <ul>
                    <li>{high_risk_count} high-risk summaries detected</li>
                    <li>{low_confidence_count / len(all_confidences) * 100 if all_confidences else 0:.1f}% of claims have low confidence</li>
                    <li><strong>IMMEDIATE human expert review recommended</strong></li>
                </ul>
            """
        
        html_content += """
                <h3> Recommended Actions:</h3>
                <ol>
                    <li>Review low-confidence claims manually</li>
                    <li>Verify claims against additional medical sources</li>
                    <li>Consider expanding the knowledge base</li>
                    <li>Flag high-risk summaries for expert review</li>
                    <li>Implement additional validation steps</li>
                    <li>Monitor verification performance over time</li>
                </ol>
                
                <h3> Clinical Safety Notes:</h3>
                <ul>
                    <li>This tool assists but does not replace clinical judgment</li>
                    <li>All medical decisions should involve qualified healthcare professionals</li>
                    <li>Use verification results as a quality assurance layer</li>
                </ul>
            </div>
            
            <div class="footer">
                <p>Generated by Medical Report Verification System</p>
                <p>For research and educational purposes</p>
            </div>
        </body>
        </html>
        """
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    

    
    def generate_all_reports(self, verification_results, base_filename):
        """Generate HTML report only"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = Path(base_filename).stem
        output_dir = Path(base_filename).parent
        
        # HTML Report only
        html_path = output_dir / f"{base_path}_{timestamp}.html"
        html_report = self.generate_html_report(verification_results, html_path)
        
        return html_report

if __name__ == "__main__":
    # Test the report generator
    print(" Testing Medical Report Generator...")
    generator = MedicalReportGenerator()
    print(" Report generator ready!")
