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
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# --- SETUP ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("1280x720")
app.title("UNIT 1 - CORELY")
app.resizable(False, False) 

# ==========================================
# --- SPRITE LOADING & COMPOSITING ---
# ==========================================
# Video & TV Sizes
CRT_W, CRT_H = 384, 240
VID_OFFSET_X, VID_OFFSET_Y = 34, 14
VID_W = 320
VID_H = 192

# Control Panel Sizes
CTRL_BG_W, CTRL_BG_H = 272, 460
SWITCH_W, SWITCH_H = 160, 96
BTN_SIZE = 60

# Macaroni Console Sizes
PC_W, PC_H = 584, 460

# Vitals Panel Sizes
OBSERVER_W, OBSERVER_H = 420, 460
ACTION_MON_W, ACTION_MON_H = 360, 40
SCORE_W, SCORE_H = 104, 40
FACE_MON_W, FACE_MON_H = 120, 96
LIGHT_SIZE = 51


def get_sprite_path(filename):
    for path in [f"Unit1/GUI/{filename}", f"Unit 1/GUI/{filename}", f"GUI/{filename}"]:
        if os.path.exists(path): return path
    return filename

# Load PIL Fonts
try:
    font_action = ImageFont.truetype(get_sprite_path("consolas.ttf"), size=14)
    font_score = ImageFont.truetype(get_sprite_path("consolas.ttf"), size=18)
    font_light = ImageFont.truetype(get_sprite_path("consolas.ttf"), size=22)
except Exception:
    print("Warning: consolas.ttf not found! Using default PIL font.")
    font_action = font_score = font_light = ImageFont.load_default()

def load_ctk_sprite(filename, size, fallback_color):
    try:
        pil_img = Image.open(get_sprite_path(filename)).convert("RGBA").resize(size)
    except Exception:
        print(f"Warning: {filename} not found. Using fallback.")
        pil_img = Image.new("RGBA", size, fallback_color)
    return ctk.CTkImage(light_image=pil_img, size=size)

def get_pil_sprite(filename, size, fallback_color):
    """ Returns raw PIL image for text stamping """
    try:
        return Image.open(get_sprite_path(filename)).convert("RGBA").resize(size)
    except Exception:
        return Image.new("RGBA", size, fallback_color)


# 1. Master Background
bg_img = load_ctk_sprite("concrete_danger.png", (1280, 720), (40, 40, 40, 255))

# 2. TV Optics
crt_pil = get_pil_sprite("CRT.png", (CRT_W, CRT_H), (50, 50, 50, 255))
no_signal_pil = get_pil_sprite("no_signal.png", (VID_W, VID_H), (20, 20, 20, 255))

# 3. Control Panel Assets
controller_bg = load_ctk_sprite("controller.png", (CTRL_BG_W, CTRL_BG_H), (80, 80, 80, 255))
switch_on_img = load_ctk_sprite("switch_on.png", (SWITCH_W, SWITCH_H), (0, 200, 0, 255))
switch_off_img = load_ctk_sprite("switch_off.png", (SWITCH_W, SWITCH_H), (200, 0, 0, 255))

btn_green = load_ctk_sprite("button_green.png", (BTN_SIZE, BTN_SIZE), (0, 150, 0, 255))
btn_green2 = load_ctk_sprite("button_green2.png", (BTN_SIZE, BTN_SIZE), (0, 255, 0, 255))

btn_red = load_ctk_sprite("button_red.png", (BTN_SIZE, BTN_SIZE), (150, 0, 0, 255))
btn_red2 = load_ctk_sprite("button_red2.png", (BTN_SIZE, BTN_SIZE), (255, 0, 0, 255))

btn_blue = load_ctk_sprite("button_blue.png", (BTN_SIZE, BTN_SIZE), (0, 0, 150, 255))
btn_blue2 = load_ctk_sprite("button_blue2.png", (BTN_SIZE, BTN_SIZE), (0, 0, 255, 255))

btn_yellow = load_ctk_sprite("button_yellow.png", (BTN_SIZE, BTN_SIZE), (150, 150, 0, 255))
btn_yellow2 = load_ctk_sprite("button_yellow2.png", (BTN_SIZE, BTN_SIZE), (255, 255, 0, 255))

# 4. Console Assets
pc_bg = load_ctk_sprite("PC.png", (PC_W, PC_H), (30, 30, 30, 255))

# 5. Vitals Panel Base Assets (PIL format for drawing text)
observer_bg = load_ctk_sprite("observer.png", (OBSERVER_W, OBSERVER_H), (80, 80, 80, 255))
action_mon_base = get_pil_sprite("actionMonitor.png", (ACTION_MON_W, ACTION_MON_H), (0, 50, 100, 255))
score_mon_base = get_pil_sprite("emotionScore.png", (SCORE_W, SCORE_H), (100, 0, 0, 255))
face_mon_base = get_pil_sprite("emotionMonitor.png", (FACE_MON_W, FACE_MON_H), (0, 100, 0, 255))

# 6. Mind Lights Bases
red_on_base = get_pil_sprite("red_on.png", (LIGHT_SIZE, LIGHT_SIZE), (255, 50, 50, 255))
red_off_base = get_pil_sprite("red_off.png", (LIGHT_SIZE, LIGHT_SIZE), (100, 0, 0, 255))

# Master Face Templates (Pre-composited for zero-lag rendering)
def load_face_ctk(filename):
    overlay = get_pil_sprite(filename, (FACE_MON_W, FACE_MON_H), (0, 0, 0, 0)) # transparent fallback
    merged = Image.alpha_composite(face_mon_base.copy(), overlay)
    return ctk.CTkImage(light_image=merged, size=(FACE_MON_W, FACE_MON_H))

# Fully baked GUI Face labels
ctk_face_happy = load_face_ctk("face_happy.png")
ctk_face_angry = load_face_ctk("face_angry.png")
ctk_face_sad = load_face_ctk("face_sad.png")
ctk_face_calm = load_face_ctk("face_calm.png")
ctk_face_neutral = load_face_ctk("face_neutral.png")


def build_tv_frame(raw_video_bytes):
    canvas = Image.new("RGBA", (CRT_W, CRT_H), (0,0,0,0))
    if raw_video_bytes is None:
        vid_layer = no_signal_pil
    else:
        try:
            vid_img = Image.open(io.BytesIO(base64.b64decode(raw_video_bytes))).convert("RGB")
            vid_img = vid_img.resize((VID_W, VID_H))
            b, g, r = vid_img.split()
            vid_layer = Image.merge("RGB", (r, g, b)).convert("RGBA")
        except Exception:
            vid_layer = no_signal_pil
            
    canvas.paste(vid_layer, (VID_OFFSET_X, VID_OFFSET_Y))
    canvas = Image.alpha_composite(canvas, crt_pil)
    return ctk.CTkImage(light_image=canvas, size=(CRT_W, CRT_H))

# TV fallback
offline_tv_img = build_tv_frame(None)


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
    log_textbox.insert("end", "\n[SYSTEM] Launching Mind 5 (Consolidator)...\n")
    log_textbox.see("end")
    consol_proc = subprocess.Popen(
        [sys.executable, '-u', 'dreamMachine-v1.py'], 
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=script_dir
    )
    threading.Thread(target=read_subprocess_output, args=(consol_proc, "Mind 5 (Consolidator)"), daemon=True).start()

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
            read_subprocess_output(consol_proc, "Mind 5 (Consolidator)")
            
        threading.Thread(target=wait_and_consolidate, daemon=True).start()
    else:
        log_textbox.insert("end", "\n[ERROR] Cannot sleep. Telemetry link is offline!\n")
        log_textbox.see("end")

def on_closing():
    if sio.connected:
        try:
            sio.emit('force_sleep')
            sio.disconnect()
        except: pass
        
    if core_process is not None and core_process.poll() is None:
        for _ in range(20):
            if core_process.poll() is not None: break
            time.sleep(0.1)
        if core_process.poll() is None:
            core_process.terminate()

    if consol_proc is not None and consol_proc.poll() is None:
        consol_proc.terminate()

    app.destroy()
    sys.exit(0)

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

# ==========================================
# --- ABSOLUTE GUI LAYOUT (1280x720) ---
# ==========================================

# LAYER 0: Master Background Wall
bg_label = ctk.CTkLabel(app, text="", image=bg_img, width=1280, height=720)
bg_label.place(x=0, y=0)

# LAYER 1: Top Box Elements (CRTs)
CRT_Y = 10
CRT1_X, CRT2_X, CRT3_X = 32, 448, 864

retina_lbl = ctk.CTkLabel(app, text="", image=offline_tv_img, fg_color="transparent", width=CRT_W, height=CRT_H)
retina_lbl.place(x=CRT1_X, y=CRT_Y)

fovea_lbl = ctk.CTkLabel(app, text="", image=offline_tv_img, fg_color="transparent", width=CRT_W, height=CRT_H)
fovea_lbl.place(x=CRT2_X, y=CRT_Y)

minds_eye_lbl = ctk.CTkLabel(app, text="", image=offline_tv_img, fg_color="transparent", width=CRT_W, height=CRT_H)
minds_eye_lbl.place(x=CRT3_X, y=CRT_Y)

# ==========================================
# LAYER 2: Bottom Left Box Elements (Controls)
# ==========================================
CTRL_BG_X = 0
CTRL_BG_Y = 260

controller_bg_lbl = ctk.CTkLabel(app, text="", image=controller_bg, fg_color="transparent", width=CTRL_BG_W, height=CTRL_BG_H)
controller_bg_lbl.place(x=CTRL_BG_X, y=CTRL_BG_Y)

# --- Switch Logic ---
render_telemetry = True
def toggle_telemetry(event):
    global render_telemetry
    render_telemetry = not render_telemetry
    telemetry_switch.configure(image=switch_on_img if render_telemetry else switch_off_img)

telemetry_switch = ctk.CTkLabel(app, text="", image=switch_on_img, fg_color="transparent", width=SWITCH_W, height=SWITCH_H)
telemetry_switch.place(x=CTRL_BG_X + 55, y=CTRL_BG_Y + 40)
telemetry_switch.bind("<Button-1>", toggle_telemetry)

ctk.CTkLabel(app, text="TELEMETRY", font=("Consolas", 25, "bold"), text_color="black", fg_color="#88888f").place(x=CTRL_BG_X + 135, y=CTRL_BG_Y + 140, anchor="n")

# --- Custom Sprite Button Builder ---
def create_sprite_button(parent, img_up, img_down, abs_x, abs_y, command):
    btn_lbl = ctk.CTkLabel(parent, text="", image=img_up, fg_color="#88888f", width=BTN_SIZE, height=BTN_SIZE)
    btn_lbl.place(x=abs_x, y=abs_y)
    
    def on_press(event):
        btn_lbl.configure(image=img_down)
    def on_release(event):
        btn_lbl.configure(image=img_up)
        command()
        
    btn_lbl.bind("<ButtonPress-1>", on_press)
    btn_lbl.bind("<ButtonRelease-1>", on_release)
    return btn_lbl

create_sprite_button(app, btn_green, btn_green2, CTRL_BG_X + 52, CTRL_BG_Y + 216, boot_unit_1)
ctk.CTkLabel(app, text="BOOT", font=("Consolas", 18, "bold"), text_color="black", fg_color="#88888f").place(x=CTRL_BG_X + 82, y=CTRL_BG_Y + 280, anchor="n")

create_sprite_button(app, btn_red, btn_red2, CTRL_BG_X + 160, CTRL_BG_Y + 216, shutdown_unit_1)
ctk.CTkLabel(app, text="STOP", font=("Consolas", 18, "bold"), text_color="black", fg_color="#88888f").place(x=CTRL_BG_X + 190, y=CTRL_BG_Y + 280, anchor="n")

create_sprite_button(app, btn_blue, btn_blue2, CTRL_BG_X + 52, CTRL_BG_Y + 316, run_consolidator_independent)
ctk.CTkLabel(app, text="DREAM", font=("Consolas", 18, "bold"), text_color="black", fg_color="#88888f").place(x=CTRL_BG_X + 82, y=CTRL_BG_Y + 380, anchor="n")

create_sprite_button(app, btn_yellow, btn_yellow2, CTRL_BG_X + 160, CTRL_BG_Y + 316, trigger_rem_sleep)
ctk.CTkLabel(app, text="FULL\nCYCLE", font=("Consolas", 18, "bold"), text_color="black", fg_color="#88888f").place(x=CTRL_BG_X + 190, y=CTRL_BG_Y + 380, anchor="n")


# ==========================================
# LAYER 3: Bottom Middle Box Elements (Console)
# ==========================================
MACARONI_X = 275
MACARONI_Y = 261

pc_bg_lbl = ctk.CTkLabel(app, text="", image=pc_bg, fg_color="#00380c", width=PC_W, height=PC_H)
pc_bg_lbl.place(x=MACARONI_X, y=MACARONI_Y)

log_textbox = ctk.CTkTextbox(app, font=("Consolas", 10), text_color="#00d802", fg_color="#00380c", border_width=0, width=448, height=389)
log_textbox.place(x=MACARONI_X + 71, y=MACARONI_Y + 33)

boot_text = (
    "Project Corely - by Harith Marzuki\n"
    "Version 1.0 | Released date: 30-Apr-2026\n"
    "For more information, visit https://github.com/HarithMarzuki/Project-Corely\n"
    "----------------------------------------------------------------------\n\n"
    "System is ready to start...\n\n"
)
log_textbox.insert("end", boot_text)


# ==========================================
# LAYER 4: Bottom Right Box Elements (Vitals & Minds)
# ==========================================
OBS_X = 861
OBS_Y = 261

observer_bg_lbl = ctk.CTkLabel(app, text="", image=observer_bg, fg_color="transparent", width=OBSERVER_W, height=OBSERVER_H)
observer_bg_lbl.place(x=OBS_X, y=OBS_Y)

# --- Action Header ---
ACT_X = OBS_X + 34
ACT_Y = OBS_Y + 74
ctk.CTkLabel(app, text="ACTION", font=("Consolas", 30, "bold"), text_color="black", fg_color="#8b8984").place(x=ACT_X + ACTION_MON_W//2, y=ACT_Y - 5, anchor="s")

action_mon_lbl = ctk.CTkLabel(app, text="", fg_color="transparent", width=ACTION_MON_W, height=ACTION_MON_H)
action_mon_lbl.place(x=ACT_X, y=ACT_Y)

# --- Emotional State Header ---
ctk.CTkLabel(app, text="EMOTIONAL STATE", font=("Consolas", 20, "bold"), text_color="black", fg_color="#8b8984").place(x=OBS_X + OBSERVER_W//2, y=OBS_Y + 160, anchor="s")

# --- Energy Label & Monitor ---
ENG_X = OBS_X + 147
ENG_Y = OBS_Y + 170  
ctk.CTkLabel(app, text="ENERGY", font=("Consolas", 18), text_color="black", fg_color="#8b8984").place(x=ENG_X - 15, y=ENG_Y + SCORE_H//2, anchor="e")

energy_score_lbl = ctk.CTkLabel(app, text="", fg_color="transparent", width=SCORE_W, height=SCORE_H)
energy_score_lbl.place(x=ENG_X, y=ENG_Y)

# --- Valence Label & Monitor ---
VAL_X = OBS_X + 147
VAL_Y = OBS_Y + 226
ctk.CTkLabel(app, text="VALENCE", font=("Consolas", 18), text_color="black", fg_color="#8b8984").place(x=VAL_X - 15, y=VAL_Y + SCORE_H//2, anchor="e")

valence_score_lbl = ctk.CTkLabel(app, text="", fg_color="transparent", width=SCORE_W, height=SCORE_H)
valence_score_lbl.place(x=VAL_X, y=VAL_Y)

# --- Face Monitor ---
FACE_X = OBS_X + 262
FACE_Y = OBS_Y + 170
face_mon_lbl = ctk.CTkLabel(app, text="", fg_color="transparent", width=FACE_MON_W, height=FACE_MON_H)
face_mon_lbl.place(x=FACE_X, y=FACE_Y)

# ==========================================
# --- 8 MINDS STATUS LIGHTS GRID ---
# ==========================================
def get_light_img(is_on, label_text):
    img = red_on_base.copy() if is_on else red_off_base.copy()
    draw = ImageDraw.Draw(img)
    # Approximating center for size 22 text on a 51x51 block
    tw = len(label_text) * 12 
    x = (LIGHT_SIZE - tw) // 2
    y = 12 
    draw.text((x, y), label_text, font=font_light, fill="#8b8984") # Stenciled grey text
    return ctk.CTkImage(light_image=img, size=(LIGHT_SIZE, LIGHT_SIZE))

# Pre-render the 16 possible light states into RAM for 0-lag switching
lights_on = {i: get_light_img(True, f"M{i}") for i in range(1, 9)}
lights_off = {i: get_light_img(False, f"M{i}") for i in range(1, 9)}

mind_lights = {}
LIGHT_START_X = OBS_X + 113
LIGHT_START_Y = OBS_Y + 323
LIGHT_GAP = 2

# Minds Header
ctk.CTkLabel(app, text="MINDS", font=("Consolas", 20, "bold"), text_color="black", fg_color="#8b8984").place(x=LIGHT_START_X + (LIGHT_SIZE*4 + LIGHT_GAP*3)//2, y=LIGHT_START_Y - 5, anchor="s")

# 4x2 Grid Placement
for i in range(8):
    row = i // 4
    col = i % 4
    x = LIGHT_START_X + col * (LIGHT_SIZE + LIGHT_GAP)
    y = LIGHT_START_Y + row * (LIGHT_SIZE + LIGHT_GAP)

    lbl = ctk.CTkLabel(app, text="", image=lights_off[i+1], fg_color="transparent", width=LIGHT_SIZE, height=LIGHT_SIZE)
    lbl.place(x=x, y=y)
    mind_lights[i+1] = lbl


# --- TEXT STAMPING HELPER FUNCTIONS ---
def stamp_action(action_str, state_str):
    img = action_mon_base.copy()
    draw = ImageDraw.Draw(img)
    text = f"{action_str} | {state_str}"
    
    text_w = len(text) * 8  
    x = (ACTION_MON_W - text_w) // 2
    y = 10 
    
    draw.text((x, y), text, font=font_action, fill="#00aaff") # Cyan
    return ctk.CTkImage(light_image=img, size=(ACTION_MON_W, ACTION_MON_H))

def stamp_score(val):
    img = score_mon_base.copy()
    draw = ImageDraw.Draw(img)
    text = f"{val:+.2f}"
    
    text_w = len(text) * 11
    x = (SCORE_W - text_w) // 2
    y = 8
    
    draw.text((x, y), text, font=font_score, fill="#ff3333") # Bright red
    return ctk.CTkImage(light_image=img, size=(SCORE_W, SCORE_H))

# Generate the initial "Standby" states
standby_act = stamp_action("STANDBY", "IDLE")
standby_eng = stamp_score(0.00)
standby_val = stamp_score(0.00)

action_mon_lbl.configure(image=standby_act)
energy_score_lbl.configure(image=stamp_score(0.00))
valence_score_lbl.configure(image=stamp_score(0.00))
face_mon_lbl.configure(image=ctk_face_neutral)

# --- GLOBAL TELEMETRY TIMER ---
last_telemetry_time = 0

# --- THE RENDER LOOP (30 FPS) ---
def update_dashboard():
    global latest_telemetry_packet, last_telemetry_time
    
    # 1. Update Mind Status Lights (Real-time tracking of the 8 Subprocesses)
    c_alive = core_process is not None and core_process.poll() is None
    cn_alive = consol_proc is not None and consol_proc.poll() is None
    br_alive = sio.connected
    head_alive = (time.time() - last_telemetry_time) < 0.5
    
    # Check the tether status for each mind
    mind_lights[1].configure(image=lights_on[1] if c_alive else lights_off[1]) # Core
    mind_lights[2].configure(image=lights_on[2] if c_alive else lights_off[2]) # Librarian
    mind_lights[3].configure(image=lights_on[3] if c_alive else lights_off[3]) # Crawler
    mind_lights[4].configure(image=lights_on[4] if c_alive else lights_off[4]) # Vocoder
    mind_lights[5].configure(image=lights_on[5] if cn_alive else lights_off[5]) # Consolidator
    mind_lights[6].configure(image=lights_on[6] if br_alive else lights_off[6]) # Bridge
    mind_lights[7].configure(image=lights_on[7] if head_alive else lights_off[7]) # Head
    mind_lights[8].configure(image=lights_on[8] if c_alive else lights_off[8]) # Curator

    # 2. Update Monitors and Video
    if latest_telemetry_packet:
        last_telemetry_time = time.time() # Reset the dead-man switch for the Head LED
        
        if render_telemetry:
            try:
                if latest_telemetry_packet.get('is_coma', False):
                    action_mon_lbl.configure(image=stamp_action("SUSPENDED", latest_telemetry_packet['state']))
                    face_mon_lbl.configure(image=ctk_face_neutral)
                    
                    retina_lbl.configure(image=offline_tv_img)
                    fovea_lbl.configure(image=offline_tv_img)
                    minds_eye_lbl.configure(image=offline_tv_img)
                else:
                    ret_img = build_tv_frame(latest_telemetry_packet['retina_bytes'])
                    fov_img = build_tv_frame(latest_telemetry_packet['fovea_bytes'])
                    me_img = build_tv_frame(latest_telemetry_packet['minds_eye_bytes'])
                    
                    retina_lbl.configure(image=ret_img)
                    fovea_lbl.configure(image=fov_img)
                    minds_eye_lbl.configure(image=me_img)
                    
                    val = latest_telemetry_packet['valence']
                    egy = latest_telemetry_packet['energy']
                    action = latest_telemetry_packet['action']
                    state = latest_telemetry_packet['state']
                    
                    # Update numerical sprites
                    energy_score_lbl.configure(image=stamp_score(egy))
                    valence_score_lbl.configure(image=stamp_score(val))
                    action_mon_lbl.configure(image=stamp_action(action, state))
                    
                    # Map quadrant directly to your custom Face Overlays!
                    if val >= 0.1 and egy >= 0.1: face_img = ctk_face_happy
                    elif val < -0.1 and egy >= 0.1: face_img = ctk_face_angry
                    elif val < -0.1 and egy < -0.1: face_img = ctk_face_sad
                    elif val >= 0.1 and egy < -0.1: face_img = ctk_face_calm
                    else: face_img = ctk_face_neutral
                    
                    face_mon_lbl.configure(image=face_img)
                
            except Exception as e:
                print(f"UI Update Error: {e}")
                
        latest_telemetry_packet = None 
        
    app.after(30, update_dashboard) 

update_dashboard()
app.mainloop()