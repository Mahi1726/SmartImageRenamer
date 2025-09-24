import streamlit as st
import os
import shutil

st.title("Image Renamer with Prompts")

# Input folder path
image_folder = st.text_input("Enter path to image folder", "")

# Upload prompts file
prompts_file = st.file_uploader("Upload prompts.txt or mapping file", type=["txt"])

if st.button("Rename Images"):
    if not image_folder or not prompts_file:
        st.error("Please provide both the image folder and the prompts file.")
    else:
        # Read prompts
        prompts = prompts_file.read().decode("utf-8").splitlines()
        prompt_dict = {}
        for line in prompts:
            parts = line.split("|")
            if len(parts) >= 2:
                prompt_dict[parts[1].strip()] = parts[2].strip() if len(parts) > 2 else parts[1].strip()

        # Get all images in folder
        images = [f for f in os.listdir(image_folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
        images.sort()  # Initial order

        renamed_folder = os.path.join(image_folder, "renamed")
        os.makedirs(renamed_folder, exist_ok=True)

        used_prompts = set()
        count = 1

        for img in images:
            matched_prompt = None
            for prompt_name, prompt_text in prompt_dict.items():
                img_base = os.path.splitext(img)[0]
                prompt_base = "_".join(prompt_name.split("_")[:5])
                if prompt_base in img_base and prompt_name not in used_prompts:
                    matched_prompt = prompt_name
                    used_prompts.add(prompt_name)
                    break

            if matched_prompt:
                new_name = f"{count:03}.png"
                shutil.copy(os.path.join(image_folder, img), os.path.join(renamed_folder, new_name))
                st.write(f"{img} ➔ {new_name}")
                count += 1
            else:
                st.warning(f"No match found for {img}")

        st.success(f"Renaming done! Renamed images are in {renamed_folder}")
