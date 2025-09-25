import streamlit as st
import tempfile
import shutil
import os

st.title("Midjourney Image-Prompt Renamer")

prompt_file = st.file_uploader("Upload prompts.txt", type=["txt"])
image_files = st.file_uploader("Upload PNG images", type=["png"], accept_multiple_files=True)

if prompt_file and image_files:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Load and process prompts
        prompts = [line.strip() for line in prompt_file if line.strip()]
        prompts = [p.decode("utf-8") if isinstance(p, bytes) else p for p in prompts]

        # Save images to temp directory for reference
        image_dir = os.path.join(tmpdir, "input_images")
        os.makedirs(image_dir, exist_ok=True)
        for file in image_files:
            filepath = os.path.join(image_dir, file.name)
            with open(filepath, "wb") as f_out:
                f_out.write(file.getbuffer())

        png_files = os.listdir(image_dir)
        output_dir = os.path.join(tmpdir, "output_images")
        os.makedirs(output_dir, exist_ok=True)

        mapping_log = []
        used_imgs = set()
        # Core image-prompt mapping logic
        for idx, prompt in enumerate(prompts, 1):
            sanitized = "_".join(prompt.lower().replace(",", "")
                                                 .replace("-", "")
                                                 .replace("’", "")
                                                 .replace("'", "")
                                                 .replace(".", "")
                                                 .replace(":", "")
                                                 .replace("“", "")
                                                 .replace("”", "")
                                                 .split())
            match = None
            for img in png_files:
                if sanitized in img.lower() and img not in used_imgs:
                    match = img
                    break
            if match:
                new_name = f"{idx:03}.png"
                shutil.copy(os.path.join(image_dir, match), os.path.join(output_dir, new_name))
                mapping_log.append(f"{match} -> {new_name} | {prompt}")
                used_imgs.add(match)
            else:
                mapping_log.append(f"SKIPPED | {prompt}")

        # Zip outputs
        out_zip = os.path.join(tmpdir, "renamed_images.zip")
        import zipfile
        with zipfile.ZipFile(out_zip, "w") as zipf:
            for fname in os.listdir(output_dir):
                zipf.write(os.path.join(output_dir, fname), arcname=fname)

        # Downloadables
        log_txt = "\n".join(mapping_log)
        st.download_button("Download Renamed Images ZIP", open(out_zip, "rb"), "renamed_images.zip")
        st.download_button("Download Mapping Log", log_txt, "mapping_log.txt")
        st.success("Done! Outputs ready for download.")

