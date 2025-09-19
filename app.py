import streamlit as st
import re
import shutil
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Optional, Set
import os
import tempfile
import zipfile
import io

def parse_prompts(uploaded_file: io.TextIOWrapper) -> List[Tuple[Optional[str], str]]:
    """
    Parses an uploaded text file to extract prompts and optional image URLs.

    Args:
        uploaded_file: An uploaded file object from st.file_uploader.

    Returns:
        A list of tuples, where each tuple contains an optional URL (str)
        and the prompt text (str).
    """
    prompts = []
    current_prompt = ""
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        url_match = re.match(r'^(https?://\S+\.png)', line)
        num_match = re.match(r'^(\d+)', line)

        if url_match or num_match:
            if current_prompt:
                prompts.append(current_prompt.strip())
            current_prompt = line
        else:
            current_prompt += " " + line

    if current_prompt:
        prompts.append(current_prompt.strip())

    cleaned_prompts = []
    for prompt in prompts:
        m = re.match(r'(https?://\S+\.png)(.*)', prompt)
        if m:
            cleaned_prompts.append((m.group(1).strip(), m.group(2).strip()))
        else:
            cleaned_prompts.append((None, prompt))

    return cleaned_prompts

def find_image_files(images_dir: Path, prefix: str, ext: str) -> Dict[str, Path]:
    """
    Finds image files matching a prefix and extension in a temporary directory.

    Args:
        images_dir: Path to the temporary directory containing images.
        prefix: The required filename prefix.
        ext: The required filename extension.

    Returns:
        A dictionary mapping the cleaned filename stem (without prefix/ext) to its full Path object.
    """
    files = {}
    if not images_dir.is_dir():
        st.error(f"ERROR: Images directory '{images_dir}' not found.")
        return files

    for fpath in images_dir.glob(f"{prefix}*{ext}"):
        stem = fpath.stem[len(prefix):].lower()
        files[stem] = fpath

    return files

def map_prompts_to_images(prompts: List[Tuple[Optional[str], str]], files: Dict[str, Path]) -> Tuple[List, Set[Path], List]:
    """
    Maps prompts to image files using a defined matching strategy.

    Args:
        prompts: A list of prompts and optional URLs.
        files: A dictionary of available image files.

    Returns:
        A tuple containing:
        - A list of mapped tuples: (target_name, source_path, prompt)
        - A set of paths for images that were not used.
        - A list of prompts that could not be matched.
    """
    used_files: Set[Path] = set()
    mapping: List[Tuple[str, Optional[Path], str]] = []
    missing_prompts: List[str] = []
    
    available_files = {stem: p for stem, p in files.items()}
    
    seq_width = max(3, len(str(len(prompts))))
    
    for i, (img_url, prompt) in enumerate(prompts):
        target_name = f"{str(i + 1).zfill(seq_width)}.png"
        found_path = None
        
        # Strategy 1: Numeric ID matching
        num_match = re.search(r'\b(\d+)\b', prompt)
        if num_match:
            prompt_num = num_match.group(1)
            if prompt_num in available_files:
                found_path = available_files.pop(prompt_num)
                
        # Strategy 2: URL Stem matching
        if not found_path and img_url:
            url_stem = Path(img_url).stem.lower()
            if url_stem in available_files:
                found_path = available_files.pop(url_stem)

        if found_path:
            mapping.append((target_name, found_path, prompt))
            used_files.add(found_path)
        else:
            mapping.append((target_name, None, prompt))
            missing_prompts.append(prompt)

    unused_files = set(files.values()) - used_files
    
    return mapping, unused_files, missing_prompts

def create_zip_archive(output_dir: Path) -> bytes:
    """
    Creates a zip archive of the files in the output directory.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in output_dir.iterdir():
            zipf.write(file, arcname=file.name)
    return buffer.getvalue()

def delete_temp_files(temp_dirs: List[Path]):
    """
    Deletes the specified temporary directories.
    """
    for d in temp_dirs:
        if d.is_dir():
            shutil.rmtree(d)
    st.session_state.temp_dirs = []
    st.success("Temporary files have been deleted.")

# Initialize session state for temporary directories
if 'temp_dirs' not in st.session_state:
    st.session_state.temp_dirs = []
    
st.title("Image Organizer & Renamer")
st.markdown("Use this app to organize and rename your images based on a list of prompts.")
st.markdown("---")

st.header("1. Upload Files")
prompts_file = st.file_uploader("Upload Prompts File (e.g., prompts.txt)", type=['txt'])
image_files = st.file_uploader("Upload Images (PNG files)", type=['png'], accept_multiple_files=True)

col1, col2 = st.columns(2)
with col1:
    prefix = st.text_input("Image filename prefix:", "asif4876_")
with col2:
    ext = st.text_input("Image filename extension:", ".png")

st.markdown("---")
st.header("2. Run the Process")
st.subheader("Action")
move_files = st.checkbox("Move files instead of copying them", help="If unchecked, files are copied, leaving the originals in place.")
dry_run = st.checkbox("Dry Run", help="Simulate the process without modifying any files.")

if st.button("Run Image Organizer"):
    st.markdown("---")
    st.header("3. Results")
    if not prompts_file or not image_files:
        st.error("Please upload both a prompts file and at least one image file to continue.")
    else:
        try:
            # Create temporary directories for processing
            temp_images_dir = Path(tempfile.mkdtemp())
            temp_output_dir = Path(tempfile.mkdtemp())
            st.session_state.temp_dirs.extend([temp_images_dir, temp_output_dir])

            # Save uploaded files to the temporary directory
            for uploaded_file in image_files:
                with open(temp_images_dir / uploaded_file.name, "wb") as f:
                    f.write(uploaded_file.getbuffer())

            # Perform the organization and renaming
            st.info("Reading prompts...")
            prompts = parse_prompts(prompts_file)
            
            st.info("Scanning for images...")
            image_files_on_disk = find_image_files(temp_images_dir, prefix, ext)
            if not image_files_on_disk:
                st.error("No images found with the specified prefix and extension.")
                raise FileNotFoundError
                
            st.info("Mapping prompts to images...")
            mapping, unused_files, missing_prompts = map_prompts_to_images(prompts, image_files_on_disk)
            
            if dry_run:
                st.warning("--- Dry Run: No files will be moved or copied. ---")
            
            st.info("Processing files...")
            progress_bar = st.progress(0)
            processed_count = 0
            total_items = len(mapping)

            with open(temp_output_dir / "report.txt", "w", encoding="utf-8") as report:
                report.write("### Image Renaming and Organization Report ###\n\n")
                report.write("--- Successfully Mapped Prompts ---\n")
                
                for i, (target_name, found_path, prompt) in enumerate(mapping):
                    progress_bar.progress((i + 1) / total_items)
                    if found_path:
                        src = found_path
                        dst = temp_output_dir / target_name
                        
                        if not dry_run:
                            if move_files:
                                shutil.move(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        
                        report.write(f"PROCESSED: {src.name} -> {dst.name}\nPrompt: {prompt}\n\n")
                        processed_count += 1
                    else:
                        report.write(f"MISSED:    (No match for '{prompt}')\n\n")
                
                report.write("\n--- Unused Image Files ---\n")
                if unused_files:
                    for fpath in unused_files:
                        report.write(f"UNUSED:    {fpath.name}\n")
                else:
                    report.write("No unused image files found.\n")
                    
                report.write("\n--- Missing Prompts (No Image Match Found) ---\n")
                if missing_prompts:
                    for prompt in missing_prompts:
                        report.write(f"MISSING:   {prompt}\n")
                else:
                    report.write("All prompts were matched with an image.\n")

            st.success("--- Summary ---")
            st.write(f"Total prompts processed: **{len(prompts)}**")
            st.write(f"Successfully mapped images: **{processed_count}**")
            st.write(f"Missing prompts: **{len(missing_prompts)}**")
            st.write(f"Unused images: **{len(unused_files)}**")
            
            if not dry_run:
                zip_data = create_zip_archive(temp_output_dir)
                st.download_button(
                    label="Download Organized Images & Report",
                    data=zip_data,
                    file_name="organized_images.zip",
                    mime="application/zip"
                )
            
            if dry_run:
                st.warning("Note: This was a dry run. No files were actually changed.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

st.markdown("---")
if st.button("Delete Temporary Files"):
    if st.session_state.temp_dirs:
        delete_temp_files(st.session_state.temp_dirs)
    else:
        st.info("No temporary files to delete.")
