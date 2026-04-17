import os
import sys
import urllib3

# --- SILENCE SSL WARNINGS ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- DIRECTORY OVERRIDE (VSCode Independence) ---
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

import customtkinter as ctk
import socketio
import threading
import subprocess
import time
from PIL import Image
import io
import base64

# --- SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("1280x720")
app.title("UNIT 1: INCUBATOR")

# --- SUBPROCESS MANAGEMENT & PIPING ---
core_process = None
consol_proc = None

def read_subprocess_output(process, name):
    for line in iter(process.stdout.readline, ''):
        if line:
            app.after(0, log_textbox.insert, "end", line)
            app.after(0, log_textbox.see, "end")
            
    process.stdout.close()
    return_code = process.wait()
    
    if return_code == 0:
        status_msg = f"[SYSTEM] {name} safely and successfully powered down.\n"
    else:
        status_msg = f"[CRITICAL WARNING] {name} terminated abruptly! (Exit Code: {return_code})\n"
        
    app.after(0, log_textbox.insert, "end", status_msg)
    app.after(0, log_textbox.see, "end")

def boot_unit_1():
    global core_process
    if core_process is None or core_process.poll() is not None:
        log_textbox.insert("end", "\n[SYSTEM] Booting Unit 1 Brain...\n")
        log_textbox.see("end")
        core_process = subprocess.Popen(
            [sys.executable, '-u', 'selfAwareness-v1.py'], 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=script_dir
        )
        threading.Thread(target=read_subprocess_output, args=(core_process, "Mind 1 (Core)"), daemon=True).start()
    else:
        log_textbox.insert("end", "[SYSTEM] Unit 1 is already running!\n")
        log_textbox.see("end")

def shutdown_unit_1():
    if sio.connected:
        log_textbox.insert("end", "\n[SYSTEM] Sending Shutdown Command to Core...\n")
        log_textbox.see("end")
        sio.emit('force_sleep')
    else:
        log_textbox.insert("end", "\n[ERROR] Cannot shut down. Telemetry link is offline!\n")
        log_textbox.see("end")

def run_consolidator_independent():
    global consol_proc
    log_textbox.insert("end", "\n[SYSTEM] Launching Mind 6 (Consolidator)...\n")
    log_textbox.see("end")
    consol_proc = subprocess.Popen(
        [sys.executable, '-u', 'dreamMachine-v1.py'], 
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=script_dir
    )
    threading.Thread(target=read_subprocess_output, args=(consol_proc, "Mind 6 (Consolidator)"), daemon=True).start()

def trigger_rem_sleep():
    global consol_proc
    if sio.connected:
        log_textbox.insert("end", "\n[SYSTEM] Queuing Sleep & Consolidator sequence...\n")
        log_textbox.see("end")
        sio.emit('force_sleep')
        
        def wait_and_consolidate():
            if core_process:
                core_process.wait()
            app.after(0, log_textbox.insert, "end", "\n[SYSTEM] Core Offline. Triggering REM Sleep...\n")
            app.after(0, log_textbox.see, "end")
            consol_proc = subprocess.Popen(
                [sys.executable, '-u', 'dreamMachine-v1.py'], 
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=script_dir
            )
            read_subprocess_output(consol_proc, "Mind 6 (Consolidator)")
            
        threading.Thread(target=wait_and_consolidate, daemon=True).start()
    else:
        log_textbox.insert("end", "\n[ERROR] Cannot sleep. Telemetry link is offline!\n")
        log_textbox.see("end")

# --- DEAD MAN'S SWITCH (ZOMBIE PREVENTION) ---
def on_closing():
    print("[INCUBATOR] Close signal detected. Engaging Dead Man's Switch...")
    if sio.connected:
        try:
            sio.emit('force_sleep')
            sio.disconnect()
        except: pass
        
    # Wait up to 2 seconds for a graceful biological shutdown...
    if core_process is not None and core_process.poll() is None:
        for _ in range(20):
            if core_process.poll() is not None: break
            time.sleep(0.1)
        # If she is still fighting, terminate the process violently to prevent a Zombie
        if core_process.poll() is None:
            core_process.terminate()

    if consol_proc is not None and consol_proc.poll() is None:
        consol_proc.terminate()

    app.destroy()
    sys.exit(0)

# Bind the X button to our Dead Man's Switch
app.protocol("WM_DELETE_WINDOW", on_closing)

# --- SOCKET.IO CLIENT ---
sio = socketio.Client(ssl_verify=False)
latest_telemetry_packet = None

@sio.event
def connect():
    sio.emit('identify_incubator')
    log_textbox.insert("end", "[SYSTEM] Telemetry link established.\n")
    log_textbox.see("end")

@sio.event
def disconnect():
    log_textbox.insert("end", "[SYSTEM] Telemetry link lost.\n")
    log_textbox.see("end")

@sio.on('dashboard_telemetry')
def on_telemetry(data):
    global latest_telemetry_packet
    latest_telemetry_packet = data

def start_client():
    while True:
        try:
            sio.connect('https://127.0.0.1:5000')
            sio.wait()
        except Exception as e:
            time.sleep(2) 

threading.Thread(target=start_client, daemon=True).start()

# --- GUI LAYOUT (1280x720) ---
optics_frame = ctk.CTkFrame(app, height=300, corner_radius=10)
optics_frame.pack(fill="x", padx=10, pady=10)

retina_lbl = ctk.CTkLabel(optics_frame, text="[ RETINA OFFLINE ]", width=400, height=240, fg_color="black")
retina_lbl.pack(side="left", padx=10, pady=10)

fovea_lbl = ctk.CTkLabel(optics_frame, text="[ FOVEA OFFLINE ]", width=400, height=240, fg_color="black")
fovea_lbl.pack(side="left", padx=10, pady=10)

minds_eye_lbl = ctk.CTkLabel(optics_frame, text="[ MIND'S EYE OFFLINE ]", width=400, height=240, fg_color="black")
minds_eye_lbl.pack(side="left", padx=10, pady=10)

vitals_frame = ctk.CTkFrame(app, height=150, corner_radius=10)
vitals_frame.pack(fill="x", padx=10, pady=5)

emotion_lbl = ctk.CTkLabel(vitals_frame, text="ORGAN 5: STANDBY", font=("Courier", 18, "bold"))
emotion_lbl.pack(pady=5)

valence_bar = ctk.CTkProgressBar(vitals_frame, width=400, progress_color="green")
valence_bar.pack(pady=5)
valence_bar.set(0.5)

energy_bar = ctk.CTkProgressBar(vitals_frame, width=400, progress_color="orange")
energy_bar.pack(pady=5)
energy_bar.set(0.5)

action_lbl = ctk.CTkLabel(vitals_frame, text="ACTION: STANDBY", font=("Courier", 14))
action_lbl.pack(pady=5)

bottom_frame = ctk.CTkFrame(app, corner_radius=10)
bottom_frame.pack(fill="both", expand=True, padx=10, pady=5)

controls_frame = ctk.CTkFrame(bottom_frame, width=300, fg_color="transparent")
controls_frame.pack(side="left", fill="y", padx=10, pady=10)

render_telemetry_var = ctk.BooleanVar(value=True)
color_swap_var = ctk.BooleanVar(value=True) # The Smurf Fix!

telemetry_switch = ctk.CTkSwitch(controls_frame, text="RENDER TELEMETRY (UI)", variable=render_telemetry_var, font=("Courier", 12, "bold"))
telemetry_switch.pack(pady=5, fill="x")

color_switch = ctk.CTkSwitch(controls_frame, text="SWAP COLORS (BGR/RGB)", variable=color_swap_var, font=("Courier", 12, "bold"))
color_switch.pack(pady=5, fill="x")

boot_btn = ctk.CTkButton(controls_frame, text="[ BOOT UNIT 1 ]", command=boot_unit_1, fg_color="darkgreen")
boot_btn.pack(pady=5, fill="x")

shutdown_btn = ctk.CTkButton(controls_frame, text="[ SHUTDOWN UNIT 1 ]", command=shutdown_unit_1, fg_color="#b58d00") 
shutdown_btn.pack(pady=5, fill="x")

consol_btn = ctk.CTkButton(controls_frame, text="[ RUN CONSOLIDATOR ]", command=run_consolidator_independent, fg_color="#00508c") 
consol_btn.pack(pady=5, fill="x")

sleep_btn = ctk.CTkButton(controls_frame, text="[ FULL REM SLEEP SEQUENCE ]", command=trigger_rem_sleep, fg_color="darkred")
sleep_btn.pack(pady=5, fill="x")

log_textbox = ctk.CTkTextbox(bottom_frame, font=("Courier", 12))
log_textbox.pack(side="right", fill="both", expand=True, padx=10, pady=10)
log_textbox.insert("end", "Welcome to the Incubator. Awaiting commands...\n")

# --- THE RENDER LOOP (30 FPS) ---
def update_dashboard():
    global latest_telemetry_packet
    
    if latest_telemetry_packet:
        if render_telemetry_var.get():
            try:
                if latest_telemetry_packet.get('is_coma', False):
                    action_lbl.configure(text=f"ACTION: SUSPENDED | STATE: {latest_telemetry_packet['state']}")
                    emotion_lbl.configure(text="ORGAN 5: COMATOSE / AWAITING LINK")
                else:
                    ret_img = Image.open(io.BytesIO(base64.b64decode(latest_telemetry_packet['retina_bytes']))).convert("RGB")
                    fov_img = Image.open(io.BytesIO(base64.b64decode(latest_telemetry_packet['fovea_bytes']))).convert("RGB")
                    me_img = Image.open(io.BytesIO(base64.b64decode(latest_telemetry_packet['minds_eye_bytes']))).convert("RGB")
                    
                    # THE SMURF FIX: Flip the toggle to swap Red and Blue dynamically!
                    if color_swap_var.get():
                        r, g, b = ret_img.split(); ret_img = Image.merge("RGB", (b, g, r))
                        r, g, b = fov_img.split(); fov_img = Image.merge("RGB", (b, g, r))
                        r, g, b = me_img.split(); me_img = Image.merge("RGB", (b, g, r))
                    
                    ctk_ret = ctk.CTkImage(light_image=ret_img, dark_image=ret_img, size=(400, 240))
                    ctk_fov = ctk.CTkImage(light_image=fov_img, dark_image=fov_img, size=(400, 240))
                    ctk_me = ctk.CTkImage(light_image=me_img, dark_image=me_img, size=(400, 240))
                    
                    retina_lbl.configure(image=ctk_ret, text="")
                    fovea_lbl.configure(image=ctk_fov, text="")
                    minds_eye_lbl.configure(image=ctk_me, text="")
                    
                    val = latest_telemetry_packet['valence']
                    egy = latest_telemetry_packet['energy']
                    emo_name = latest_telemetry_packet['emotion_name']
                    action = latest_telemetry_packet['action']
                    state = latest_telemetry_packet['state']
                    
                    valence_bar.set((val + 1.0) / 2.0)
                    energy_bar.set((egy + 1.0) / 2.0)
                    
                    emotion_lbl.configure(text=f"ORGAN 5: {emo_name} [V: {val:.2f} | E: {egy:.2f}]")
                    action_lbl.configure(text=f"ACTION: {action} | STATE: {state}")
                
            except Exception as e:
                print(f"UI Update Error: {e}")
                
        latest_telemetry_packet = None 
        
    app.after(30, update_dashboard) 

update_dashboard()
app.mainloop()