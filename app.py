import streamlit as st
import os
import zipfile
import tempfile
import shutil

st.title("📸 Smart Image Renamer")
st.write("Upload images and a prompts file, and get them renamed with a mapping file.")

# File upload widgets
uploaded_images = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
uploaded_prompts = st.file_uploader("Upload prompts.txt", type=["txt"])

if uploaded_images and uploaded_prompts:
    if st.button("🚀 Rename Images"):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save prompts.txt
            prompts_path = os.path.join(tmpdir, "prompts.txt")
            with open(prompts_path, "wb") as f:
                f.write(uploaded_prompts.read())
            
            # Load prompts
            with open(prompts_path, "r", encoding="utf-8") as f:
                prompts = [line.strip() for line in f if line.strip()]

            renamed_dir = os.path.join(tmpdir, "renamed")
            os.makedirs(renamed_dir, exist_ok=True)

            mapping_lines = []

            for idx, img_file in enumerate(uploaded_images, start=1):
                ext = os.path.splitext(img_file.name)[1].lower()
                new_name = f"{idx:03d}{ext}"
                new_path = os.path.join(renamed_dir, new_name)

                # Save image
                with open(new_path, "wb") as f:
                    f.write(img_file.read())

                prompt = prompts[idx - 1] if idx - 1 < len(prompts) else "NO PROMPT"
                mapping_lines.append(f"{new_name} | {img_file.name} | {prompt}")

            # Save mapping.txt
            mapping_path = os.path.join(renamed_dir, "mapping.txt")
            with open(mapping_path, "w", encoding="utf-8") as f:
                f.write("\n".join(mapping_lines))

            # Create ZIP for download
            zip_path = os.path.join(tmpdir, "renamed_images.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for root, _, files in os.walk(renamed_dir):
                    for file in files:
                        zipf.write(os.path.join(root, file), file)

            with open(zip_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Renamed Images + Mapping",
                    data=f,
                    file_name="renamed_images.zip",
                    mime="application/zip"
                )
