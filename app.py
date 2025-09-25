import streamlit as st
import tempfile
import os
import shutil
import re
import zipfile
from rapidfuzz import fuzz, process

st.title("Midjourney Prompt-Image Matcher with Fuzzy Matching")

prompt_file = st.file_uploader("Upload prompts.txt", type=["txt"])
image_files = st.file_uploader("Upload PNG images", type=["png"], accept_multiple_files=True)

def clean_text(text):
    # Lowercase and remove UUIDs, special tokens, and trailing numbers nicely
    text = text.lower()
    text = re.sub(r"[’,.'\"-]", "", text)
    # Remove UUID-like hex sequences (8 or more hex chars)
    text = re.sub(r"\b[a-f0-9]{8,}\b", "", text)
    # Remove extra underscores and multiple spaces
    text = re.sub(r"[_\s]+", "_", text).strip("_")
    return text

def extract_prompt_from_filename(filename):
    name_part = filename.rsplit("_", 1)[0]  # remove UUID trailing part
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

        for idx, prompt in enumerate(prompts, 1):
            clean_prompt = clean_text(prompt)
            # Try direct substring match first
            direct_match = None
            for fname, cleaned_name in cleaned_filenames:
                if clean_prompt in cleaned_name and fname not in used_images:
                    direct_match = fname
                    break

            matched_file = direct_match
            # If no direct match, try fuzzy matching with threshold
            if not matched_file:
                candidates = [(fname, cleaned_name) for fname, cleaned_name in cleaned_filenames if fname not in used_images]
                if candidates:
                    # Select best fuzzy match
                    best_match = None
                    best_score = 0
                    for fname, cleaned_name in candidates:
                        score = fuzz.ratio(clean_prompt, cleaned_name)
                        if score > best_score:
                            best_score = score
                            best_match = fname
                    if best_score >= 85:  # threshold for acceptance
                        matched_file = best_match

            if matched_file:
                new_name = f"{idx:03}.png"
                shutil.copy(os.path.join(image_dir, matched_file), os.path.join(output_dir, new_name))
                mapping_log.append(f"Prompt {idx} → {matched_file}")
                used_images.add(matched_file)
            else:
                mapping_log.append(f"Prompt {idx} → missing")

        # Zip output images
        out_zip = os.path.join(tmpdir, "renamed_images.zip")
        with zipfile.ZipFile(out_zip, "w") as zipf:
            for f in os.listdir(output_dir):
                zipf.write(os.path.join(output_dir, f), arcname=f)

        mapping_log_text = "\n".join(mapping_log)

        st.download_button("Download Renamed Images ZIP", open(out_zip, "rb"), "renamed_images.zip")
        st.download_button("Download Matching Log", mapping_log_text, "mapping_log.txt")

        st.success("Matching complete. Download your files above.")
