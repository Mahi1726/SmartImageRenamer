import streamlit as st
from io import BytesIO
from zipfile import ZipFile
import os

st.title("Image Renamer with Prompts")

# Upload multiple images
uploaded_images = st.file_uploader("Upload images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# Upload prompts file
prompts_file = st.file_uploader("Upload prompts file", type=["txt"])

if st.button("Rename Images"):
    if not uploaded_images or not prompts_file:
        st.error("Please upload both images and a prompts file.")
    else:
        # Read prompts
        prompts = prompts_file.read().decode("utf-8").splitlines()
        prompt_dict = {}
        for line in prompts:
            parts = line.split("|")
            if len(parts) >= 2:
                prompt_dict[parts[1].strip()] = parts[2].strip() if len(parts) > 2 else parts[1].strip()

        # Sort uploaded images by filename
        uploaded_images.sort(key=lambda x: x.name)

        renamed_files = []

        for count, img_file in enumerate(uploaded_images, start=1):
            matched_prompt = None
            img_base = os.path.splitext(img_file.name)[0]
            for prompt_name in prompt_dict.keys():
                # Check if first few words match
                prompt_base = "_".join(prompt_name.split("_")[:5])
                if prompt_base in img_base:
                    matched_prompt = prompt_name
                    break

            if matched_prompt:
                new_name = f"{count:03}.png"
                renamed_files.append((new_name, img_file.getvalue()))
            else:
                # If no match, just keep original name but numbered
                new_name = f"{count:03}_{img_file.name}"
                renamed_files.append((new_name, img_file.getvalue()))

        # Create a ZIP file for download
        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w") as zip_file:
            for file_name, data in renamed_files:
                zip_file.writestr(file_name, data)

        st.download_button(
            label="Download Renamed Images",
            data=zip_buffer.getvalue(),
            file_name="renamed_images.zip",
            mime="application/zip"
        )

        st.success("Images renamed and ready for download!")
