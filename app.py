import streamlit as st
import os
from zipfile import ZipFile
from difflib import get_close_matches
import tempfile
import pandas as pd

st.title("MidJourney Image Renamer 📸➡️001,002,… + Mapping File")

# Upload prompts file
prompts_file = st.file_uploader("Upload your prompts.txt", type=["txt"])

# Upload images as a zip
images_zip = st.file_uploader("Upload your images as a ZIP", type=["zip"])

if prompts_file and images_zip:
    # Read prompts
    prompts = [line.strip().replace("___ar_16:9___v_6___style_raw", "") 
               for line in prompts_file.read().decode("utf-8").splitlines() if line.strip()]

    # Create temporary folder to extract images
    temp_dir = tempfile.mkdtemp()
    
    with ZipFile(images_zip, "r") as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # List PNG images
    images = [f for f in os.listdir(temp_dir) if f.lower().endswith(".png")]

    # Prepare mapping: remove UUID-like suffixes
    image_map = {}
    for img in images:
        parts = img.split("_")
        desc_part = "_".join(parts[1:-2]).lower()  # remove first and last UUID-like parts
        image_map[desc_part] = img

    renamed_files = []
    mapping_data = []

    for idx, prompt in enumerate(prompts, start=1):
        key = "_".join(prompt.split("_")[:10]).lower()
        match = get_close_matches(key, image_map.keys(), n=1, cutoff=0.1)
        if match:
            orig_name = image_map[match[0]]
            new_name = f"{idx:03d}.png"
            os.rename(os.path.join(temp_dir, orig_name), os.path.join(temp_dir, new_name))
            renamed_files.append(new_name)
            mapping_data.append({"Prompt_Number": idx, "Prompt": prompt, "Original_File": orig_name, "New_File": new_name})
        else:
            st.warning(f"No match found for prompt {idx}: {prompt}")

    # Create mapping CSV
    mapping_df = pd.DataFrame(mapping_data)
    mapping_csv_path = os.path.join(temp_dir, "mapping.csv")
    mapping_df.to_csv(mapping_csv_path, index=False)

    # Zip renamed files
    zip_path = os.path.join(temp_dir, "renamed_images.zip")
    with ZipFile(zip_path, "w") as zipf:
        for file in renamed_files:
            zipf.write(os.path.join(temp_dir, file), arcname=file)
        zipf.write(mapping_csv_path, arcname="mapping.csv")

    st.success("Images renamed successfully with mapping!")
    st.download_button("Download renamed images + mapping ZIP", zip_path)
