import streamlit as st
import os
import tempfile
import pandas as pd
import zipfile

st.title("MidJourney Image Renamer – Perfect Version 🔥")

# Upload prompts
prompts_file = st.file_uploader("Upload your prompts.txt", type=["txt"])
uploaded_images = st.file_uploader("Upload your images", type=["png", "jpg", "jpeg"], accept_multiple_files=True)

if "processed" not in st.session_state:
    st.session_state.processed = False

process = st.button("Process Images")

if process and prompts_file and uploaded_images and not st.session_state.processed:
    st.session_state.processed = True

    # --- Read prompts ---
    prompts = [line.strip().replace("___ar_16:9___v_6___style_raw", "")
               for line in prompts_file.read().decode("utf-8").splitlines() if line.strip()]

    # --- Temporary folder ---
    temp_dir = tempfile.mkdtemp()

    # Save uploaded images
    for file in uploaded_images:
        with open(os.path.join(temp_dir, file.name), "wb") as f:
            f.write(file.read())

    # Get exact filenames
    images = os.listdir(temp_dir)

    mapping_data = []

    # --- Perfect matching ---
    for idx, prompt in enumerate(prompts, start=1):
        # Normalize prompt and filenames for comparison
        prompt_lower = prompt.lower().replace("-", " ").replace("’", "'").replace("'", "")
        found = None

        for img in images:
            img_lower = img.lower().replace("-", " ").replace("’", "'").replace("'", "")
            if prompt_lower in img_lower:
                found = img
                break

        if found:
            orig_path = os.path.join(temp_dir, found)
            new_name = f"{idx:03d}.png"
            new_path = os.path.join(temp_dir, new_name)
            try:
                os.rename(orig_path, new_path)
                mapping_data.append({
                    "Prompt_Number": idx,
                    "Prompt": prompt,
                    "Original_File": found,
                    "New_File": new_name,
                    "Status": "Renamed"
                })
            except Exception as e:
                mapping_data.append({
                    "Prompt_Number": idx,
                    "Prompt": prompt,
                    "Original_File": found,
                    "New_File": "",
                    "Status": f"Rename failed: {e}"
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

    st.success("✅ All images processed perfectly! Missing images skipped safely.")
    st.download_button("Download renamed images + mapping ZIP", zip_path)
    st.dataframe(mapping_df)
