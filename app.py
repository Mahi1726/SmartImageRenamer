import streamlit as st
import os
import re
from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Optional
import json
import pandas as pd
from io import StringIO

class PromptImageMatcher:
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        
    def clean_text(self, text: str) -> str:
        # Remove UUID patterns
        text = re.sub(r'[a-f0-9]{8}[-_]?[a-f0-9]{4}[-_]?[a-f0-9]{4}[-_]?[a-f0-9]{4}[-_]?[a-f0-9]{12}', '', text, flags=re.IGNORECASE)
        text = re.sub(r'[a-f0-9]{6,}', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\.(png|jpg|jpeg|gif|webp)$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^[a-zA-Z0-9]+_', '', text)
        text = re.sub(r'_+\d*$', '', text)
        text = re.sub(r'_{2,}', '_', text)
        text = text.strip('_')
        return text.lower()
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        return SequenceMatcher(None, str1, str2).ratio()
    
    def extract_prompt_from_filename(self, filename: str) -> str:
        name_without_ext = os.path.splitext(filename)[0]
        cleaned = self.clean_text(name_without_ext)
        return cleaned
    
    def find_best_match(self, prompt: str, filenames: List[str]) -> Tuple[Optional[str], float]:
        cleaned_prompt = self.clean_text(prompt)
        best_match = None
        best_score = 0.0
        
        for filename in filenames:
            cleaned_filename = self.extract_prompt_from_filename(filename)
            
            if cleaned_prompt in cleaned_filename or cleaned_filename in cleaned_prompt:
                return filename, 1.0
            
            similarity = self.calculate_similarity(cleaned_prompt, cleaned_filename)
            
            if similarity > best_score:
                best_score = similarity
                best_match = filename
        
        if best_score >= self.similarity_threshold:
            return best_match, best_score
        
        return None, best_score
    
    def match_prompts_to_images(self, prompts: List[str], image_filenames: List[str]) -> Dict:
        results = {
            "matches": [],
            "missing": [],
            "summary": {
                "total_prompts": len(prompts),
                "matched": 0,
                "missing": 0
            }
        }
        
        used_filenames = set()
        available_filenames = set(image_filenames)
        
        for i, prompt in enumerate(prompts, 1):
            prompt_text = re.sub(r'^\d+\.\s*', '', prompt).strip()
            
            candidates = list(available_filenames - used_filenames)
            match, score = self.find_best_match(prompt_text, candidates)
            
            if match:
                results["matches"].append({
                    "prompt_number": i,
                    "prompt": prompt_text,
                    "image": match,
                    "similarity_score": round(score, 3)
                })
                used_filenames.add(match)
                results["summary"]["matched"] += 1
            else:
                results["missing"].append({
                    "prompt_number": i,
                    "prompt": prompt_text,
                    "best_score": round(score, 3)
                })
                results["summary"]["missing"] += 1
        
        return results

# Streamlit App
st.set_page_config(
    page_title="Prompt-Image Matcher",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Prompt-Image Matcher")
st.markdown("Match prompts to their generated images using fuzzy string matching")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    similarity_threshold = st.slider(
        "Similarity Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.85,
        step=0.05,
        help="Minimum similarity score for fuzzy matching"
    )
    
    st.markdown("---")
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. **Upload prompts**: Text file with one prompt per line
    2. **Enter image filenames**: One per line in the text area
    
