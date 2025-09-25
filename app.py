import streamlit as st
import os
import re
from difflib import SequenceMatcher
from typing import List, Tuple, Dict, Optional
import json
import pandas as pd
from io import StringIO, BytesIO
import zipfile
from PIL import Image

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
    
    def match_prompts_to_images(self, prompts: List[str], uploaded_files: Dict) -> Dict:
        results = {
            "matches": [],
            "missing": [],
            "summary": {
                "total_prompts": len(prompts),
                "matched": 0,
                "missing": 0
            }
        }
        
        filenames = list(uploaded_files.keys())
        used_filenames = set()
        available_filenames = set(filenames)
        
        for i, prompt in enumerate(prompts, 1):
            prompt_text = re.sub(r'^\d+\.\s*', '', prompt).strip()
            
            candidates = list(available_filenames - used_filenames)
            match, score = self.find_best_match(prompt_text, candidates)
            
            if match:
                # Generate new filename based on prompt order
                new_filename = f"{i:03d}_{prompt_text[:50]}.png"  # Limit filename length
                new_filename = re.sub(r'[<>:"/\\|?*]', '_', new_filename)  # Remove invalid chars
                
                results["matches"].append({
                    "prompt_number": i,
                    "prompt": prompt_text,
                    "original_filename": match,
                    "new_filename": new_filename,
                    "file_data": uploaded_files[match],
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
    page_title="Prompt-Image Matcher & Renamer",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Prompt-Image Matcher & Renamer")
st.markdown("Match prompts to uploaded images and rename them according to prompt order")

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
    
    naming_convention = st.selectbox(
        "Naming Convention",
        ["Sequential (001_prompt.png)", "Prompt only (prompt.png)", "Custom prefix"],
        help="How to rename the matched images"
    )
    
    if naming_convention == "Custom prefix":
        custom_prefix = st.text_input("Custom prefix", "image")
    
    st.markdown("---")
    st.markdown("### 📋 Instructions")
    st.markdown("""
    1. **Upload prompts**: Text file with one prompt per line
    2. **Upload images**: PNG files to match and rename
    3. **Click Match**: Process and preview results
    4. **Download**: Get renamed images as a ZIP file
    """)

# Main content area
col1, col2 = st.columns(2)

with col1:
    st.header("📝 Input Prompts")
    
    # File upload for prompts
    uploaded_prompt_file = st.file_uploader(
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
    st.header("🖼️ Upload Images")
    
    # Multiple file upload for images
    uploaded_images = st.file_uploader(
        "Upload PNG images",
        type=['png'],
        accept_multiple_files=True,
        help="Select all PNG images to match with prompts"
    )
    
    if uploaded_images:
        st.info(f"📁 {len(uploaded_images)} images uploaded")
        
        # Show uploaded filenames
        with st.expander("View uploaded filenames"):
            for img in uploaded_images:
                st.text(img.name)

# Process button
if st.button("🔍 Match & Prepare Rename", type="primary", use_container_width=True):
    # Get prompts
    prompts = []
    if uploaded_prompt_file is not None:
        stringio = StringIO(uploaded_prompt_file.getvalue().decode("utf-8"))
        prompts = [line.strip() for line in stringio if line.strip()]
    elif prompt_text:
        prompts = [line.strip() for line in prompt_text.split('\n') if line.strip()]
    
    # Validate inputs
    if not prompts:
        st.error("❌ Please provide prompts either by uploading a file or entering them manually.")
    elif not uploaded_images:
        st.error("❌ Please upload PNG images.")
    else:
        # Create dictionary of uploaded files
        uploaded_files = {img.name: img for img in uploaded_images}
        
        # Create matcher and process
        matcher = PromptImageMatcher(similarity_threshold=similarity_threshold)
        
        with st.spinner("Processing matches..."):
            results = matcher.match_prompts_to_images(prompts, uploaded_files)
        
        # Store results in session state
        st.session_state['results'] = results
        
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
        
        # Preview matches with thumbnails
        if results["matches"]:
            st.subheader("✅ Matched Images (Preview)")
            
            # Create columns for preview
            preview_cols = st.columns(3)
            
            for idx, match in enumerate(results["matches"][:9]):  # Show first 9
                col_idx = idx % 3
                with preview_cols[col_idx]:
                    # Display thumbnail
                    image = Image.open(match["file_data"])
                    st.image(image, use_column_width=True)
                    st.caption(f"**New name:** {match['new_filename']}")
                    st.caption(f"Original: {match['original_filename']}")
                    st.caption(f"Score: {match['similarity_score']}")
            
            if len(results["matches"]) > 9:
                st.info(f"Showing first 9 of {len(results['matches'])} matches")
        
        # Show missing prompts
        if results["missing"]:
            with st.expander(f"❌ Missing Images ({len(results['missing'])})"):
                missing_df = pd.DataFrame(results["missing"])
                st.dataframe(
                    missing_df[["prompt_number", "prompt", "best_score"]],
                    use_container_width=True,
                    hide_index=True
                )

# Download section
if 'results' in st.session_state and st.session_state['results']['matches']:
    st.markdown("---")
    st.header("💾 Download Renamed Images")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Generate rename mapping CSV
        mapping_data = []
        for match in st.session_state['results']['matches']:
            mapping_data.append({
                "prompt_number": match["prompt_number"],
                "prompt": match["prompt"],
                "original_filename": match["original_filename"],
                "new_filename": match["new_filename"],
                "similarity_score": match["similarity_score"]
            })
        
        mapping_df = pd.DataFrame(mapping_data)
        csv = mapping_df.to_csv(index=False)
        
        st.download_button(
            label="📑 Download Rename Mapping (CSV)",
            data=csv,
            file_name="rename_mapping.csv",
            mime="text/csv"
        )
    
    with col2:
        # Create ZIP file with renamed images
        if st.button("📦 Generate ZIP with Renamed Images", type="primary"):
            with st.spinner("Creating ZIP file..."):
                # Create a BytesIO object to store the ZIP
                zip_buffer = BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for match in st.session_state['results']['matches']:
                        # Get the image data
                        img_data = match["file_data"].getvalue()
                        
                        # Determine filename based on naming convention
                        if naming_convention == "Sequential (001_prompt.png)":
                            filename = match["new_filename"]
                        elif naming_convention == "Prompt only (prompt.png)":
                            prompt_clean = re.sub(r'[<>:"/\\|?*]', '_', match["prompt"][:100])
                            filename = f"{prompt_clean}.png"
                        else:  # Custom prefix
                            filename = f"{custom_prefix}_{match['prompt_number']:03d}.png"
                        
                        # Add to ZIP
                        zip_file.writestr(filename, img_data)
                
                # Prepare for download
                zip_buffer.seek(0)
                
                st.download_button(
                    label="⬇️ Download Renamed Images (ZIP)",
                    data=zip_buffer,
                    file_name="renamed_images.zip",
                    mime="application/zip"
                )
                
                st.success("✅ ZIP file ready for download!")

# Show detailed results table
if 'results' in st.session_state:
    with st.expander("📋 Detailed Results Table"):
        all_data = []
        for match in st.session_state['results']['matches']:
            all_data.append({
                "prompt_number": match["prompt_number"],
                "prompt": match["prompt"],
                "status": "matched",
                "original_filename": match["original_filename"],
                "new_filename": match["new_filename"],
                "score": match["similarity_score"]
            })
        for missing in st.session_state['results']['missing']:
            all_data.append({
                "prompt_number": missing["prompt_number"],
                "prompt": missing["prompt"],
                "status": "missing",
                "original_filename": "-",
                "new_filename": "-",
                "score": missing["best_score"]
            })
        
        if all_data:
            df = pd.DataFrame(all_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("Made with ❤️ using Streamlit")
