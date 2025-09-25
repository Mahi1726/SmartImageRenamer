import streamlit as st
import tempfile
import os
import shutil
import re
import zipfile
from rapidfuzz import fuzz

st.title("Debug Enhanced Midjourney Prompt-Image Matcher")

prompt_file = st.file_uploader("Upload prompts.txt", type=["txt"])
image_files = st.file_uploader("Upload PNG images", type=["png"], accept_multiple_files=True)

def clean_text(text):
    text = text.lower()
    text = re.sub(r"[’,.'\"-]", "", text)
    text = re.sub(r"\b[a-f0-9]{8,}\b", "", text)
    text = re.sub(r"[_\s]+", "_", text).strip("_")
    return text

def extract_prompt_from_filename(filename):
    name_part = filename.rsplit("_", 1)[0]
    return clean_text(name_part)

if prompt_file and image_files:
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts = [line.strip() for line in prompt_file if line.strip()]
        prompts = [p.decode("utf-8") if isinstance(p, bytes) else p for p in prompts]

        image_dir = os.path.join(tmpdir, "images")
        os.makedirs(image_dir, exist_ok=True)

        for im in image_files:
            with open(os.path.join(image_dir, im.name), "wb") as f:
                f.write(im.getbuffer())

        png_files = os.listdir(image_dir)
        cleaned_filenames = [(fname, extract_prompt_from_filename(fname)) for fname in png_files]

        output_dir = os.path.join(tmpdir, "output_images")
        os.makedirs(output_dir, exist_ok=True)

        used_images = set()
        mapping_log = []

        st.subheader("Cleaned Prompts")
        for p in prompts:
            st.text(clean_text(p))

        st.subheader("Cleaned Filenames")
        for fname, clean_fname in cleaned_filenames:
            st.text(f"{fname} -> {clean_fname}")

        for idx, prompt in enumerate(prompts, 1):
            clean_prompt = clean_text(prompt)

            # Try direct substring match
            direct_match = None
            for fname, cleaned_name in cleaned_filenames:
                if clean_prompt in cleaned_name and fname not in used_images:
                    direct_match = fname
                    break

            matched_file = direct_match

            # Try fuzzy matching if no direct match
            if not matched_file:
                candidates = [(fname, cleaned_name) for fname, cleaned_name in cleaned_filenames if fname not in used_images]
                best_match = None
                best_score = 0
                for fname, cleaned_name in candidates:
                    score = fuzz.ratio(clean_prompt, cleaned_name)
                    if score > best_score:
                        best_score = score
                        best_match = fname

                if best_score >= 70:
                    matched_file = best_match

            if matched_file:
                new_name = f"{idx:03}.png"
                shutil.copy(os.path.join(image_dir, matched_file), os.path.join(output_dir, new_name))
                mapping_log.append(f"Prompt {idx} → {matched_file} (score: {best_score if not direct_match else 100})")
                used_images.add(matched_file)
            else:
                mapping_log.append(f"Prompt {idx} → missing")

        st.subheader("Match Log")
        for log in mapping_log:
            st.text(log)
