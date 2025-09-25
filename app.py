import streamlit as st
import tempfile
import os
import shutil
import re
import zipfile

st.title("Midjourney Image-Prompt Renamer")

# File upload widgets
prompt_file = st.file_uploader("Upload prompts.txt", type=["txt"])
image_files = st.file_uploader("Upload PNG images", type=["png"], accept_multiple_files=True)

def sanitize_text(text):
    # Lowercase and remove punctuation except underscores
    text = text.lower()
    text = re.sub(r"[’,.'\"-]", "", text)
    text = text.replace(" ", "_")
    return text

def extract_prompt_from_filename(filename):
    # Extract the part before the UUID suffix (assumed to be last hyphen/underscore + UUID)
    name_part = filename.rsplit("_", 1)[0]
    # Clean UUID-like patterns (if any trailing)
    return name_part.lower()

if prompt_file and image_files:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Load prompts lines
        prompts = [line.strip() for line in prompt_file if line.strip()]
        prompts = [p.decode("utf-8") if isinstance(p, bytes) else p for p in prompts]

        # Save images to temp directory for matching
        image_dir = os.path.join(tmpdir, "input_images")
        os.makedirs(image_dir, exist_ok=True)

        for file in image_files:
            with open(os.path.join(image_dir, file.name), "wb") as f:
                f.write(file.getbuffer())

        png_files = os.listdir(image_dir)
        output_dir = os.path.join(tmpdir, "output_images")
        os.makedirs(output_dir, exist_ok=True)

        used_imgs = set()
        mapping_log = []

        # Preprocess filenames to map prompt-like text to files
        filename_map = {}
        for fname in png_files:
            prompt_like = extract_prompt_from_filename(fname)
            filename_map[prompt_like] = fname

        # Match prompts to images by sanitized prompt prefix in filename keys
        for idx, prompt in enumerate(prompts, 1):
            sanitized_prompt = sanitize_text(prompt)
            matched_file = None
            # Use simple contains or startswith logic across filename keys
            for key in filename_map:
                if sanitized_prompt in key or key in sanitized_prompt:
                    if filename_map[key] not in used_imgs:
                        matched_file = filename_map[key]
                        break
            if matched_file:
                new_name = f"{idx:03}.png"
                shutil.copy(os.path.join(image_dir, matched_file), os.path.join(output_dir, new_name))
                mapping_log.append(f"{matched_file} -> {new_name} | {prompt}")
                used_imgs.add(matched_file)
            else:
                mapping_log.append(f"SKIPPED | {prompt}")

        # Create zip file of renamed images
        out_zip = os.path.join(tmpdir, "renamed_images.zip")
        with zipfile.ZipFile(out_zip, "w") as zipf:
            for f in os.listdir(output_dir):
                zipf.write(os.path.join(output_dir, f), arcname=f)

        # Prepare mapping log for download
        log_txt = "\n".join(mapping_log)

        # Download buttons
        st.download_button("Download Renamed Images ZIP", open(out_zip, "rb"), "renamed_images.zip")
        st.download_button("Download Mapping Log", log_txt, "mapping_log.txt")

        st.success("Renaming and matching complete. Download your files above.")
