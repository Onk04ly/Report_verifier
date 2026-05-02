"""
"""
import hashlib
import json
from datetime import datetime

import pandas as pd
import re
import spacy
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import warnings
warnings.filterwarnings('ignore')

# Advanced embedding imports with fallback handling
try:
    from transformers import AutoTokenizer, AutoModel, pipeline as hf_pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
    print(" Transformers available for PubMedBERT and OpenMed NER")
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print(" Transformers not available - will use TF-IDF fallback")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
    print(" sentence-transformers available for PubMedBERT embeddings")
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print(" sentence-transformers not available - falling back to transformers")

try:
    import faiss
    FAISS_AVAILABLE = True
    print(" Faiss available for efficient similarity search")
except ImportError:
    FAISS_AVAILABLE = False
    print(" Faiss not available - will use slower similarity methods")

class MedicalPreprocessor:
    """Advanced preprocessing for medical knowledge base"""
    
    def __init__(self):
        # Load scispaCy sentence-splitting model (v0.6.2)
        try:
            self.nlp = spacy.load("en_core_sci_scibert")
            print(" Loaded en_core_sci_scibert for sentence splitting (scispaCy v0.6.2)")
        except OSError:
            print(" en_core_sci_scibert not found, using basic preprocessing")
            self.nlp = None

        # Load OpenMed NER pipeline for biomedical entity extraction
        self.ner_pipeline = None
        if TRANSFORMERS_AVAILABLE:
            try:
                self.ner_pipeline = hf_pipeline(
                    "token-classification",
                    model="OpenMed/OpenMed-NER-PharmaDetect-SuperClinical-434M",
                    aggregation_strategy="simple"
                )
                print(" Loaded OpenMed NER (OpenMed-NER-PharmaDetect-SuperClinical-434M)")
            except Exception as e:
                print(f" OpenMed NER failed to load: {e}")
        
        # Initialize embedding models with fallback hierarchy
        self.embedding_models = {}
        self.available_methods = []
        
        self._initialize_embedding_models()
        
        # Medical abbreviation mappings
        self.medical_abbreviations = {
            'mi': 'myocardial infarction',
            'dm': 'diabetes mellitus',
            'htn': 'hypertension',
            'copd': 'chronic obstructive pulmonary disease',
            'ra': 'rheumatoid arthritis',
            'ckd': 'chronic kidney disease',
            'cad': 'coronary artery disease',
            'chf': 'congestive heart failure',
            'icu': 'intensive care unit',
            'er': 'emergency room',
            'iv': 'intravenous',
            'po': 'by mouth',
            'bid': 'twice daily',
            'qid': 'four times daily',
            'prn': 'as needed',
            'mg': 'milligrams',
            'ml': 'milliliters',
            'kg': 'kilograms',
            'bp': 'blood pressure',
            'hr': 'heart rate',
            'rr': 'respiratory rate',
            'temp': 'temperature',
            'pt': 'patient',
            'pts': 'patients',
            'dx': 'diagnosis',
            'tx': 'treatment',
            'rx': 'prescription',
            'sx': 'symptoms',
            'hx': 'history',
            'fx': 'fracture',
            'ca': 'cancer',
            'cva': 'cerebrovascular accident',
            'tia': 'transient ischemic attack',
            'pe': 'pulmonary embolism',
            'dvt': 'deep vein thrombosis',
            'uti': 'urinary tract infection',
            'uri': 'upper respiratory infection',
            'gi': 'gastrointestinal',
            'gu': 'genitourinary',
            'cns': 'central nervous system',
            'pns': 'peripheral nervous system',
            'ekg': 'electrocardiogram',
            'ecg': 'electrocardiogram',
            'ct': 'computed tomography',
            'mri': 'magnetic resonance imaging',
            'xray': 'x-ray radiograph'
        }
    
    def _initialize_embedding_models(self):
        """Initialize embedding models with fallback hierarchy"""
        print("\n INITIALIZING ADVANCED SEMANTIC EMBEDDING MODELS")
        print("=" * 55)

        # Method 1: PubMedBERT Embeddings (Primary — same space as claim extractor)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print(" Loading PubMedBERT Embeddings (Primary Method)...")
                self.embedding_models['pubmedbert_model'] = SentenceTransformer('neuml/pubmedbert-base-embeddings')
                self.available_methods.append('pubmedbert')
                print("  neuml/pubmedbert-base-embeddings successfully loaded")
                print("  Optimized for: PubMed abstracts, biomedical literature")
            except Exception as e:
                print(f"  PubMedBERT failed to load: {e}")

        # Method 2: S-PubMedBert-MS-MARCO (Secondary — retrieval-tuned fallback)
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                print(" Loading S-PubMedBert-MS-MARCO (Secondary Method)...")
                self.embedding_models['spubmedbert_model'] = SentenceTransformer('pritamdeka/S-PubMedBert-MS-MARCO')
                self.available_methods.append('spubmedbert')
                print("  pritamdeka/S-PubMedBert-MS-MARCO successfully loaded")
                print("  Optimized for: Semantic retrieval in biomedical domain")
            except Exception as e:
                print(f"  S-PubMedBert-MS-MARCO failed to load: {e}")

        # Method 3: TF-IDF (Fallback - Always available)
        self.available_methods.append('tfidf')
        print(" TF-IDF (Fallback Method) — always available")
        print("  Optimized for: Term frequency, statistical similarity")

        print(f"\n Available Methods: {' → '.join(self.available_methods)}")
        print(f" Primary Method: {self.available_methods[0] if self.available_methods else 'None'}")
    
    def _get_pubmedbert_embeddings(self, texts, batch_size=32):
        """Generate embeddings using neuml/pubmedbert-base-embeddings (SentenceTransformer)"""
        try:
            model = self.embedding_models['pubmedbert_model']
            print(f" Using PubMedBERT Embeddings for {len(texts)} texts...")
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            print(f" PubMedBERT encoding failed: {e}")
            return None

    def _get_spubmedbert_embeddings(self, texts, batch_size=32):
        """Generate embeddings using pritamdeka/S-PubMedBert-MS-MARCO (SentenceTransformer)"""
        try:
            model = self.embedding_models['spubmedbert_model']
            print(f" Using S-PubMedBert-MS-MARCO for {len(texts)} texts...")
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            return embeddings
        except Exception as e:
            print(f" S-PubMedBert-MS-MARCO encoding failed: {e}")
            return None

    # kept for internal fallback reference only — no longer a public embedding method
    def _get_bioclinical_embeddings_legacy(self, texts, batch_size=16):
        """Legacy BioClinicalBERT embeddings — retained for reference only"""
        try:
            tokenizer = self.embedding_models.get('bioclinical_tokenizer')
            model = self.embedding_models.get('bioclinical_model')
            if tokenizer is None or model is None:
                return None
            print(f" Using BioClinicalBERT (legacy) for {len(texts)} texts...")
            embeddings = []
            model.eval()
            with torch.no_grad():
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    inputs = tokenizer(batch, return_tensors="pt", truncation=True,
                                      padding=True, max_length=512)
                    outputs = model(**inputs)
                    batch_embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
                    embeddings.extend(batch_embeddings)

            return np.array(embeddings)
            
        except Exception as e:
            print(f" BioClinicalBERT encoding failed: {e}")
            return None
    
    def _get_tfidf_embeddings(self, texts):
        """Generate embeddings using TF-IDF (fallback method)"""
        try:
            print(f" Using TF-IDF for {len(texts)} texts...")
            
            vectorizer = TfidfVectorizer(
                max_features=2000,
                stop_words='english',
                ngram_range=(1, 3),
                analyzer='char_wb',
                lowercase=True,
                min_df=2,
                max_df=0.95
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            return tfidf_matrix.toarray()
            
        except Exception as e:
            print(f" TF-IDF encoding failed: {e}")
            return None
    
    def normalize_text(self, text):
        """Normalize medical text"""
        if not isinstance(text, str):
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Expand medical abbreviations
        words = text.split()
        expanded_words = []
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.medical_abbreviations:
                expanded_words.append(self.medical_abbreviations[clean_word])
            else:
                expanded_words.append(word)
        
        text = ' '.join(expanded_words)
        
        # Clean up punctuation while preserving meaning
        text = re.sub(r'[^\w\s\-\.]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def categorize_by_specialty(self, text, original_category):
        """Categorize medical facts by specialty area"""
        text_lower = text.lower()
        
        specialty_patterns = {
            'cardiology': ['heart', 'cardiac', 'cardiovascular', 'coronary', 'artery', 'myocardial', 'hypertension', 'blood pressure'],
            'endocrinology': ['diabetes', 'insulin', 'thyroid', 'hormone', 'endocrine', 'metabolic', 'glucose'],
            'oncology': ['cancer', 'tumor', 'malignant', 'chemotherapy', 'radiation', 'oncology', 'metastasis'],
            'neurology': ['brain', 'neural', 'neurological', 'alzheimer', 'parkinson', 'stroke', 'seizure', 'epilepsy'],
            'respiratory': ['lung', 'pulmonary', 'respiratory', 'asthma', 'copd', 'pneumonia', 'breathing'],
            'gastroenterology': ['gastro', 'liver', 'stomach', 'intestinal', 'digestive', 'hepatic'],
            'rheumatology': ['arthritis', 'joint', 'rheumatoid', 'lupus', 'inflammatory'],
            'infectious_disease': ['infection', 'bacterial', 'viral', 'antibiotic', 'vaccine', 'sepsis'],
            'psychiatry': ['depression', 'anxiety', 'mental', 'psychiatric', 'bipolar', 'schizophrenia'],
            'emergency': ['emergency', 'trauma', 'acute', 'critical', 'resuscitation']
        }
        
        for specialty, keywords in specialty_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return specialty
        
        # Fallback to original category processing
        if isinstance(original_category, str):
            return original_category.replace('_', ' ').lower()
        
        return 'general_medicine'
    
    def extract_medical_entities(self, text):
        """Extract and normalize medical entities using OpenMed NER pipeline"""
        entities = []

        if self.ner_pipeline:
            try:
                results = self.ner_pipeline(text)
                for ent in results:
                    normalized_ent = self.normalize_text(ent['word'])
                    if len(normalized_ent) > 2:
                        entities.append({
                            'text': normalized_ent,
                            'label': ent.get('entity_group', 'ENTITY'),
                            'start': ent.get('start', 0),
                            'end': ent.get('end', 0)
                        })
            except Exception as e:
                print(f" OpenMed NER extraction failed: {e}")
        elif self.nlp:
            # Fallback: scispaCy sentence model has basic NER
            doc = self.nlp(text)
            for ent in doc.ents:
                normalized_ent = self.normalize_text(ent.text)
                if len(normalized_ent) > 2:
                    entities.append({
                        'text': normalized_ent,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char
                    })

        return entities
    
    def calculate_quality_score(self, text, entities, category):
        """Calculate quality score for a medical fact"""
        score = 0.0
        
        # Length bonus (longer facts often more informative)
        if len(text) > 100:
            score += 0.3
        elif len(text) > 50:
            score += 0.2
        else:
            score += 0.1
        
        # Medical entity bonus
        entity_count = len(entities)
        if entity_count >= 3:
            score += 0.4
        elif entity_count >= 2:
            score += 0.3
        elif entity_count >= 1:
            score += 0.2
        
        # Medical keyword density (enhanced with more medical terms)
        medical_keywords = [
            'treatment', 'therapy', 'medication', 'drug', 'dose', 'dosage',
            'efficacy', 'effective', 'clinical', 'trial', 'study', 'research',
            'patient', 'diagnosis', 'symptom', 'disease', 'condition',
            'adverse', 'side effect', 'contraindication', 'indication',
            'management', 'care', 'intervention', 'outcome', 'result',
            'prevention', 'screening', 'vaccination', 'antibiotic', 'antiviral',
            'surgery', 'surgical', 'procedure', 'operation', 'transplant',
            'chemotherapy', 'radiotherapy', 'immunotherapy', 'rehabilitation',
            'hospital', 'healthcare', 'medical', 'physician', 'nurse',
            'injection', 'infusion', 'tablet', 'capsule', 'ointment'
        ]
        
        word_count = len(text.split())
        medical_word_count = sum(1 for word in text.split() if word.lower() in medical_keywords)
        
        if word_count > 0:
            keyword_density = medical_word_count / word_count
            score += min(keyword_density * 0.3, 0.3)  # Cap at 0.3
        
        return min(score, 1.0)  # Cap at 1.0
    
    def detect_negation_uncertainty(self, text):
        """Detect negation and uncertainty in medical text"""
        negation_patterns = [
            r'\bno\b', r'\bnot\b', r'\bnever\b', r'\bneither\b', r'\bnor\b',
            r'\babsent\b', r'\babsence\b', r'\bdenies\b', r'\bdenied\b',
            r'\bnegative\b', r'\bwithout\b', r'\bunlikely\b', r'\bfailed\b',
            r'\bcannot\b', r'\bcan\'t\b', r'\bwon\'t\b', r'\bdidn\'t\b'
        ]
        
        uncertainty_patterns = [
            r'\bpossible\b', r'\bpossibly\b', r'\bprobable\b', r'\bprobably\b',
            r'\blikely\b', r'\bmay\b', r'\bmight\b', r'\bcould\b', r'\bseems\b',
            r'\bappears\b', r'\bsuggests\b', r'\bsuspected\b', r'\bquestionable\b',
            r'\bundetermined\b', r'\bunclear\b', r'\bunknown\b', r'\bpotential\b'
        ]
        
        text_lower = text.lower()
        
        has_negation = any(re.search(pattern, text_lower) for pattern in negation_patterns)
        has_uncertainty = any(re.search(pattern, text_lower) for pattern in uncertainty_patterns)
        
        return {
            'has_negation': has_negation,
            'has_uncertainty': has_uncertainty,
            'confidence_modifier': 0.3 if has_negation else (0.7 if has_uncertainty else 1.0)
        }
    
    def grade_evidence_quality(self, title, source, publication_year=None):
        """Grade evidence quality based on publication type and recency"""
        if not isinstance(title, str):
            title = ""
        if not isinstance(source, str):
            source = ""
        
        combined_text = (title + " " + source).lower()
        
        # High-quality evidence types
        high_quality_patterns = [
            r'systematic review', r'meta-analysis', r'randomized controlled trial',
            r'clinical trial', r'guideline', r'consensus', r'cochrane',
            r'evidence-based', r'practice guideline'
        ]
        
        # Medium-quality evidence types
        medium_quality_patterns = [
            r'prospective', r'cohort study', r'case-control', r'observational',
            r'multicenter', r'clinical study', r'comparative study'
        ]
        
        # Low-quality evidence types
        low_quality_patterns = [
            r'case report', r'case series', r'opinion', r'editorial',
            r'letter', r'commentary', r'perspective', r'anecdotal'
        ]
        
        # Base quality score
        base_score = 0.5  # Default
        if any(re.search(pattern, combined_text) for pattern in high_quality_patterns):
            base_score = 1.0
        elif any(re.search(pattern, combined_text) for pattern in medium_quality_patterns):
            base_score = 0.7
        elif any(re.search(pattern, combined_text) for pattern in low_quality_patterns):
            base_score = 0.3
        
        # Recency bonus (newer research gets higher score)
        if publication_year and not pd.isna(publication_year):
            current_year = datetime.today().year
            years_old = current_year - publication_year
            
            if years_old <= 2:
                recency_bonus = 0.2  # Very recent
            elif years_old <= 5:
                recency_bonus = 0.1  # Recent
            elif years_old <= 10:
                recency_bonus = 0.0  # Moderate
            else:
                recency_bonus = -0.1  # Older research gets slight penalty
        else:
            recency_bonus = 0.0
        
        final_score = min(base_score + recency_bonus, 1.0)
        return max(final_score, 0.0)  # Ensure non-negative
    
    def extract_relationships(self, text, entities):
        """Extract medical relationships from text"""
        relationships = []
        
        if not entities or len(entities) < 2:
            return relationships
        
        # Relationship patterns
        treatment_patterns = [
            r'(\w+)\s+(?:treat|treats|treating|treatment for|therapy for|used for)\s+(\w+)',
            r'(\w+)\s+(?:is|was|were)\s+(?:prescribed|given|administered)\s+(?:for|to treat)\s+(\w+)',
            r'(\w+)\s+(?:effective|efficacious)\s+(?:for|against|in)\s+(\w+)'
        ]
        
        causes_patterns = [
            r'(\w+)\s+(?:cause|causes|causing|leads to|results in)\s+(\w+)',
            r'(\w+)\s+(?:associated with|linked to|related to)\s+(\w+)'
        ]
        
        prevents_patterns = [
            r'(\w+)\s+(?:prevent|prevents|preventing|prevention of)\s+(\w+)',
            r'(\w+)\s+(?:reduce|reduces|reducing)\s+(?:risk of|incidence of)\s+(\w+)'
        ]
        
        text_lower = text.lower()
        
        # Extract treatment relationships
        for pattern in treatment_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                relationships.append({
                    'type': 'treats',
                    'subject': match.group(1),
                    'object': match.group(2),
                    'confidence': 0.8
                })
        
        # Extract causation relationships
        for pattern in causes_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                relationships.append({
                    'type': 'causes',
                    'subject': match.group(1),
                    'object': match.group(2),
                    'confidence': 0.7
                })
        
        # Extract prevention relationships
        for pattern in prevents_patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                relationships.append({
                    'type': 'prevents',
                    'subject': match.group(1),
                    'object': match.group(2),
                    'confidence': 0.8
                })
        
        return relationships
    
    def advanced_semantic_deduplication(self, df, similarity_threshold=0.87):
        """
        Advanced semantic deduplication with multi-model fallback
        Uses PubMedBERT → S-PubMedBert-MS-MARCO → TF-IDF hierarchy
        """
        print(f"\n ADVANCED SEMANTIC DEDUPLICATION")
        print("=" * 45)
        print(f"    Initial facts: {len(df):,}")
        print(f"    Similarity threshold: {similarity_threshold}")
        
        if len(df) < 2:
            print(" Not enough facts for deduplication")
            return df
        
        texts = df['normalized_text'].fillna('').tolist()
        embeddings = None
        method_used = None
        
        # Try each method in order of preference
        for method in self.available_methods:
            print(f"\n Attempting: {method.upper()}")
            
            if method == 'pubmedbert' and 'pubmedbert_model' in self.embedding_models:
                embeddings = self._get_pubmedbert_embeddings(texts)
                if embeddings is not None:
                    method_used = 'PubMedBERT'
                    break

            elif method == 'spubmedbert' and 'spubmedbert_model' in self.embedding_models:
                embeddings = self._get_spubmedbert_embeddings(texts)
                if embeddings is not None:
                    method_used = 'S-PubMedBert-MS-MARCO'
                    break
                    
            elif method == 'tfidf':
                embeddings = self._get_tfidf_embeddings(texts)
                if embeddings is not None:
                    method_used = 'TF-IDF'
                    break
        
        if embeddings is None:
            print("  All embedding methods failed!")
            return df.drop_duplicates(subset=['normalized_text'], keep='first')
        
        print(f"    Successfully using: {method_used}")
        print(f"    Embedding shape: {embeddings.shape}")
        
        # Calculate semantic similarities using efficient top-k search
        print("  Finding semantic duplicates with top-k similarity search...")
        
        # Use Faiss for efficient similarity search if available
        if FAISS_AVAILABLE and len(embeddings) > 1000:
            duplicates = self._find_duplicates_faiss(embeddings, similarity_threshold, k=20)
        else:
            # Fallback to batch processing for smaller datasets or when Faiss is unavailable
            duplicates = self._find_duplicates_batch(embeddings, similarity_threshold, batch_size=500)
        
        # Identify which documents to remove (keep highest quality from each duplicate pair)
        print(" Resolving duplicate pairs...")
        to_remove = self._resolve_duplicate_pairs(duplicates, df)
        
        # Remove duplicates
        df_deduplicated = df.drop(df.index[list(to_remove)])
        
        # Statistics
        removed_count = len(to_remove)
        
        print(f"\n DEDUPLICATION RESULTS:")
        print(f" Method used: {method_used}")
        print(f" Duplicate pairs found: {len(duplicates):,}")
        print(f" Duplicates removed: {removed_count:,}")
        print(f" Final facts: {len(df_deduplicated):,}")
        print(f" Reduction: {(removed_count/len(df)*100):.1f}%")
        
        return df_deduplicated.reset_index(drop=True)
    
    def _find_duplicates_faiss(self, embeddings, threshold=0.87, k=20):
        """Find duplicates using Faiss for efficient top-k similarity search"""
        print(f"      Using Faiss top-k search (k={k}, threshold={threshold})")
        
        # Normalize embeddings for cosine similarity
        embeddings_normalized = embeddings.astype('float32')
        faiss.normalize_L2(embeddings_normalized)
        
        # Build Faiss index
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        index.add(embeddings_normalized)
        
        # Search for top-k similar documents for each document
        similarities, indices = index.search(embeddings_normalized, k + 1)  # +1 to exclude self
        
        duplicates = []
        for i, (sims, idxs) in enumerate(zip(similarities, indices)):
            # Skip first result (self-match with similarity 1.0)
            for sim, idx in zip(sims[1:], idxs[1:]):
                if sim > threshold and i < idx:  # Avoid duplicate pairs and self-matches
                    duplicates.append((i, idx, float(sim)))
        
        print(f"         Found {len(duplicates)} duplicate pairs")
        return duplicates
    
    def _find_duplicates_batch(self, embeddings, threshold=0.87, batch_size=500):
        """Find duplicates using batched processing (fallback when Faiss unavailable)"""
        print(f"      Using batched similarity search (batch_size={batch_size}, threshold={threshold})")
        
        duplicates = []
        n = len(embeddings)
        
        for i in range(0, n, batch_size):
            end_i = min(i + batch_size, n)
            batch_embeddings = embeddings[i:end_i]
            
            # Calculate similarities between this batch and all embeddings
            batch_similarities = cosine_similarity(batch_embeddings, embeddings)
            
            # Find high-similarity pairs
            for batch_idx, similarities_row in enumerate(batch_similarities):
                global_idx = i + batch_idx
                for j, sim in enumerate(similarities_row):
                    if sim > threshold and global_idx < j:  # Avoid duplicates and self-matches
                        duplicates.append((global_idx, j, float(sim)))
            
            if i % (batch_size * 5) == 0:
                print(f"         Batch progress: {end_i}/{n}")
        
        print(f"         Found {len(duplicates)} duplicate pairs")
        return duplicates
    
    def _resolve_duplicate_pairs(self, duplicates, df):
        """Resolve duplicate pairs by keeping the highest quality document from each pair"""
        to_remove = set()
        
        # Sort duplicates by similarity (highest first) to prioritize clear duplicates
        duplicates_sorted = sorted(duplicates, key=lambda x: x[2], reverse=True)
        
        for idx1, idx2, similarity in duplicates_sorted:
            # Skip if either document is already marked for removal
            if idx1 in to_remove or idx2 in to_remove:
                continue
            
            # Get quality scores (use default if not available)
            quality1 = df.iloc[idx1].get('quality_score', 0.5)
            quality2 = df.iloc[idx2].get('quality_score', 0.5)
            
            # Remove the lower quality document
            if quality1 >= quality2:
                to_remove.add(idx2)
            else:
                to_remove.add(idx1)
        
        return to_remove
    

    def preprocess_knowledge_base(self, input_path, output_path):
        """Complete preprocessing pipeline"""
        print(" MEDICAL KNOWLEDGE BASE PREPROCESSING")
        print("=" * 50)
        
        # Load raw data
        print(" Loading raw knowledge base...")
        df = pd.read_csv(input_path)
        print(f"   Loaded {len(df)} raw facts")
        
        # Handle new fields from expanded pubmed fetcher
        if 'year' not in df.columns:
            df['year'] = ''
        if 'query_original' not in df.columns:
            df['query_original'] = df.get('category', '')
        
        # Clean and validate year data
        df['year'] = df['year'].fillna('').astype(str)
        df['publication_year'] = pd.to_numeric(df['year'], errors='coerce')
        
        yr_min = df['publication_year'].min()
        yr_max = df['publication_year'].max()
        yr_range = (
            f"{yr_min:.0f} - {yr_max:.0f}"
            if pd.notna(yr_min) and pd.notna(yr_max)
            else "unknown"
        )
        print(f"   Year range: {yr_range}")
        
        # Step 1: Text normalization
        print("\n Normalizing text...")
        df['normalized_text'] = df['text'].apply(self.normalize_text)
        
        # Step 2: Medical entity extraction and specialty categorization
        print(" Extracting medical entities and categorizing by specialty...")
        df['entities'] = df['normalized_text'].apply(self.extract_medical_entities)
        df['entity_count'] = df['entities'].apply(len)
        df['medical_specialty'] = df.apply(
            lambda row: self.categorize_by_specialty(row['normalized_text'], row['category']), axis=1
        )
        
        # Step 3: Negation and uncertainty detection
        print("3. Detecting negation and uncertainty...")
        negation_data = df['normalized_text'].apply(self.detect_negation_uncertainty)
        df['has_negation'] = negation_data.apply(lambda x: x['has_negation'])
        df['has_uncertainty'] = negation_data.apply(lambda x: x['has_uncertainty'])
        df['confidence_modifier'] = negation_data.apply(lambda x: x['confidence_modifier'])
        
        # Step 4: Evidence quality grading (enhanced with year consideration)
        print("4. Grading evidence quality...")
        df['evidence_grade'] = df.apply(
            lambda row: self.grade_evidence_quality(row.get('title', ''), row.get('source', ''), row.get('publication_year', None)), axis=1
        )
        
        # Step 5: Relationship extraction
        print("5. Extracting medical relationships...")
        df['relationships'] = df.apply(
            lambda row: self.extract_relationships(row['normalized_text'], row['entities']), axis=1
        )
        df['relationship_count'] = df['relationships'].apply(len)
        
        # Step 6: Quality scoring 
        print("6. Calculating quality scores...")
        df['quality_score'] = df.apply(
            lambda row: self.calculate_quality_score(
                row['normalized_text'], 
                row['entities'], 
                row.get('category', '')
            ) * row['confidence_modifier'] * row['evidence_grade'], axis=1
        )
        
        # Step 7: Advanced semantic deduplication with multi-model fallback
        print("7. Advanced semantic deduplication...")
        df = self.advanced_semantic_deduplication(df)
        
        # Step 8: Quality filtering
        print("8. Filtering by quality...")
        quality_threshold = 0.3
        high_quality_df = df[df['quality_score'] >= quality_threshold]
        print(f"   Kept {len(high_quality_df)} high-quality facts (score >= {quality_threshold})")
        
        # Step 9: Final cleanup and export
        print("9. Final cleanup and export...")
        
        # Create final dataset with all fields including new ones
        final_df = high_quality_df[[
            'text', 'normalized_text', 'source', 'title', 'category', 'year', 'query_original',
            'medical_specialty', 'quality_score', 'entity_count', 'has_negation', 'has_uncertainty',
            'confidence_modifier', 'evidence_grade', 'relationship_count', 'publication_year'
        ]].copy()
        
        # Sort by quality score (best first)
        final_df = final_df.sort_values('quality_score', ascending=False)
        
        # Save preprocessed data
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_df.to_csv(output_path, index=False)
        
        # Generate statistics
        print(f"\n PREPROCESSING COMPLETE!")
        print(f" FINAL STATISTICS:")
        print(f"=" * 50)
        print(f"    Original facts: {len(df):,}")
        print(f"    High-quality facts: {len(final_df):,}")
        print(f"    Quality improvement: {((len(final_df)/len(df))*100):.1f}% retained")
        print(f"    Average quality score: {final_df['quality_score'].mean():.3f}")
        print(f"    Categories: {final_df['category'].nunique()}")
        print(f"    Facts with entities: {len(final_df[final_df['entity_count'] > 0])}")
        print(f"    Facts with negation: {len(final_df[final_df['has_negation']])}")
        print(f"    Facts with uncertainty: {len(final_df[final_df['has_uncertainty']])}")
        print(f"    Facts with relationships: {len(final_df[final_df['relationship_count'] > 0])}")
        print(f"    Average evidence grade: {final_df['evidence_grade'].mean():.3f}")
        print(f"    Recent facts (2020+): {len(final_df[final_df['publication_year'] >= 2020])}")
        print(f"    Query categories: {final_df['query_original'].nunique()}")
        print(f"    Medical specialties: {final_df['medical_specialty'].nunique()}")
        print(f"    Top specialties: {', '.join(final_df['medical_specialty'].value_counts().head(3).index.tolist())}")
        print(f"    Saved to: {output_path}")
        
        # Generate detailed report
        self._generate_preprocessing_report(final_df, output_path)

        # DATA-01: write reproducibility audit record after all artifacts saved
        embeddings_path = os.path.join(os.path.dirname(output_path), 'kb_embeddings_preprocessed.npy')
        self._write_kb_metadata(output_path, embeddings_path, final_df)

        return final_df
    
    def _write_kb_metadata(self, csv_path: str, embeddings_path: str, final_df) -> str:
        """
        Write data/kb_metadata.json as the final audit record for this KB build.

        Called ONLY after both csv_path and embeddings_path are confirmed saved.
        If either artifact is missing, raises FileNotFoundError so no partial JSON
        is written.

        Returns the path written.
        """
        for artifact in (csv_path, embeddings_path):
            if not os.path.exists(artifact):
                raise FileNotFoundError(
                    f"KB artifact not found — cannot write metadata: {artifact}"
                )

        def _sha256_file(path: str) -> str:
            h = hashlib.sha256()
            with open(path, 'rb') as fh:
                for chunk in iter(lambda: fh.read(8192), b''):
                    h.update(chunk)
            return h.hexdigest()

        # Derive embedding model name from method priority
        method_to_model = {
            'pubmedbert': 'neuml/pubmedbert-base-embeddings',
            'spubmedbert': 'pritamdeka/S-PubMedBert-MS-MARCO',
            'tfidf': 'tfidf',
        }
        primary_method = self.available_methods[0] if self.available_methods else 'unknown'
        embedding_model = method_to_model.get(primary_method, primary_method)

        pubmed_queries = 0
        if 'query_original' in final_df.columns:
            pubmed_queries = int(final_df['query_original'].nunique())

        metadata = {
            'generated_at': datetime.utcnow().isoformat() + 'Z',
            'embedding_model': embedding_model,
            'row_count': int(len(final_df)),
            'csv_sha256': _sha256_file(csv_path),
            'embeddings_sha256': _sha256_file(embeddings_path),
            'pubmed_queries': pubmed_queries,
        }

        metadata_path = os.path.join(os.path.dirname(csv_path), 'kb_metadata.json')
        payload = json.dumps(metadata, indent=2)
        with open(metadata_path, 'w', encoding='utf-8') as fh:
            fh.write(payload)

        print(f"    KB metadata written to: {metadata_path}")
        return metadata_path

    def _generate_preprocessing_report(self, df, output_path):
        """Generate detailed preprocessing report"""
        try:
            report_path = output_path.replace('.csv', '_report.txt')
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("MEDICAL KNOWLEDGE BASE PREPROCESSING REPORT\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f" ADVANCED SEMANTIC PROCESSING METHODS USED:\n")
                f.write(f"   Primary Methods: {' → '.join(self.available_methods)}\n")
                f.write(f"   Embedding Models: {len(self.embedding_models)} loaded\n\n")
                
                f.write(f" DATASET STATISTICS:\n")
                f.write(f"   Total Facts: {len(df):,}\n")
                f.write(f"   Quality Score Range: {df['quality_score'].min():.3f} - {df['quality_score'].max():.3f}\n")
                f.write(f"   Entity Count Range: {df['entity_count'].min()} - {df['entity_count'].max()}\n")
                f.write(f"   Publication Years: {df['publication_year'].min():.0f} - {df['publication_year'].max():.0f}\n\n")
                
                f.write(f" MEDICAL SPECIALTY DISTRIBUTION:\n")
                specialty_counts = df['medical_specialty'].value_counts()
                for specialty, count in specialty_counts.head(10).items():
                    f.write(f"   {specialty}: {count:,} facts\n")
                
                f.write(f"\n QUALITY ANALYSIS:\n")
                f.write(f"   High Quality (>0.7): {len(df[df['quality_score'] > 0.7]):,}\n")
                f.write(f"   Medium Quality (0.4-0.7): {len(df[(df['quality_score'] >= 0.4) & (df['quality_score'] <= 0.7)]):,}\n")
                f.write(f"   With Medical Entities: {len(df[df['entity_count'] > 0]):,}\n")
                f.write(f"   With Relationships: {len(df[df['relationship_count'] > 0]):,}\n")
                
            print(f"    Detailed report saved to: {report_path}")
            
        except Exception as e:
            print(f"    Could not generate report: {e}")

def main():
    """Run medical knowledge base preprocessing"""
    print(" MEDICAL KNOWLEDGE BASE ADVANCED PREPROCESSING")
    print("=" * 55)
    
    preprocessor = MedicalPreprocessor()
    
    # Test embedding system
    print(f"\n TESTING EMBEDDING SYSTEM:")
    test_texts = [
        "Metformin is effective for treating type 2 diabetes mellitus",
        "Type 2 diabetes can be managed with metformin therapy",
        "Aspirin reduces cardiovascular risk in patients"
    ]
    
    for method in preprocessor.available_methods:
        print(f"   Testing {method}... ", end="")
        if method == 'pubmedbert' and 'pubmedbert_model' in preprocessor.embedding_models:
            test_emb = preprocessor._get_pubmedbert_embeddings(test_texts[:2])
            print("PASS" if test_emb is not None else "FAIL")
        elif method == 'spubmedbert' and 'spubmedbert_model' in preprocessor.embedding_models:
            test_emb = preprocessor._get_spubmedbert_embeddings(test_texts[:2])
            print("PASS" if test_emb is not None else "FAIL")
        elif method == 'tfidf':
            test_emb = preprocessor._get_tfidf_embeddings(test_texts)
            print("PASS" if test_emb is not None else "FAIL")
    
    # Preprocess the expanded knowledge base
    input_path = './data/expanded_knowledge_base.csv'
    output_path = './data/expanded_knowledge_base_preprocessed.csv'
    
    if os.path.exists(input_path):
        preprocessed_kb = preprocessor.preprocess_knowledge_base(input_path, output_path)
        print(f"\n PREPROCESSED KNOWLEDGE BASE READY!")
        print(f" Ready for high-accuracy medical verification!")
    else:
        print(f" Input file not found: {input_path}")
        print("   Please run pubmed_fetcher.py first to create the expanded knowledge base")

if __name__ == "__main__":
    main()
