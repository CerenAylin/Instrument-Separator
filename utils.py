import os

# List separated instrument (stem) files
def list_stems(output_dir, song_name): 
    stems_path = os.path.join(output_dir, "htdemucs_ft", song_name)
    files = [f for f in os.listdir(stems_path) if f.endswith(".wav")]
    return [os.path.join(stems_path, f) for f in files]
