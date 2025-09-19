import streamlit as st
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
import os
import tempfile
import zipfile
import io

def parse_prompts(uploaded_file: io.TextIOWrapper) -> List[Tuple[Optional[str], str]]:
    """
    Parses an uploaded text file to extract prompts and optional image URLs.
    Handles multi-line prompts and URL references.
    
    Args:
        uploaded_file: An uploaded file object from st.file_uploader.
    
    Returns:
        A list of tuples, where each tuple contains an optional image URL (str) and
        the corresponding prompt text (str).
    """
    lines = uploaded_file.getvalue().decode("utf-8").splitlines()
    
    prompts = []
    buffer = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for a new prompt starting with a number
        match = re.match(r'^(\d+)(.+)', line)
        if match:
            if buffer: 
                prompts.append(buffer.strip())
            buffer = match.group(2).strip()
            buffer = match.group(1) + " " + buffer  # Keep number with prompt
        elif re.match(r'^https?://', line):
            # If the line is a URL, glue it to the current buffer
            buffer += " " + line.strip()
        else:
            # If the line is a continuation of the previous prompt
            buffer += " " + line.strip()
            
    if buffer:
        prompts.append(buffer.strip())

    cleaned_prompts = []
    for prompt in prompts:
        m = re.match(r'(https?://\S+\.png)(.*)', prompt)
        if m:
            cleaned_prompts.append((m.group(1).strip(), m.group(2).strip()))
        else:
            cleaned_prompts.append((None, prompt))
    
    st.info(f"Loaded {len(cleaned_prompts)} prompts.")
    return cleaned_prompts

def find_image_files(images_dir: Path, prefix: str, ext: str) -> Dict[str, Path]:
    """
    Scans a directory for image files that match a specific prefix and extension.
    
    Args:
        images_dir (Path): The path to the directory containing images.
        prefix (str): The required filename prefix.
        ext (str): The required filename extension.
        
    Returns:
        dict: A dictionary mapping the cleaned filename stem to its full Path object.
    """
    files = {}
    if not images_dir.is_dir():
        st.error(f"ERROR: Images directory '{images_dir}' not found.")
        return files
        
    for fpath in images_dir.glob(f"{prefix}*{ext}"):
        stem = fpath.stem.lower()
        files[stem] = fpath
            
    st.info(f"Found {len(files)} images with prefix '{prefix}' and extension '{ext}'.")
    return files

def map_prompts_to_images(prompts: List[Tuple[Optional[str], str]], files: Dict[str, Path], prefix: str) -> Tuple[List, Set[Path], List]:
    """
    Maps prompts to image files using a multi-tiered matching strategy.
    
    Args:
        prompts (list): A list of tuples containing (url, prompt_text).
        files (dict): A dictionary of available image files.
        prefix (str): The filename prefix to consider for numeric matching.
        
    Returns:
        tuple: A tuple containing the mapping list, a set of unused file paths, and a list of missing prompts.
    """
    used_stems = set()
    mapping = []
    missing_prompts = []
    
    seq = 1
    width = max(3, len(str(len(prompts))))
    
    # Create a copy of available files to modify during the process
    available_files = {stem: fname for stem, fname in files.items()}

    for img_url, prompt in prompts:
        target_name = f"{str(seq).zfill(width)}.png"
        found_file = None

        # Strategy 1: Numeric ID Matching
        # This is the most reliable strategy.
        prompt_num_match = re.match(r'^(\d+)', prompt)
        if prompt_num_match:
            prompt_num = prompt_num_match.group(1)
            img_stem_to_find = f"{prefix.lower()}{prompt_num}"
            if img_stem_to_find in available_files:
                found_file = available_files.pop(img_stem_to_find)
        
        # Strategy 2: URL Stem Matching
        # Used if Strategy 1 fails and a URL is present.
        if not found_file and img_url:
            url_stem = Path(img_url).stem.lower()
            # Find the full stem from the available files dictionary
            full_url_stem = next((stem for stem in available_files if url_stem in stem), None)
            if full_url_stem:
                found_file = available_files.pop(full_url_stem)

        # Strategy 3: Fuzzy Substring Matching (fallback)
        # Used if both of the above fail.
        if not found_file:
            for stem, fname in list(available_files.items()):
                if (stem in prompt.lower() or prompt.lower() in stem) and stem not in used_stems:
                    found_file = available_files.pop(stem)
                    break

        if found_file:
            mapping.append((target_name, found_file, prompt))
            used_stems.add(Path(found_file).stem.lower())
        else:
            mapping.append(('(missing)', None, prompt))
            missing_prompts.append(prompt)
        seq += 1
        
    st.info(f"Mapped {len(mapping) - len(missing_prompts)} prompts to images, with {len(missing_prompts)} missing.")
    unused_files = set(files.values()) - set(used_stems)
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
            with st.spinner("Reading prompts..."):
                prompts = parse_prompts(prompts_file)
            
            with st.spinner("Scanning for images..."):
                image_files_on_disk = find_image_files(temp_images_dir, prefix, ext)
            if not image_files_on_disk:
                st.error("No images found with the specified prefix and extension.")
                raise FileNotFoundError
                
            with st.spinner("Mapping prompts to images..."):
                mapping, unused_files, missing_prompts = map_prompts_to_images(prompts, image_files_on_disk, prefix)
            
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
