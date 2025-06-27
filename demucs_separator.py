import subprocess
import os
import re
import torch

def separate_audio(input_path, progress_callback=None, output_path="outputs"):
    os.makedirs(output_path, exist_ok=True)

    if not input_path or not os.path.exists(input_path):
        return False, "Invalid or missing input file."

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INFO] Using device: {device}")

    process = subprocess.Popen(
        ["demucs", "-n", "htdemucs_ft", "-d", device, input_path, "-o", output_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8', 
        errors='replace'
    )

    # This function reads Demucs' terminal output and updates the progress percentage.
    progress_pattern = re.compile(r"(\d{1,3})%")

    for line in process.stdout:
        print(line.strip())  # Print terminal output to console
        match = progress_pattern.search(line)
        if match and progress_callback:
            percent = int(match.group(1))
            progress_callback(percent / 100.0)

    process.wait()

    if process.returncode == 0:
        return True, "Separation completed successfully."
    else:
        return False, "An error occurred during separation."
