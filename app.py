import streamlit as st
import os
import tempfile
import pandas as pd
from difflib import get_close_matches
import zipfile

st.title("MidJourney Image Renamer 📸➡️001,002… (Direct Upload)")

# --- Upload files ---
prompts_file = st.file_uploader("Upload your prompts.txt", type=["txt"])
uploaded_images = st.file_uploader("Upload your images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

# --- Use session state to prevent reruns ---
if "processed" not in st.session_state:
    st.session_state.processed = False

process = st.button("Process Images")

if process and prompts_file and uploaded_images and not st.session_state.processed:
    st.session_state.processed = True

    # --- Read prompts ---
    prompts = [line.strip().replace("___ar_16:9___v_6___style_raw", "") 
               for line in prompts_file.read().decode("utf-8").splitlines() if line.strip()]

    # --- Temp folder for images ---
    temp_dir = tempfile.mkdtemp()
    
    # Save uploaded images
    images = []
    for file in uploaded_images:
        file_path = os.path.join(temp_dir, file.name)
        with open(file_path, "wb") as f:
            f.write(file.read())
        images.append(file.name)

    # --- Map images by descriptive part ---
    image_map = {}
    for img in images:
        parts = img.split("_")
        desc_part = "_".join(parts[1:-2]).lower()  # remove prefix + UUID suffix
        image_map[desc_part] = img

    mapping_data = []

    # --- Rename images sequentially, skip missing ---
    for idx, prompt in enumerate(prompts, start=1):
        key = "_".join(prompt.split("_")[:10]).lower()
        match = get_close_matches(key, image_map.keys(), n=1, cutoff=0.1)
        
        if match:
            orig_name = image_map[match[0]]
            orig_path = os.path.join(temp_dir, orig_name)
            if os.path.exists(orig_path):
                new_name = f"{idx:03d}.png"
                os.rename(orig_path, os.path.join(temp_dir, new_name))
                mapping_data.append({
                    "Prompt_Number": idx,
                    "Prompt": prompt,
                    "Original_File": orig_name,
                    "New_File": new_name,
                    "Status": "Renamed"
                })
            else:
                mapping_data.append({
                    "Prompt_Number": idx,
                    "Prompt": prompt,
                    "Original_File": orig_name,
                    "New_File": "",
                    "Status": "Missing File"
                })
        else:
            mapping_data.append({
                "Prompt_Number": idx,
                "Prompt": prompt,
                "Original_File": "",
                "New_File": "",
                "Status": "Missing"
            })

    # --- Save mapping CSV ---
    mapping_df = pd.DataFrame(mapping_data)
    mapping_csv_path = os.path.join(temp_dir, "mapping.csv")
    mapping_df.to_csv(mapping_csv_path, index=False)

    # --- Zip renamed images + mapping ---
    zip_path = os.path.join(temp_dir, "renamed_images.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in os.listdir(temp_dir):
            zipf.write(os.path.join(temp_dir, file), arcname=file)

    st.success("✅ Images renamed successfully (missing images skipped)!")
    st.download_button("Download renamed images + mapping ZIP", zip_path)
    st.dataframe(mapping_df)
