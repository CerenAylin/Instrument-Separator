import customtkinter as ctk        
from tkinter import filedialog      
from demucs_separator import separate_audio   
import threading        
import os       
import pygame       
from audio_player import show_stem_selection_ui, show_audio_buttons, set_globals, audio_buttons 

# Set appearance mode and color theme for CustomTkinter
ctk.set_appearance_mode("dark")    
ctk.set_default_color_theme("blue")

app = ctk.CTk()     # Main application window
app.geometry("600x650")         
app.title("InstSep")     

icon_path = "assets/icon.ico"          # Add icon
if os.path.exists(icon_path):   
    app.iconbitmap(icon_path)           
else:
    print("❗ Icon file not found:", icon_path)     

# Global variables
selected_file = None
playing_audio = None
update_sliders = True
available_stems = []
selected_stems = [] 
stem_vars = {}
current_stem_selection_frame = None 
selected_stems_container = []  

# Audio buttons frame, will be dynamically filled after selecting audio file
audio_buttons_frame = ctk.CTkScrollableFrame(app, width=580, height=300) 

# Call set_globals function so other modules can access these global variables
def choose_file():
    global selected_file
    selected_file = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
    if selected_file:
        file_label.configure(text=os.path.basename(selected_file))
        set_globals(app, selected_file, selected_stems_container, status_label, audio_buttons_frame, current_stem_selection_frame_setter)

# Function to update progress bar
def update_progress(progress):  
    progress_bar.set(progress)

# Function to update the current stem selection frame
def current_stem_selection_frame_setter(frame): 
    global current_stem_selection_frame
    current_stem_selection_frame = frame

# Function to perform separation in a separate thread (so GUI doesn’t freeze)
def threaded_separation():  
    success, msg = separate_audio(selected_file, progress_callback=update_progress) 
    print(f"Separation success: {success}, message: {msg}") 
    status_label.configure(text=msg, text_color="green" if success else "red")  
    if success:
        show_stem_selection_ui(app, selected_file, stem_vars, selected_stems_container, show_audio_buttons, audio_buttons_frame, current_stem_selection_frame_setter)
    else:
        print("Separation failed, not showing stem selection")

def start_separation():
    global current_stem_selection_frame

    pygame.mixer.music.stop()  # Stop any playing audio
    
    if not selected_file:
        file_label.configure(text="No file selected!", text_color="red")
        return
    
    # If previous stem selection frame still exists, destroy it
    if current_stem_selection_frame and current_stem_selection_frame.winfo_exists():
        current_stem_selection_frame.destroy()
        current_stem_selection_frame = None 

    # Destroy all widgets inside the audio buttons frame
    for widget in audio_buttons_frame.winfo_children():
        widget.destroy()
    
    # Hide the audio buttons frame (to avoid taking space)
    audio_buttons_frame.pack_forget()

    # Clear global audio_buttons list from audio_player.py
    audio_buttons.clear()

    status_label.configure(text="Processing...", text_color="yellow")
    progress_bar.set(0)
    threading.Thread(target=threaded_separation, daemon=True).start()  # Start separation in a thread

pygame.mixer.init() # Initialize pygame audio module

# UI components
file_label = ctk.CTkLabel(app, text="Select an audio file", font=("Arial", 14))    
file_label.pack(pady=20)

select_button = ctk.CTkButton(app, text="Select File", command=choose_file)   
select_button.pack(pady=10)

start_button = ctk.CTkButton(app, text="Start Separation", command=start_separation)
start_button.pack(pady=20)

progress_bar = ctk.CTkProgressBar(app, width=400)
progress_bar.pack(pady=10)
progress_bar.set(0)

status_label = ctk.CTkLabel(app, text="")
status_label.pack(pady=10)

set_globals(app, selected_file, selected_stems_container, status_label, audio_buttons_frame, current_stem_selection_frame_setter) 

app.mainloop()
