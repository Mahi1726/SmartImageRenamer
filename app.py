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
    3. **Click Match**: Process and view results
    4. **Download results**: Get your matches in various formats
    """)

# Main content area
col1, col2 = st.columns(2)

with col1:
    st.header("📝 Input Prompts")
    
    # File upload for prompts
    uploaded_file = st.file_uploader(
        "Upload prompts file (.txt)",
        type=['txt'],
        help="Text file with one prompt per line"
    )
    
    # Text area for manual prompt input
    prompt_text = st.text_area(
        "Or paste prompts here (one per line)",
        height=200,
        placeholder="1. An_English_sailor_writes_a_heartfelt_letter_to_his_wife\n2. A_cat_sleeping_on_a_window_with_sunlight\n3. A_futuristic_city_with_flying_cars"
    )

with col2:
    st.header("🖼️ Image Filenames")
    
    # Text area for image filenames
    image_filenames_text = st.text_area(
        "Enter image filenames (one per line)",
        height=200,
        placeholder="asif4876_An_English_sailor_writes_a_heartfelt_letter_to_his_w_172bb4b0.png\nuser9_A_futuristic_city_with_flying_cars_8ff92123.png"
    )

# Process button
if st.button("🔍 Match Prompts to Images", type="primary", use_container_width=True):
    # Get prompts
    prompts = []
    if uploaded_file is not None:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        prompts = [line.strip() for line in stringio if line.strip()]
    elif prompt_text:
        prompts = [line.strip() for line in prompt_text.split('\n') if line.strip()]
    
    # Get image filenames
    image_filenames = [line.strip() for line in image_filenames_text.split('\n') if line.strip()]
    
    # Validate inputs
    if not prompts:
        st.error("❌ Please provide prompts either by uploading a file or entering them manually.")
    elif not image_filenames:
        st.error("❌ Please enter image filenames.")
    else:
        # Create matcher and process
        matcher = PromptImageMatcher(similarity_threshold=similarity_threshold)
        
        with st.spinner("Processing matches..."):
            results = matcher.match_prompts_to_images(prompts, image_filenames)
        
        # Display results
        st.markdown("---")
        st.header("📊 Results")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Prompts", results["summary"]["total_prompts"])
        with col2:
            st.metric("Matched", results["summary"]["matched"], 
                     delta=f"{results['summary']['matched']/results['summary']['total_prompts']*100:.1f}%")
        with col3:
            st.metric("Missing", results["summary"]["missing"])
        
        # Detailed results in tabs
        tab1, tab2, tab3 = st.tabs(["✅ Matches", "❌ Missing", "📄 Full Log"])
        
        with tab1:
            if results["matches"]:
                matches_df = pd.DataFrame(results["matches"])
                st.dataframe(
                    matches_df[["prompt_number", "prompt", "image", "similarity_score"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No matches found.")
        
        with tab2:
            if results["missing"]:
                missing_df = pd.DataFrame(results["missing"])
                st.dataframe(
                    missing_df[["prompt_number", "prompt", "best_score"]],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("All prompts matched!")
        
        with tab3:
            # Generate full log
            log_lines = []
            all_results = []
            
            for match in results["matches"]:
                all_results.append((
                    match["prompt_number"], 
                    f"Prompt {match['prompt_number']} → {match['image']} (score: {match['similarity_score']})"
                ))
            
            for missing in results["missing"]:
                all_results.append((
                    missing["prompt_number"], 
                    f"Prompt {missing['prompt_number']} → missing (best score: {missing['best_score']})"
                ))
            
            all_results.sort(key=lambda x: x[0])
            
            for _, line in all_results:
                log_lines.append(line)
            
            log_text = "\n".join(log_lines)
            st.text_area("Full Log", log_text, height=300)
        
        # Download options
        st.markdown("---")
        st.header("💾 Download Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Download as text log
            st.download_button(
                label="📄 Download as Text",
                data=log_text,
                file_name="matching_results.txt",
                mime="text/plain"
            )
        
        with col2:
            # Download as JSON
            json_str = json.dumps(results, indent=2)
            st.download_button(
                label="📊 Download as JSON",
                data=json_str,
                file_name="matching_results.json",
                mime="application/json"
            )
        
        with col3:
            # Download as CSV
            all_data = []
            for match in results["matches"]:
                all_data.append({
                    "prompt_number": match["prompt_number"],
                    "prompt": match["prompt"],
                    "status": "matched",
                    "image": match["image"],
                    "score": match["similarity_score"]
                })
            for missing in results["missing"]:
                all_data.append({
                    "prompt_number": missing["prompt_number"],
                    "prompt": missing["prompt"],
                    "status": "missing",
                    "image": "",
                    "score": missing["best_score"]
                })
            
            if all_data:
                df = pd.DataFrame(all_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📑 Download as CSV",
                    data=csv,
                    file_name="matching_results.csv",
                    mime="text/csv"
                )

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")
