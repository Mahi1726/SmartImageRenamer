import streamlit as st
import re
import shutil
from pathlib import Path
from collections import defaultdict
from typing import List, Tuple, Dict, Optional, Set
import os

def parse_prompts(prompts_path: Path) -> List[Tuple[Optional[str], str]]:
    """
    Parses a text file to extract prompts and optional image URLs.

    Args:
        prompts_path: Path to the prompts file.

    Returns:
        A list of tuples, where each tuple contains an optional URL (str)
        and the prompt text (str).
    """
    prompts = []
    current_prompt = ""
    try:
        with open(prompts_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        st.error(f"ERROR: Prompts file '{prompts_path}' not found.")
        return []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        url_match = re.match(r'^(https?://\S+\.png)', line)
        num_match = re.match(r'^(\d+)', line)

        if url_match or num_match:
            # New prompt starts with a number or a URL
            if current_prompt:
                prompts.append(current_prompt.strip())
            current_prompt = line
        else:
            # Continuation of the previous prompt
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
    Finds image files matching a prefix and extension in a directory.

    Args:
        images_dir: Path to the directory containing images.
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

def organize_and_rename(prompts_path: Path, images_dir: Path, output_dir: Path,
                        prefix: str, ext: str, move: bool, dry_run: bool):
    """
    Main function to orchestrate the entire process via a Streamlit UI.
    """
    st.info(f"Reading prompts from '{prompts_path}'...")
    prompts = parse_prompts(prompts_path)
    if not prompts:
        return

    st.info(f"Scanning for images in '{images_dir}'...")
    image_files = find_image_files(images_dir, prefix, ext)
    if not image_files:
        return

    st.info("Mapping prompts to images...")
    mapping, unused_files, missing_prompts = map_prompts_to_images(prompts, image_files)

    if dry_run:
        st.warning("\n--- Dry Run: No files will be modified. ---")
    else:
        st.info(f"Creating output directory '{output_dir}'...")
        output_dir.mkdir(parents=True, exist_ok=True)

    st.info("Processing files...")
    progress_bar = st.progress(0)
    
    report_path = output_dir / "report.txt"
    with open(report_path, "w", encoding="utf-8") as report:
        report.write("### Image Renaming and Organization Report ###\n\n")
        
        # Section 1: Successful Matches
        report.write("--- Successfully Mapped Prompts ---\n")
        processed_count = 0
        total_items = len(mapping)
        
        for i, (target_name, found_path, prompt) in enumerate(mapping):
            progress_bar.progress((i + 1) / total_items)
            if found_path:
                src = found_path
                dst = output_dir / target_name
                
                if not dry_run:
                    if move:
                        shutil.move(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                report.write(f"PROCESSED: {src.name} -> {dst.name}\nPrompt: {prompt}\n\n")
                processed_count += 1
            else:
                report.write(f"MISSED:    (No match for '{prompt}')\n\n")
                
        # Section 2: Unused Files
        report.write("\n--- Unused Image Files ---\n")
        if unused_files:
            for fpath in unused_files:
                report.write(f"UNUSED:    {fpath.name}\n")
        else:
            report.write("No unused image files found.\n")
            
        # Section 3: Missing Prompts
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
    st.write(f"Detailed report saved to: `{report_path}`")
    
    if dry_run:
        st.warning("Note: This was a dry run. No files were actually changed.")

st.title("Image Organizer & Renamer")
st.markdown("Use this app to organize and rename your images based on a list of prompts. "
            "It is a web-based version of the command-line tool I created for you.")
st.markdown("---")

st.header("1. Setup")
st.info("Before running, make sure you have the following in the same directory as this script:")
st.markdown("- A text file containing your prompts (e.g., `prompts.txt`).")
st.markdown("- A folder with the images you want to organize (e.g., `images/`).")
st.markdown("The script will create a new folder for the output.")

st.header("2. Configure Options")
prompts_path = st.text_input("Prompts file path:", "prompts.txt")
images_dir = st.text_input("Source images directory:", "images")
output_dir = st.text_input("Output directory:", "output")

col1, col2 = st.columns(2)
with col1:
    prefix = st.text_input("Image filename prefix:", "asif4876_")
with col2:
    ext = st.text_input("Image filename extension:", ".png")

st.markdown("---")
st.header("3. Run the Process")
st.subheader("Action")
move_files = st.checkbox("Move files instead of copying them", help="If unchecked, files are copied, leaving the originals in place.")
dry_run = st.checkbox("Dry Run", help="Simulate the process without modifying any files. A detailed report will still be generated.")

if st.button("Run Image Organizer"):
    st.markdown("---")
    st.header("4. Results")
    try:
        organize_and_rename(Path(prompts_path), Path(images_dir), Path(output_dir), 
                            prefix, ext, move_files, dry_run)
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
