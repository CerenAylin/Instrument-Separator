import os
import threading
import tkinter as tk
import customtkinter as ctk
import pygame
import time
import platform 

from utils import list_stems

# Global variables
playing_audio = None
audio_buttons = []
volume_values = {}
progress_values = {}
audio_lengths = {}
update_sliders = False
selected_file = None
app = None
status_label = None
selected_stems_container_ref = None
audio_buttons_frame_ref = None
set_current_stem_selection_frame_callback = None
current_playback_offset = 0.0 
current_output_folder_path = None

# Function to set global variables
def set_globals(app_instance, file, stems_container_param, status, audio_buttons_frame_param, stem_frame_setter_callback):  
    global app, selected_file, status_label, selected_stems_container_ref, audio_buttons_frame_ref, set_current_stem_selection_frame_callback
    app = app_instance
    selected_file = file
    selected_stems_container_ref = stems_container_param
    status_label = status
    audio_buttons_frame_ref = audio_buttons_frame_param
    set_current_stem_selection_frame_callback = stem_frame_setter_callback


def show_stem_selection_ui(app_instance, selected_file_param, stem_vars_param, selected_stems_container_param, show_audio_buttons_callback, audio_buttons_frame_param, stem_frame_setter_callback):
    if not selected_file_param:
        print("selected_file_param is None, can't show stem selection UI")
        return
    print("Entering show_stem_selection_ui")

    song_name = os.path.splitext(os.path.basename(selected_file_param))[0]

    available_stems = [
        os.path.basename(f).replace(".wav", "").capitalize()
        for f in list_stems("outputs", song_name)
    ]    
    print(f"Available stems: {available_stems}")

    stem_selection_frame = ctk.CTkFrame(app_instance)
    stem_selection_frame.pack(pady=10, padx=10, fill="x")

    stem_frame_setter_callback(stem_selection_frame) 

    ctk.CTkLabel(stem_selection_frame, text="Select Instruments:").pack(pady=5)

    stem_vars_param.clear() # Clear previous selections

    # New: Button to select all instruments
    def select_all(): 
        for var in stem_vars_param.values():
            var.set(True)

    select_all_button = ctk.CTkButton(stem_selection_frame, text="Select All", command=select_all) 
    select_all_button.pack(pady=2)

    for stem in available_stems: # Create a checkbox for each instrument
        var = tk.BooleanVar(value=True)
        checkbox = ctk.CTkCheckBox(stem_selection_frame, text=stem, variable=var)
        checkbox.pack(pady=2, padx=10, anchor="w")
        stem_vars_param[stem.lower()] = var
    
    # Apply instrument selections and delete unselected stems
    def apply_selection(): 
        global current_output_folder_path 
        print("Applying stem selection")
        
        selected_stems_container_param.clear() 
        selected_stems_container_param.extend([stem for stem, var in stem_vars_param.items() if var.get()])
        
        print(f"Selected stems (in container): {selected_stems_container_param}")

        song_name_for_deletion = os.path.splitext(os.path.basename(selected_file_param))[0] # Folder name where stems are stored
        output_base_dir = os.path.join("outputs", "htdemucs_ft", song_name_for_deletion) 
        current_output_folder_path = output_base_dir 

        all_stem_files_for_deletion = list_stems("outputs", song_name_for_deletion) # Get all stem files in folder
        
        deleted_count = 0 # Track number of deleted files
        for file_path in all_stem_files_for_deletion:
            stem_name_from_file = os.path.basename(file_path).replace(".wav", "").lower()
            if stem_name_from_file not in selected_stems_container_param:  
                try:
                    os.remove(file_path) # Delete unselected stem file
                    print(f"Deleted unselected stem file: {file_path}") 
                    deleted_count += 1
                except OSError as e:
                    print(f"Error deleting file {file_path}: {e}") 
        
        if status_label:
            if deleted_count > 0: 
                status_label.configure(text=f"{deleted_count} stem files deleted.", text_color="orange")  
            else:
                status_label.configure(text="All selected stems preserved.", text_color="green") 

        stem_selection_frame.destroy() # Destroy stem selection frame
        stem_frame_setter_callback(None) # Reset reference in main.py
        
        show_audio_buttons_callback(selected_stems_container_param, audio_buttons_frame_param) # Show audio buttons

    apply_button = ctk.CTkButton(stem_selection_frame, text="Apply", command=apply_selection) 
    apply_button.pack(pady=5)

# Play/pause audio function
def toggle_play(path, play_button): 
    global playing_audio, update_sliders, status_label, current_playback_offset 

    if playing_audio == path: # Same track clicked again (toggle play/pause)
        if pygame.mixer.music.get_busy(): 
            pygame.mixer.music.pause() 
            update_sliders = False  
            play_button.configure(text=f"▶️ Play: {os.path.basename(path).replace('.wav', '').capitalize()}") 
            print(f"Paused: {path}")
        else: # If paused, unpause
            pygame.mixer.music.unpause()
            update_sliders = True
            play_button.configure(text=f"⏸️ Stop: {os.path.basename(path).replace('.wav', '').capitalize()}") 
            print(f"Unpaused: {path}")
            threading.Thread(target=update_slider_progress, args=(path,), daemon=True).start()
    else: # Different track clicked or nothing playing
        if playing_audio: 
            pygame.mixer.music.stop()
            for btn, _, _, _ in audio_buttons:
                if btn.cget("text").startswith("⏸️ Stop:") or btn.cget("text").startswith("▶️ Play:"): 
                    stem_name_from_button = btn.cget("text").replace("⏸️ Stop: ", "").replace("▶️ Play: ", "").strip()
                    btn.configure(text=f"▶️ Play: {stem_name_from_button}") 
                    break
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume_values.get(path, 1.0))
            pygame.mixer.music.play()
            playing_audio = path
            update_sliders = True
            play_button.configure(text=f"⏸️ Stop: {os.path.basename(path).replace('.wav', '').capitalize()}") 
            audio_lengths[path] = pygame.mixer.Sound(path).get_length()
            
            current_playback_offset = 0.0 # Reset offset for new track
            
            update_time_label(path)
            threading.Thread(target=update_slider_progress, args=(path,), daemon=True).start()
            print(f"Started playing new track: {path}")

        except pygame.error as e:
            print(f"Error playing {path}: {e}")
            if status_label:
                status_label.configure(text=f"Error playing {os.path.basename(path)}", text_color="red")
            playing_audio = None
            update_sliders = False

# Function to open the output folder
def open_output_folder(): 
    global current_output_folder_path
    if current_output_folder_path and os.path.exists(current_output_folder_path):
        try:
            if platform.system() == "Windows":
                os.startfile(current_output_folder_path)
            elif platform.system() == "Darwin":
                os.system(f"open \"{current_output_folder_path}\"")
            else: 
                os.system(f"xdg-open \"{current_output_folder_path}\"")
            print(f"Opened folder: {current_output_folder_path}")
        except Exception as e:
            print(f"Error opening folder {current_output_folder_path}: {e}")
            if status_label:
                status_label.configure(text=f"Failed to open folder: {e}", text_color="red")
    else:
        print("Output folder path is not set or does not exist.")
        if status_label:
            status_label.configure(text="Output folder not found.", text_color="red")

# Function to create buttons for selected stems
def show_audio_buttons(selected_stems_param, target_frame):
    global audio_buttons, selected_file, app, current_output_folder_path
    
    print(f"Received selected_stems_param in show_audio_buttons: {selected_stems_param}")
    print(f"Received target_frame in show_audio_buttons: {target_frame}")

    if not selected_file:
        print("selected_file is None, can't show audio buttons")
        return
    
    print("Entering show_audio_buttons")
    song_name = os.path.splitext(os.path.basename(selected_file))[0]
    all_stem_files = list_stems("outputs", song_name)

    print(f"All stem files found by list_stems (after possible deletion): {all_stem_files}")

    for widget in target_frame.winfo_children():
        widget.destroy()
    audio_buttons.clear()

    target_frame.pack(pady=10, padx=10, fill="both", expand=True)

    header_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
    header_frame.pack(pady=(0, 10), fill="x") 

    open_folder_button = ctk.CTkButton(header_frame, text="📁 Open Folder", command=open_output_folder, width=120)
    open_folder_button.pack(side="right", padx=(5, 0))
    
    folder_label = ctk.CTkLabel(header_frame, text="Separated Stems Folder:", font=("Arial", 12) )
    folder_label.pack(side="right", padx=(0, 5))

    for f in all_stem_files:
        stem_name_with_ext = os.path.basename(f)
        stem_part = stem_name_with_ext.replace(".wav", "").lower()
        
        print(f"Processing file: {stem_name_with_ext}, extracted stem_part: {stem_part}")

        if stem_part in selected_stems_param:
            print(f"Creating buttons for stem: {stem_part}")
            name = stem_part.capitalize()
            
            play_button = ctk.CTkButton(target_frame, text=f"▶️ Play: {name}") 
            play_button.configure(command=lambda path=f, btn=play_button: toggle_play(path, btn))
            play_button.pack(pady=5)

            progress_slider = ctk.CTkSlider(target_frame, from_=0, to=100, command=lambda value, path=f: seek_audio(value, path))
            progress_slider.pack(pady=5)
            progress_values[f] = 0

            volume_control_frame = ctk.CTkFrame(target_frame, fg_color="transparent")
            volume_control_frame.pack(pady=0, padx=0, anchor="center") 

            volume_icon_label = ctk.CTkLabel(volume_control_frame, text="🔊", font=("Arial", 16))
            volume_icon_label.pack(side="left", padx=(0, 5))

            volume_slider = ctk.CTkSlider(volume_control_frame, from_=0, to=1, command=lambda value, path=f: set_volume(value, path), width=100)
            volume_slider.pack(side="left") 
            volume_values[f] = 1.0

            time_label = ctk.CTkLabel(target_frame, text="00:00 / 00:00")
            time_label.pack(pady=5)

            audio_buttons.append((play_button, volume_slider, progress_slider, time_label))
        else:
            print(f"Stem '{stem_part}' not in selected stems param, skipping button creation.")

    print("Exiting show_audio_buttons")

# Seek audio (fast forward/rewind)
def seek_audio(value, path): 
    global playing_audio, update_sliders, status_label, current_playback_offset
    if playing_audio == path:
        total_length = audio_lengths.get(path, 0)
        if total_length > 0:
            seek_time = (value / 100.0) * total_length
            try:
                pygame.mixer.music.set_pos(seek_time)
                current_playback_offset = seek_time # Update offset
                print(f"Seeking {path} to {seek_time:.2f} seconds. New offset: {current_playback_offset:.2f}")
                
                # Update only time label and progress bar, do not change play state
                update_time_label(path) 
            except pygame.error as e:
                print(f"Error seeking {path}: {e}")
                if status_label:
                    status_label.configure(text=f"Error seeking {os.path.basename(path)}", text_color="red")
    progress_values[path] = value / 100.0

# Update slider progress bar
def update_slider_progress(path): 
    global update_sliders, playing_audio, current_playback_offset
    while playing_audio == path and update_sliders:
        
        if not pygame.mixer.music.get_busy() and pygame.mixer.music.get_pos() == -1: # Music finished?
            print(f"Music finished for {path}")
            for btn, vol_slider, prog_slider, label in audio_buttons:
                if btn.cget("text").startswith("⏸️ Stop:") and os.path.basename(path).replace(".wav", "").capitalize() in btn.cget("text"): 
                    btn.configure(text=f"▶️ Play: {os.path.basename(path).replace('.wav', '').capitalize()}") 
                    prog_slider.set(0)
                    label.configure(text="00:00 / " + format_time(audio_lengths.get(path, 0)))
                    break
            playing_audio = None
            update_sliders = False
            current_playback_offset = 0.0
            return

        if pygame.mixer.music.get_busy():
            current_time = (pygame.mixer.music.get_pos() / 1000.0) + current_playback_offset
            total_length = audio_lengths.get(path, 0)
            if total_length > 0:
                update_time_label(path)
        time.sleep(0.1)

# Update time label function
def update_time_label(path):
    global current_playback_offset
    song_name = os.path.splitext(os.path.basename(selected_file))[0]
    file_base_stem = os.path.basename(path).replace(".wav", "").capitalize()

    for btn, vol_slider, prog_slider, label in audio_buttons:
        button_stem_text = btn.cget("text").replace("▶️ Play: ", "").replace("⏸️ Stop: ", "").strip()
        
        if button_stem_text == file_base_stem:
            total_length = audio_lengths.get(path, 0)
            
            current_time = (pygame.mixer.music.get_pos() / 1000.0) + current_playback_offset if playing_audio == path else current_playback_offset 
            
            if current_time > total_length:
                current_time = total_length

            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            total_minutes = int(total_length // 60)
            total_seconds = int(total_length % 60)
            label.configure(text=f"{minutes:02d}:{seconds:02d} / {total_minutes:02d}:{total_seconds:02d}")
            
            if total_length > 0:
                progress = (current_time / total_length) * 100
                prog_slider.set(progress)
            break

# Format time helper function
def format_time(seconds):
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

# Set volume function
def set_volume(value, path):
    global volume_values
    volume_values[path] = value
    pygame.mixer.music.set_volume(value)
    print(f"Volume set to {value} for {path}")
