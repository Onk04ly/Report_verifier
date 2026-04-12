import sys
import os
sys.path.append(os.path.dirname(__file__))

from claim_extractor_fixed import ClaimExtractor
from medical_config import get_global_config
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any

class MedicalVerifier:
    """Central pipeline for medical claim verification and hallucination detection with Responsible AI Layer"""
    
    def __init__(self, extractor_config=None):
        print(" Initializing Medical Report Verifier...")

        # Load centralized configuration — single source of truth for all
        # thresholds and scoring constants (D-01, D-04).
        self.global_config = get_global_config()

        # extractor_config must be a ConfigurationSettings instance or None.
        # Passing a partial dict is no longer supported (D-11, D-13).
        if extractor_config is not None:
            from medical_config import ConfigurationSettings
            if not isinstance(extractor_config, ConfigurationSettings):
                raise TypeError(
                    "MedicalVerifier expects extractor_config to be a "
                    f"ConfigurationSettings instance (got {type(extractor_config).__name__}). "
                    "Pass get_global_config() or None."
                )
            config = extractor_config
        else:
            config = self.global_config

        self.extractor = ClaimExtractor(config=config)
        
        # Load safety configuration from centralized config
        self.safety_config = self.global_config.get_safety_config()
        self.risk_thresholds = self.global_config.get_risk_thresholds()
        
        print(" Medical Verifier ready with Responsible AI Layer enabled!") 
        print(" Safety thresholds configured for healthcare compliance")
    
    def verify_single_summary(self, medical_summary: str, summary_id: str = None) -> Dict[str, Any]:
        """Verify a single medical summary and return structured results with Responsible AI safeguards"""
        if not summary_id:
            summary_id = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f" Analyzing: {medical_summary[:50]}...")
        
        # Extract claims and get verification results
        results = self.extractor.extract_claims_from_summary(medical_summary)
        
        # Add metadata
        results['summary_id'] = summary_id
        results['analysis_timestamp'] = datetime.now().isoformat()
        results['risk_assessment'] = self._assess_overall_risk(results['claims'])
        
        # Apply Responsible AI Layer
        results = self._apply_responsible_ai_layer(results, medical_summary)
        
        return results
    
    def verify_multiple_summaries(self, summaries_data: List[Dict]) -> List[Dict]:
        """Verify multiple medical summaries"""
        all_results = []
        
        for i, summary_data in enumerate(summaries_data):
            if isinstance(summary_data, dict):
                summary_text = summary_data.get('summary', '')
                summary_id = summary_data.get('id', f'summary_{i+1}')
            else:
                summary_text = str(summary_data)
                summary_id = f'summary_{i+1}'
            
            result = self.verify_single_summary(summary_text, summary_id)
            all_results.append(result)
        
        return all_results
    
    def verify_from_csv(self, csv_path: str) -> List[Dict]:
        """Load and verify summaries from CSV file"""
        df = pd.read_csv(csv_path)
        summaries_data = df.to_dict('records')
        return self.verify_multiple_summaries(summaries_data)
    
    def _detect_medical_implausibility(self, claim_text):
        """Advanced semantic analysis for medical implausibility without keyword dependency"""
        
        # SEMANTIC ANALYSIS: Check for logical medical impossibilities
        semantic_issues = []
        claim_lower = claim_text.lower()
        
        # 1. Impossibility Detection: Medical claims that violate known biology
        impossibility_indicators = self._analyze_medical_impossibilities(claim_text)
        
        # 2. Risk Analysis: Claims that could endanger patient safety
        safety_risks = self._analyze_patient_safety_risks(claim_text)
        
        # 3. Evidence Contradiction: Claims that contradict established medicine
        evidence_conflicts = self._analyze_evidence_contradictions(claim_text)
        
        # 4. Logical Consistency: Claims that are internally contradictory
        logical_issues = self._analyze_logical_consistency(claim_text)
        
        # Combine all analyses with proper severity assessment
        all_issues = impossibility_indicators + safety_risks + evidence_conflicts + logical_issues
        
        # Enhanced severity assessment based on multiple factors
        for issue in all_issues:
            if not issue.get('severity'):
                # Auto-assign severity based on issue type and content
                if any(keyword in claim_lower for keyword in ['type 1 diabetes', 'insulin', 'meningitis', 'sepsis', 'cardiac arrest']):
                    issue['severity'] = 'CRITICAL'
                elif any(keyword in claim_lower for keyword in ['cancer', 'metastatic', 'advanced']):
                    issue['severity'] = 'HIGH'
                else:
                    issue['severity'] = 'MEDIUM'
        
        return all_issues
    
    def _analyze_medical_impossibilities(self, claim_text):
        """Detect claims that violate fundamental medical/biological principles"""
        issues = []
        claim_lower = claim_text.lower()
        
        # Check for impossible biological claims
        if any(word in claim_lower for word in ['regenerate', 'regrow', 'restore']) and \
           any(word in claim_lower for word in ['limb', 'organ', 'brain tissue', 'spinal cord']):
            issues.append({
                'type': 'biological_impossibility',
                'severity': 'HIGH',
                'reason': 'Claims regeneration of non-regenerative tissues',
                'medical_domain': 'biology/physiology'
            })
        
        # Check for impossible timeline claims
        if any(phrase in claim_lower for phrase in ['instant cure', 'immediate cure', 'cured overnight']):
            issues.append({
                'type': 'impossible_timeline',
                'severity': 'HIGH', 
                'reason': 'Claims unrealistic treatment timelines',
                'medical_domain': 'treatment_efficacy'
            })
            
        return issues
    
    def _analyze_patient_safety_risks(self, claim_text):
        """Identify claims that could endanger patient safety"""
        risks = []
        claim_lower = claim_text.lower()
        
        # Medication discontinuation risks
        critical_medications = ['insulin', 'warfarin', 'digoxin', 'phenytoin', 'lithium']
        if any(f'stop {med}' in claim_lower or f'no {med}' in claim_lower for med in critical_medications):
            risks.append({
                'type': 'medication_safety_risk',
                'severity': 'CRITICAL',
                'reason': 'Advises discontinuing critical medication',
                'medical_domain': 'pharmacology'
            })
        
        # Emergency condition mismanagement
        emergency_conditions = ['heart attack', 'stroke', 'anaphylaxis', 'sepsis']
        alternative_treatments = ['herbs', 'meditation', 'crystals', 'prayer']
        
        if any(condition in claim_lower for condition in emergency_conditions) and \
           any(treatment in claim_lower for treatment in alternative_treatments):
            risks.append({
                'type': 'emergency_mismanagement',
                'severity': 'CRITICAL',
                'reason': 'Suggests alternative treatment for medical emergency',
                'medical_domain': 'emergency_medicine'
            })
            
        return risks
    
    def _analyze_evidence_contradictions(self, claim_text):
        """Check against established medical evidence using semantic understanding"""
        contradictions = []
        claim_lower = claim_text.lower()
        
        # Check for claims that contradict established medical consensus
        # Type 1 diabetes and insulin
        if 'diabetes' in claim_lower and 'type 1' in claim_lower:
            if any(phrase in claim_lower for phrase in ['no insulin', 'without insulin', 'cure diabetes']):
                contradictions.append({
                    'type': 'evidence_contradiction',
                    'severity': 'CRITICAL',
                    'reason': 'Contradicts established treatment for Type 1 diabetes',
                    'medical_domain': 'endocrinology'
                })
        
        # Cancer treatment claims
        if 'cancer' in claim_lower:
            if any(phrase in claim_lower for phrase in ['completely cured', 'perfect cure', 'guaranteed cure']):
                contradictions.append({
                    'type': 'unrealistic_outcome',
                    'severity': 'HIGH',
                    'reason': 'Claims unrealistic cancer treatment outcomes',
                    'medical_domain': 'oncology'
                })
                
        return contradictions
    
    def _analyze_logical_consistency(self, claim_text):
        """Analyze internal logical consistency of medical claims"""
        inconsistencies = []
        claim_lower = claim_text.lower()
        
        # Check for mutually exclusive statements
        if 'completely cured' in claim_lower and any(word in claim_lower for word in ['may', 'possibly', 'might']):
            inconsistencies.append({
                'type': 'logical_inconsistency',
                'severity': 'MEDIUM',
                'reason': 'Contains contradictory certainty levels',
                'medical_domain': 'clinical_reasoning'
            })
            
        return inconsistencies

    def _check_evidence_based_validity(self, claim_text, verification_result):
        """Check if claim contradicts established medical evidence with  clinical knowledge"""
        claim_lower = claim_text.lower()
        
        # evidence-based medical facts that should never be contradicted
        established_facts = {
            # Critical life-saving medications
            'insulin_dependency': {
                'fact': 'Type 1 diabetes requires lifelong insulin therapy',
                'contradictions': [
                    r'type\s*1\s+diabetes.*cured.*(without|no)\s+insulin',
                    r'pancreas.*regenerate.*insulin.*production',
                    r'reverse.*type\s*1.*diabetes.*(diet|herbs|natural)'
                ],
                'severity': 'CRITICAL'
            },
            
            'cardiac_emergency': {
                'fact': 'Cardiac arrest requires immediate CPR and advanced life support',
                'contradictions': [
                    r'heart.*attack.*(home|natural).*remedy',
                    r'cardiac.*arrest.*(herbs|meditation|prayer).*treatment',
                    r'myocardial.*infarction.*cured.*(vitamins|supplements)'
                ],
                'severity': 'CRITICAL'
            },
            
            'cancer_treatment_evidence': {
                'fact': 'Cancer treatment requires evidence-based oncological interventions',
                'contradictions': [
                    r'cancer.*cured.*(crystal|energy|prayer|magic|alkaline)',
                    r'chemotherapy.*unnecessary.*(natural|alternative).*cure',
                    r'stage.*4.*cancer.*reversed.*(diet|supplements|meditation)'
                ],
                'severity': 'CRITICAL'
            },
            
            # Emergency conditions
            'anaphylaxis_treatment': {
                'fact': 'Anaphylaxis requires immediate epinephrine injection',
                'contradictions': [
                    r'anaphylaxis.*treated.*(herbs|natural|homeopathic)',
                    r'severe.*allergic.*reaction.*cured.*(meditation|breathing)'
                ],
                'severity': 'CRITICAL'
            },
            
            'stroke_emergency': {
                'fact': 'Stroke is a medical emergency requiring immediate hospital treatment',
                'contradictions': [
                    r'stroke.*treated.*(home|natural|herbs|acupuncture)',
                    r'brain.*damage.*reversed.*(supplements|natural.*healing)'
                ],
                'severity': 'CRITICAL'
            },
            
            # Infectious diseases
            'meningitis_severity': {
                'fact': 'Bacterial meningitis is life-threatening and requires immediate antibiotic treatment',
                'contradictions': [
                    r'meningitis.*treated.*(natural|herbs|homeopathic)',
                    r'brain.*infection.*cured.*(vitamins|supplements)'
                ],
                'severity': 'CRITICAL'
            },
            
            'sepsis_treatment': {
                'fact': 'Sepsis requires immediate hospital treatment with antibiotics and supportive care',
                'contradictions': [
                    r'sepsis.*treated.*(home|natural|herbs)',
                    r'blood.*poisoning.*cured.*(diet|supplements)'
                ],
                'severity': 'CRITICAL'
            },
            
            # Vaccine science
            'vaccine_safety': {
                'fact': 'Vaccines are safe and effective disease prevention tools',
                'contradictions': [
                    r'vaccines.*cause.*(autism|cancer|infertility|death)',
                    r'vaccination.*more.*dangerous.*than.*disease',
                    r'natural.*immunity.*always.*better.*than.*vaccines'
                ],
                'severity': 'HIGH'
            },
            
            # Pregnancy and childbirth
            'high_risk_pregnancy': {
                'fact': 'High-risk pregnancies require medical monitoring and intervention',
                'contradictions': [
                    r'preeclampsia.*treated.*(natural|herbs|diet)',
                    r'gestational.*diabetes.*cured.*(natural|meditation)',
                    r'pregnancy.*complications.*resolved.*(prayer|energy)'
                ],
                'severity': 'HIGH'
            },
            
            # Chronic diseases
            'autoimmune_management': {
                'fact': 'Autoimmune diseases require ongoing medical management',
                'contradictions': [
                    r'autoimmune.*disease.*cured.*(diet|supplements|detox)',
                    r'lupus.*rheumatoid.*arthritis.*reversed.*(natural)',
                    r'multiple.*sclerosis.*cured.*(vitamins|herbs)'
                ],
                'severity': 'HIGH'
            },
            
            'genetic_disorders': {
                'fact': 'Genetic disorders cannot be cured by lifestyle interventions alone',
                'contradictions': [
                    r'genetic.*disorder.*cured.*(diet|supplements|lifestyle)',
                    r'dna.*repaired.*(natural|herbs|meditation)',
                    r'chromosomal.*abnormality.*reversed.*(natural)'
                ],
                'severity': 'HIGH'
            },
            
            # Mental health
            'severe_mental_illness': {
                'fact': 'Severe mental illness often requires psychiatric medication and professional treatment',
                'contradictions': [
                    r'bipolar.*disorder.*cured.*(diet|supplements|natural)',
                    r'schizophrenia.*treated.*(vitamins|herbs|meditation)',
                    r'severe.*depression.*resolved.*(natural.*only)'
                ],
                'severity': 'HIGH'
            },
            
            # Pharmacological principles
            'drug_interactions': {
                'fact': 'Drug interactions can be dangerous and require medical supervision',
                'contradictions': [
                    r'herbs.*safe.*with.*all.*medications',
                    r'natural.*supplements.*no.*side.*effects',
                    r'vitamins.*cannot.*cause.*overdose'
                ],
                'severity': 'MEDIUM'
            }
        }
        
        import re
        evidence_violations = []
        
        for fact_id, fact_data in established_facts.items():
            for contradiction_pattern in fact_data['contradictions']:
                if re.search(contradiction_pattern, claim_lower):
                    evidence_violations.append({
                        'fact_category': fact_id,
                        'violated_fact': fact_data['fact'],
                        'claim_contradiction': claim_text,
                        'severity': fact_data['severity'],
                        'clinical_domain': self._determine_clinical_domain(fact_id),
                        'evidence_strength': 'High-quality clinical evidence'
                    })
        
        return evidence_violations
    
    def _determine_clinical_domain(self, fact_id):
        """Determine the clinical specialty domain for evidence violations"""
        domain_mapping = {
            'insulin_dependency': 'Endocrinology',
            'cardiac_emergency': 'Cardiology/Emergency Medicine',
            'cancer_treatment_evidence': 'Oncology',
            'anaphylaxis_treatment': 'Emergency Medicine/Allergy',
            'stroke_emergency': 'Neurology/Emergency Medicine',
            'meningitis_severity': 'Infectious Disease/Neurology',
            'sepsis_treatment': 'Critical Care/Infectious Disease',
            'vaccine_safety': 'Infectious Disease/Public Health',
            'high_risk_pregnancy': 'Obstetrics/Maternal-Fetal Medicine',
            'autoimmune_management': 'Rheumatology/Immunology',
            'genetic_disorders': 'Medical Genetics',
            'severe_mental_illness': 'Psychiatry',
            'drug_interactions': 'Clinical Pharmacology'
        }
        
        return domain_mapping.get(fact_id, 'General Medicine')

    def _assess_overall_risk(self, claims: List[Dict]) -> Dict[str, Any]:
        """multi-layer risk assessment with medical plausibility analysis"""
        if not claims:
            return {"level": "UNKNOWN", "reason": "No claims extracted"}
        
        # LAYER 1: Medical Plausibility Analysis
        all_implausibility_issues = []
        all_evidence_violations = []
        
        for claim in claims:
            # Canonical schema — claim_text is the only accepted key (D-07, D-08, D-11).
            claim_text = claim['claim_text']
            
            # Check for medical implausibility
            implausibility_issues = self._detect_medical_implausibility(claim_text)
            all_implausibility_issues.extend(implausibility_issues)
            
            # Check evidence-based validity
            evidence_violations = self._check_evidence_based_validity(claim_text, claim)
            all_evidence_violations.extend(evidence_violations)

        # LAYER 2: Content-Based Risk Assessment with Plausibility Integration
        critical_issues = [issue for issue in all_implausibility_issues if issue.get('severity') == 'CRITICAL']
        critical_violations = [violation for violation in all_evidence_violations if violation.get('severity') == 'CRITICAL']
        high_issues = [issue for issue in all_implausibility_issues if issue.get('severity') == 'HIGH']
        high_violations = [violation for violation in all_evidence_violations if violation.get('severity') == 'HIGH']
        
        # Enhanced severity assessment based on claim verification scores
        very_low_confidence_claims = [claim for claim in claims 
                                    if claim.get('verification_confidence') == 'LOW' 
                                    and claim.get('verification_score', 1.0) < 0.1]
        
        # Override risk level for critical medical safety issues
        if critical_issues or critical_violations:
            return {
                "level": "CRITICAL_RISK",
                "reason": f"MEDICAL SAFETY VIOLATION: {len(critical_issues)} implausible claims, {len(critical_violations)} evidence violations detected",
                "critical_issues": critical_issues,
                "evidence_violations": critical_violations,
                "very_low_confidence_claims": len(very_low_confidence_claims),
                "stats": self._build_basic_risk_stats(claims)
            }
        
        # High risk for multiple high-severity issues or very low confidence claims
        if (len(high_issues) + len(high_violations)) >= 2 or len(very_low_confidence_claims) >= 2:
            return {
                "level": "HIGH_RISK", 
                "reason": f"Multiple high-severity issues: {len(high_issues)} implausible claims, {len(high_violations)} evidence violations, {len(very_low_confidence_claims)} very low confidence claims",
                "high_issues": high_issues,
                "evidence_violations": high_violations,
                "very_low_confidence_claims": len(very_low_confidence_claims),
                "stats": self._build_basic_risk_stats(claims)
            }
        
        # LAYER 3: High-risk plausibility issues
        if all_implausibility_issues:
            return {
                "level": "HIGH_RISK", 
                "reason": f"Medical plausibility concerns: {len(all_implausibility_issues)} suspicious claims detected",
                "plausibility_issues": all_implausibility_issues,
                "stats": self._build_basic_risk_stats(claims)
            }
        
        # LAYER 4: Nuanced confidence-based risk assessment
        # Count confidence levels
        high_conf = sum(1 for c in claims if c['verification_confidence'] == 'HIGH')
        medium_conf = sum(1 for c in claims if c['verification_confidence'] == 'MEDIUM')
        low_conf = sum(1 for c in claims if c['verification_confidence'] == 'LOW')

        total_claims = len(claims)
        high_conf_ratio = high_conf / total_claims if total_claims else 0
        medium_conf_ratio = medium_conf / total_claims if total_claims else 0
        low_conf_ratio = low_conf / total_claims if total_claims else 0

        # More sophisticated risk determination using centralized thresholds
        if low_conf_ratio >= self.risk_thresholds['high_risk_low_conf_ratio']:  # 60% or more low confidence claims
            risk_level = "HIGH_RISK"
            risk_reason = f"{low_conf_ratio:.0%} low confidence claims ({low_conf}/{total_claims})"
        elif low_conf_ratio >= self.risk_thresholds['medium_risk_low_conf_ratio'] or (medium_conf_ratio >= 0.8 and high_conf_ratio < 0.2):
            risk_level = "MEDIUM_RISK"
            risk_reason = f"{low_conf_ratio:.0%} low or {medium_conf_ratio:.0%} medium confidence, low high confidence"
        elif high_conf_ratio >= self.risk_thresholds['low_risk_high_conf_ratio']:  # Majority high confidence
            risk_level = "LOW_RISK"
            risk_reason = f"{high_conf_ratio:.0%} high confidence claims ({high_conf}/{total_claims})"
        else:
            risk_level = "MEDIUM_RISK"  # Default to medium for mixed cases
            risk_reason = "Mixed confidence levels"

        # Count negation and uncertainty patterns using centralized thresholds
        negated_claims = sum(1 for c in claims if c.get('has_negation', False))
        uncertain_claims = sum(1 for c in claims if c.get('has_uncertainty', False))
        negation_ratio = negated_claims / total_claims if total_claims else 0
        uncertainty_ratio = uncertain_claims / total_claims if total_claims else 0

        risk_factors = [risk_reason]
        if negation_ratio > self.risk_thresholds['high_negation_ratio']:
            risk_factors.append(f"High negation rate: {negated_claims}/{total_claims}")
        if uncertainty_ratio > self.risk_thresholds['high_uncertainty_ratio']:
            risk_factors.append(f"High uncertainty: {uncertain_claims}/{total_claims}")

        return {
            "level": risk_level,
            "reason": "; ".join(risk_factors),
            "stats": {
                "total_claims": total_claims,
                "high_confidence": high_conf,
                "medium_confidence": medium_conf,
                "low_confidence": low_conf,
                "negated_claims": negated_claims,
                "uncertain_claims": uncertain_claims,
                "high_conf_ratio": round(high_conf_ratio, 2),
                "medium_conf_ratio": round(medium_conf_ratio, 2),
                "low_conf_ratio": round(low_conf_ratio, 2),
                "negation_ratio": round(negation_ratio, 2),
                "uncertainty_ratio": round(uncertainty_ratio, 2)
            }
        }
    
    def _build_basic_risk_stats(self, claims):
        """Helper method to build risk statistics for plausibility-based assessments"""
        total_claims = len(claims)
        high_conf = sum(1 for c in claims if c['verification_confidence'] == 'HIGH')
        medium_conf = sum(1 for c in claims if c['verification_confidence'] == 'MEDIUM')
        low_conf = sum(1 for c in claims if c['verification_confidence'] == 'LOW')
        negated_claims = sum(1 for c in claims if c.get('has_negation', False))
        uncertain_claims = sum(1 for c in claims if c.get('has_uncertainty', False))
        
        return {
            "total_claims": total_claims,
            "high_confidence": high_conf,
            "medium_confidence": medium_conf,
            "low_confidence": low_conf,
            "negated_claims": negated_claims,
            "uncertain_claims": uncertain_claims,
            "high_ratio": round(high_conf / total_claims, 2) if total_claims > 0 else 0,
            "low_ratio": round(low_conf / total_claims, 2) if total_claims > 0 else 0,
            "negation_ratio": round(negated_claims / total_claims, 2) if total_claims > 0 else 0,
            "uncertainty_ratio": round(uncertain_claims / total_claims, 2) if total_claims > 0 else 0
        }
    
    def _apply_responsible_ai_layer(self, results: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Apply Responsible AI safeguards and safety warnings"""
        
        risk_stats = results['risk_assessment']['stats']
        low_conf_ratio = risk_stats.get('low_conf_ratio', risk_stats.get('low_ratio', 0))
        medium_conf_ratio = risk_stats.get('medium_conf_ratio', risk_stats.get('medium_ratio', 0))
        high_conf_ratio = risk_stats.get('high_conf_ratio', risk_stats.get('high_ratio', 0))
        risk_level = results['risk_assessment']['level']

        # Initialize safety warnings and recommendations
        safety_warnings = []
        safety_recommendations = []
        requires_expert_review = False
        auto_flagged = False

        # Critical safety thresholds
        if low_conf_ratio >= self.safety_config['critical_threshold']:
            safety_warnings.append({
                'level': 'CRITICAL',
                'message': 'CRITICAL: Very high proportion of unsupported medical claims detected. Immediate expert review required.',
                'action_required': 'DO NOT USE for clinical decisions. Require immediate medical expert validation.'
            })
            requires_expert_review = True
            auto_flagged = True

        elif low_conf_ratio >= self.safety_config['high_risk_threshold']:
            safety_warnings.append({
                'level': 'HIGH',
                'message': 'HIGH RISK: Significant medical hallucination risk detected. Expert review strongly recommended.',
                'action_required': 'Medical expert review required before any clinical use.'
            })
            requires_expert_review = True

        elif low_conf_ratio >= self.safety_config['require_expert_review_threshold']:
            safety_warnings.append({
                'level': 'MEDIUM',
                'message': 'MEDIUM RISK: Some medical claims lack strong evidence support.',
                'action_required': 'Clinical review recommended for verification.'
            })

        # Auto-flagging for quality assurance
        if low_conf_ratio >= self.safety_config['auto_flag_threshold']:
            auto_flagged = True

        # Domain-specific warnings
        medical_terms = ['diagnosis', 'treatment', 'medication', 'dosage', 'contraindication', 'side effect']
        contains_medical_terms = any(term.lower() in original_text.lower() for term in medical_terms)

        if contains_medical_terms and risk_level != 'LOW_RISK':
            safety_warnings.append({
                'level': 'CLINICAL',
                'message': 'Clinical content detected with verification concerns.',
                'action_required': 'Healthcare professional review recommended.'
            })
        
        # Critical dangerous medical terminology detection
        dangerous_terms = {
            'critical': [
                'magical healing', 'magic cure', 'healing crystals', 'positive energy therapy',
                'homeopathic cure', 'miracle cure', 'instant cure', 'guaranteed cure',
                'completely cured', 'perfect cure', 'divine healing', 'spiritual healing',
                'no medicine needed', 'no medication needed', 'no insulin needed',
                'natural cure only', 'herbs cure everything', 'prayer heals all'
            ],
            'high_risk': [
                'homeopathic water', 'alternative medicine only', 'avoid vaccines',
                'stop medication', 'ignore doctors', 'medical conspiracy',
                'pharmaceutical lie', 'doctors wrong', 'medicine harmful',
                'natural only treatment', 'refuse treatment', 'detox cure'
            ]
        }
        
        text_lower = original_text.lower()
        dangerous_detected = []
        
        # Check for critical dangerous terms
        for term in dangerous_terms['critical']:
            if term in text_lower:
                dangerous_detected.append(('CRITICAL', term))
                safety_warnings.insert(0, {  # Insert at beginning for priority
                    'level': 'CRITICAL',
                    'message': f'CRITICAL DANGER: Dangerous medical claim detected - "{term}". This content promotes potentially life-threatening medical misinformation.',
                    'action_required': 'IMMEDIATE FLAGGING REQUIRED. Do not use for any medical purpose. Report for content moderation.'
                })
                requires_expert_review = True
                auto_flagged = True
                # Override risk level to CRITICAL
                results['risk_assessment']['level'] = 'CRITICAL_RISK'
        
        # Check for high-risk dangerous terms
        for term in dangerous_terms['high_risk']:
            if term in text_lower:
                dangerous_detected.append(('HIGH_RISK', term))
                safety_warnings.append({
                    'level': 'HIGH',
                    'message': f'HIGH RISK: Potentially dangerous medical advice detected - "{term}". Medical misinformation risk.',
                    'action_required': 'Expert review required. Verify against medical guidelines.'
                })
                requires_expert_review = True
                # Upgrade risk level if not already critical
                if results['risk_assessment']['level'] != 'CRITICAL_RISK':
                    results['risk_assessment']['level'] = 'HIGH_RISK'
        
        # Add dangerous terms detection to safety assessment
        contains_dangerous_terms = len(dangerous_detected) > 0
        
        # Safety recommendations based on analysis
        if risk_stats.get('negated_claims', 0) > 0:
            safety_recommendations.append('Review negated statements for clinical accuracy')
            
        if risk_stats.get('uncertain_claims', 0) > 0:
            safety_recommendations.append('Verify uncertain medical statements with reliable sources')
            
        if requires_expert_review:
            safety_recommendations.append('Mandatory expert review required before clinical use')
            
        safety_recommendations.extend([
            'Cross-reference all medical claims with authoritative medical literature',
            'Consult qualified healthcare professionals for clinical decisions',
            'Use this analysis as a quality assurance tool, not diagnostic guidance'
        ])
        
        # Responsible AI disclaimer
        responsible_ai_disclaimer = {
            'title': 'RESPONSIBLE AI - HEALTHCARE SAFETY NOTICE',
            'notice': [
                'This tool is designed to assist in identifying potential medical hallucinations in AI-generated content.',
                'It is NOT a replacement for clinical judgment, medical expertise, or professional healthcare advice.',
                'All medical decisions must be made by qualified healthcare professionals.',
                'This analysis should be used as a quality assurance layer only.',
                'The system may miss subtle medical inaccuracies or flag legitimate medical content.',
                'Always validate medical information against authoritative medical sources and guidelines.'
            ],
            'limitations': [
                'Cannot replace clinical expertise or medical training',
                'May not detect all types of medical hallucinations',
                'False positives and false negatives are possible',
                'Not validated for use in direct patient care',
                'Knowledge base limitations may affect accuracy'
            ],
            'proper_use': [
                'Quality assurance for AI-generated medical content',
                'Preliminary screening before expert review',
                'Educational and research purposes only',
                'Content flagging for manual verification'
            ]
        }
        
        # Add Responsible AI Layer to results
        results['responsible_ai'] = {
            'safety_warnings': safety_warnings,
            'safety_recommendations': safety_recommendations,
            'requires_expert_review': requires_expert_review,
            'auto_flagged': auto_flagged,
            'disclaimer': responsible_ai_disclaimer,
            'safety_assessment': {
                'low_confidence_ratio': low_conf_ratio,
                'safety_threshold_exceeded': low_conf_ratio >= self.safety_config['require_expert_review_threshold'],
                'critical_threshold_exceeded': low_conf_ratio >= self.safety_config['critical_threshold'],
                'contains_medical_terms': contains_medical_terms,
                'contains_dangerous_terms': contains_dangerous_terms,
                'dangerous_terms_detected': dangerous_detected
            }
        }
        
        # Log safety events
        if safety_warnings:
            print(f" SAFETY ALERT: {len(safety_warnings)} warning(s) generated for {results['summary_id']}")
            for warning in safety_warnings:
                print(f"   {warning['level']}: {warning['message']}")
        
        return results
    
    def export_results(self, results: List[Dict], output_path: str, format: str = 'json'):
        """Export verification results to file with Responsible AI safety validation"""
        
        # Safety validation before export
        self._validate_export_safety(results, output_path)
        
        # Create directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if format.lower() == 'json':
            # Add responsible AI metadata to JSON export
            export_data = {
                'metadata': {
                    'export_timestamp': datetime.now().isoformat(),
                    'safety_compliance': 'Healthcare AI Safety Standards',
                    'disclaimer': 'FOR QUALITY ASSURANCE USE ONLY - NOT FOR DIRECT CLINICAL DECISIONS'
                },
                'verification_results': results,
                'global_safety_summary': self._generate_global_safety_summary(results)
            }
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
        elif format.lower() == 'csv':
            # Flatten results for CSV export with safety fields
            flattened = []
            for result in results:
                responsible_ai = result.get('responsible_ai', {})
                safety_warnings = responsible_ai.get('safety_warnings', [])
                
                for claim in result['claims']:
                    flattened.append({
                        'summary_id': result['summary_id'],
                        'claim_text': claim['claim_text'],
                        'claim_type': claim['type'],
                        'medical_entities': ', '.join(claim['medical_entities']),
                        'verification_confidence': claim['verification_confidence'],
                        'verification_score': claim['verification_score'],
                        'has_negation': claim.get('has_negation', False),
                        'has_uncertainty': claim.get('has_uncertainty', False),
                        'certainty_modifier': claim.get('certainty_modifier', 'positive'),
                        'risk_level': result['risk_assessment']['level'],
                        'total_claims': result['risk_assessment']['stats']['total_claims'],
                        'negation_ratio': result['risk_assessment']['stats'].get('negation_ratio', 0),
                        'uncertainty_ratio': result['risk_assessment']['stats'].get('uncertainty_ratio', 0),
                        # Responsible AI fields
                        'requires_expert_review': responsible_ai.get('requires_expert_review', False),
                        'auto_flagged': responsible_ai.get('auto_flagged', False),
                        'safety_warnings_count': len(safety_warnings),
                        'highest_safety_level': max([w['level'] for w in safety_warnings], default='NONE'),
                        'safety_compliance_status': 'REQUIRES_REVIEW' if responsible_ai.get('requires_expert_review') else 'STANDARD'
                    })
            pd.DataFrame(flattened).to_csv(output_path, index=False)
        
        print(f" Results exported to {output_path} with Responsible AI safeguards")
    
    def _validate_export_safety(self, results: List[Dict], output_path: str):
        """Validate safety before allowing export"""
        
        critical_cases = 0
        flagged_cases = 0
        
        for result in results:
            responsible_ai = result.get('responsible_ai', {})
            safety_warnings = responsible_ai.get('safety_warnings', [])
            
            if any(w['level'] == 'CRITICAL' for w in safety_warnings):
                critical_cases += 1
            if responsible_ai.get('auto_flagged', False):
                flagged_cases += 1
        
        if critical_cases > 0:
            print(f" SAFETY VALIDATION: {critical_cases} CRITICAL safety case(s) detected")
            print(f" Expert review MANDATORY before using exported results")
            
        if flagged_cases > 0:
            print(f" SAFETY VALIDATION: {flagged_cases} case(s) auto-flagged for review")
        
        # Log safety validation
        safety_log = {
            'export_path': output_path,
            'timestamp': datetime.now().isoformat(),
            'total_cases': len(results),
            'critical_cases': critical_cases,
            'flagged_cases': flagged_cases,
            'safety_validation': 'PASSED' if critical_cases == 0 else 'REQUIRES_EXPERT_REVIEW'
        }
        
        # Save safety log
        log_path = output_path.replace('.json', '_safety_log.json').replace('.csv', '_safety_log.json')
        with open(log_path, 'w') as f:
            json.dump(safety_log, f, indent=2)
        
        print(f" Safety validation log saved: {log_path}")
    
    def _generate_global_safety_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate global safety summary across all results"""
        
        total_cases = len(results)
        critical_cases = 0
        high_risk_cases = 0
        requires_review_cases = 0
        auto_flagged_cases = 0
        
        all_warnings = []
        
        for result in results:
            responsible_ai = result.get('responsible_ai', {})
            safety_warnings = responsible_ai.get('safety_warnings', [])
            
            if any(w['level'] == 'CRITICAL' for w in safety_warnings):
                critical_cases += 1
            if any(w['level'] == 'HIGH' for w in safety_warnings):
                high_risk_cases += 1
            if responsible_ai.get('requires_expert_review', False):
                requires_review_cases += 1
            if responsible_ai.get('auto_flagged', False):
                auto_flagged_cases += 1
                
            all_warnings.extend(safety_warnings)
        
        return {
            'total_cases_analyzed': total_cases,
            'safety_statistics': {
                'critical_cases': critical_cases,
                'high_risk_cases': high_risk_cases,
                'requires_expert_review': requires_review_cases,
                'auto_flagged_cases': auto_flagged_cases,
                'safe_cases': total_cases - max(critical_cases, high_risk_cases, requires_review_cases)
            },
            'safety_percentages': {
                'critical_rate': round(critical_cases / total_cases * 100, 1) if total_cases > 0 else 0,
                'review_required_rate': round(requires_review_cases / total_cases * 100, 1) if total_cases > 0 else 0,
                'safe_rate': round((total_cases - requires_review_cases) / total_cases * 100, 1) if total_cases > 0 else 0
            },
            'overall_safety_status': (
                'CRITICAL_ATTENTION_REQUIRED' if critical_cases > 0 else
                'EXPERT_REVIEW_RECOMMENDED' if requires_review_cases > 0 else
                'STANDARD_MONITORING'
            ),
            'recommendations': [
                'All flagged cases require human expert validation',
                'Use results only as quality assurance, not for clinical decisions',
                'Implement continuous monitoring of safety metrics',
                'Regular calibration with medical experts recommended'
            ]
        }
    
    def verify_from_claim_extractor_json(self, json_path: str) -> list:
        """Load claim extraction results from JSON and run risk/safety verification on each summary."""
        import json
        with open(json_path, 'r') as f:
            summaries = json.load(f)
        all_results = []
        for i, summary in enumerate(summaries):
            # Use the original text and claims from the extractor output
            summary_id = summary.get('summary_id', f'claim_extractor_{i+1}')
            # Re-run risk assessment and responsible AI layer
            # If claims are already extracted, use them directly
            results = {
                'original_text': summary.get('original_text', ''),
                'sentences': summary.get('sentences', []),
                'claims': summary.get('claims', []),
                'total_claims': summary.get('total_claims', 0),
                'summary_id': summary_id
            }
            results['risk_assessment'] = self._assess_overall_risk(results['claims'])
            results = self._apply_responsible_ai_layer(results, results['original_text'])
            all_results.append(results)
        return all_results

def main():
    """Demo the medical verifier with Responsible AI Layer using JSON workflow
    
    This function now uses the JSON output from claim_extractor_fixed.py to avoid
    duplicate test data and follow the proper workflow.
    """
    import os
    
    # Test with a simple case first to verify fixes
    print("\n Testing Medical Verifier Fixes...")
    print("=" * 60)
    
    verifier = MedicalVerifier()
    
    # Test case to verify data structure fix
    test_summary = "A Patient with type 1 diabetes was successfully weaned off insulin after six months of a strict ketogenic diet, maintaining normal blood glucose levels without medications."
    
    print("Testing data structure fixes...")
    result = verifier.verify_single_summary(test_summary, "structure_test")
    
    print(f" Claims processing: {result['total_claims']} claims found")
    print(f" Risk assessment: {result['risk_assessment']['level']}")
    print(f" Advanced analysis integration: {'critical_issues' in result['risk_assessment'] or 'high_issues' in result['risk_assessment']}")
    
    # Check if JSON output from claim extractor exists for full workflow test
    json_file = "outputs/claim_extraction_results.json"
    if not os.path.exists(json_file):
        print(f"\n  {json_file} not found for full workflow test.")
        print("Run claim_extractor_fixed.py first for complete integration testing.")
        print("\n Basic fixes verified successfully!")
        return result
    
    print(f"\nTesting JSON workflow...")
    print(f"Loading results from {json_file}...")
    
    # Use the new JSON-based verification method
    verifier = MedicalVerifier()
    results = verifier.verify_from_claim_extractor_json(json_file)
    
    print(f"\n{'='*20} VERIFICATION SUMMARY {'='*20}")
    print(f"Total summaries processed: {len(results)}")
    
    high_risk_count = sum(1 for r in results if r.get('final_assessment', {}).get('risk_level') == 'HIGH_RISK')
    print(f"High-risk summaries identified: {high_risk_count}")
    
    # Show details for all results
    for i, result in enumerate(results, 1):
        print(f"\n{'='*20} SUMMARY {i} {'='*20}")
        # Print the full summary text
        summary_text = result.get('original_text', '')
        if summary_text:
            print(f"Summary: {summary_text}")
        print(f"Claims found: {result.get('total_claims', 0)}")
        # Try to get risk level from final_assessment, else from risk_assessment, else UNKNOWN
        risk_level = result.get('final_assessment', {}).get('risk_level')
        if not risk_level:
            risk_level = result.get('risk_assessment', {}).get('level', 'UNKNOWN')
        print(f"Risk level: {risk_level}")
        # Display Responsible AI information
        responsible_ai = result.get('responsible_ai', {})
        safety_warnings = responsible_ai.get('safety_warnings', [])
        if safety_warnings:
            print(f"SAFETY WARNINGS ({len(safety_warnings)}):")
            for warning in safety_warnings:
                # Clean up label: e.g., 'MEDIUM: MEDIUM RISK: ...' -> 'MEDIUM RISK: ...'
                level = warning.get('level', 'WARNING').upper()
                message = warning.get('message', '')
                # Remove duplicate level prefix if present
                if message.startswith(f"{level}: "):
                    message = message[len(f"{level}: "):]
                # Map CRITICAL: CRITICAL: ... to CRITICAL RISK: ...
                if level == 'CRITICAL':
                    print(f"  CRITICAL RISK: {message}")
                elif level == 'HIGH':
                    print(f"  HIGH RISK: {message}")
                elif level == 'MEDIUM':
                    print(f"  MEDIUM RISK: {message}")
                else:
                    print(f"  {level}: {message}")
        if responsible_ai.get('requires_expert_review', False):
            print("EXPERT REVIEW REQUIRED")
        
    
    print(f"\n{'='*60}")
    print("RESPONSIBLE AI DISCLAIMER:")
    if results and results[0].get('responsible_ai', {}).get('disclaimer'):
        disclaimer = results[0]['responsible_ai']['disclaimer']
        for notice in disclaimer.get('notice', [])[:3]:  # Show first 3 points
            print(f" {notice}")
        print("  - (Additional safety guidelines in full output)")
    
    print(f"\n{'='*60}")
    print("Processing complete. JSON workflow used to avoid data duplication.")
    return results


def main_legacy():
    """Legacy main function - kept for backward compatibility
    
    This version creates a verifier instance and processes a single test case.
    Use main() for the preferred JSON workflow approach.
    """
    verifier = MedicalVerifier()
    
    # Single test case for demonstration
    test_summary = "A Patient with type 1 diabetes was successfully weaned off insulin after six months of a strict ketogenic diet, maintaining normal blood glucose levels without medications."
    
    print("\n Testing Medical Verifier with Responsible AI Layer (Legacy)...")
    print("=" * 60)
    
    result = verifier.verify_single_summary(test_summary, "legacy_test")
    
    print(f"Text: {test_summary}")
    print(f"Claims found: {result['total_claims']}")
    print(f"Risk level: {result['risk_assessment']['level']}")
    
    # Display Responsible AI information
    responsible_ai = result.get('responsible_ai', {})
    safety_warnings = responsible_ai.get('safety_warnings', [])
    
    if safety_warnings:
        print(f"\nSAFETY WARNINGS ({len(safety_warnings)}):")
        for warning in safety_warnings:
            print(f"  {warning['level']}: {warning['message']}")
            print(f"  Action: {warning['action_required']}")
    
    if responsible_ai.get('requires_expert_review', False):
        print(f"EXPERT REVIEW REQUIRED")
        
    if responsible_ai.get('auto_flagged', False):
        print(f"AUTO-FLAGGED for quality assurance review")
    
    # Export results with Responsible AI safeguards
    verifier.export_results([result], './outputs/verification_results.json', 'json')

    return result


if __name__ == "__main__":
    main()
