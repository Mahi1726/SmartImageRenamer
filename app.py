import streamlit as st
import cv2
import os
import tempfile
import zipfile
import shutil
import difflib
from skimage.metrics import structural_similarity as ssim
import numpy as np

# --- Helper: fuzzy match between filename and prompt ---
def fuzzy_match(target, candidates, cutoff=0.6):
    """Return the best fuzzy match for target among candidates."""
    best_match = None
    best_score = 0.0
    for cand in candidates:
        score = difflib.SequenceMatcher(None, target.lower(), cand.lower()).ratio()
        if score > best_score and score >= cutoff:
            best_score = score
            best_match = cand
    return best_match, best_score


# --- Streamlit UI ---
st.title("🎥 SmartVideoRenamer with Fuzzy Matching")
st.write("Upload reference images and videos. The app will rename videos by matching their first frame to the most similar image. Now with **fuzzy filename matching** so small text differences won’t break things!")

image_files = st.file_uploader("Upload reference images (.png)", type=["png"], accept_multiple_files=True)
video_files = st.file_uploader("Upload videos (.mp4)", type=["mp4"], accept_multiple_files=True)

if image_files and video_files:
    if st.button("🚀 Process and Rename Videos"):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = os.path.join(tmpdir, "images")
            video_dir = os.path.join(tmpdir, "videos")
            os.makedirs(image_dir, exist_ok=True)
            os.makedirs(video_dir, exist_ok=True)

            # Save uploaded images
            for file in image_files:
                with open(os.path.join(image_dir, file.name), "wb") as f:
                    f.write(file.read())

            # Save uploaded videos
            for file in video_files:
                with open(os.path.join(video_dir, file.name), "wb") as f:
                    f.write(file.read())

            # Load images
            images = {}
            for fname in os.listdir(image_dir):
                if fname.endswith(".png"):
                    img = cv2.imread(os.path.join(image_dir, fname))
                    img = cv2.resize(img, (256, 256))
                    images[fname] = img

            renamed = []
            skipped = []

            # Process videos
            for vfile in os.listdir(video_dir):
                if not vfile.endswith(".mp4"):
                    continue
                vpath = os.path.join(video_dir, vfile)
                cap = cv2.VideoCapture(vpath)
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    skipped.append(vfile)
                    continue

                frame = cv2.resize(frame, (256, 256))

                best_match = None
                best_score = -1

                for img_name, img in images.items():
                    grayA = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    grayB = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    score, _ = ssim(grayA, grayB, full=True)
                    if score > best_score:
                        best_score = score
                        best_match = img_name

                if best_match:
                    # Fuzzy match filename to prompt name (ignoring suffixes)
                    prompt_base = os.path.splitext(best_match)[0]
                    new_name, text_score = fuzzy_match(prompt_base, [os.path.splitext(vfile)[0]])
                    if not new_name:  # fallback: just use image filename
                        new_name = prompt_base
                    final_name = new_name + ".mp4"

                    new_path = os.path.join(video_dir, final_name)
                    os.rename(vpath, new_path)
                    renamed.append(f"{vfile} → {final_name} (ssim={best_score:.2f}, text={text_score:.2f})")

            # Zip renamed videos
            zip_path = os.path.join(tmpdir, "renamed_videos.zip")
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for vfile in os.listdir(video_dir):
                    zipf.write(os.path.join(video_dir, vfile), vfile)

            st.success("✅ Processing complete!")
            st.download_button("⬇️ Download Renamed Videos (ZIP)", data=open(zip_path, "rb"), file_name="renamed_videos.zip")

            if renamed:
                st.subheader("Renamed Files")
                for line in renamed:
                    st.text(line)
            if skipped:
                st.subheader("Skipped Videos")
                for s in skipped:
                    st.text(s)
