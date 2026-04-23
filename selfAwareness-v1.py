import os
import sys

# --- DIRECTORY OVERRIDE (VSCode Independence) ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import cv2
import queue
import time
import threading
import datetime
import json
import h5py
import numpy as np
import scipy.linalg
import cupy as cp
from cupyx.scipy.ndimage import convolve
import base64 
import heapq
import math
import random
import traceback

from flask import Flask, render_template, request 
from flask_socketio import SocketIO
import logging

from encoders import get_visual_profile, get_audio_profile
from curator import CognitiveCurator

# --- SETTINGS ---
WIDTH, HEIGHT = 1280, 720 
FOVEA_SIZE = 300          

STATE_DIR = "Unit1/simulation_state"
UNCONSOLIDATED_FILE = "Unit1/unconsolidated_memory.h5"
CONSOLIDATED_FILE = "Unit1/consolidated_memory.h5"
SAVE_COOLDOWN = 0.5 

SAMPLE_RATE = 44100
NOISE_THRESHOLD = 0.010  
MAX_BASKET_SAMPLES = int(SAMPLE_RATE * 5.0) 

BASE_DECAY = 0.3
HEAT_DECAY = 0.8
SCATTER = 9.0
HEAT_INTERVAL = 2
COHERENCE_TOLERANCE = 35.0 
SLEEP_PIXEL_THRESHOLD = 5000 
SACCADE_SPEED = 0.15 
PERIPHERAL_THRESHOLD = 20.0 
MIN_TOTAL_MOTION = 5000     
MAX_VIS_DIST = 0.35 
MAX_AUD_DIST = 0.45 

# --- PHASE 2: PRIORITY COGNITIVE LOCK ---
class CognitiveLock:
    def __init__(self):
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)
        self.active = False
        self.waiting = []
        self.ticket = 0

    def acquire(self, priority):
        with self.lock:
            my_ticket = self.ticket
            self.ticket += 1
            heapq.heappush(self.waiting, (priority, my_ticket))
            while self.active or self.waiting[0][1] != my_ticket:
                self.cv.wait()
            heapq.heappop(self.waiting)
            self.active = True

    def release(self):
        with self.lock:
            self.active = False
            self.cv.notify_all()

deep_lock = CognitiveLock()
shallow_lock = CognitiveLock()

# --- GLOBALS & QUEUES ---
current_decay = BASE_DECAY
v_coherence_history = np.zeros(WIDTH, dtype=np.float32)
v_velocity_history = np.zeros(WIDTH, dtype=np.float32)
validation_history = np.zeros(WIDTH, dtype=np.float32)

eye_x, eye_y = (WIDTH - FOVEA_SIZE) // 2.0, (HEIGHT - FOVEA_SIZE) // 2.0
target_x, target_y = eye_x, eye_y
prev_gpu_frame = None

last_save_time = time.time()
last_noise_time = time.time()
pending_audio_alert = None 

visual_queue = queue.Queue() 
audio_queue = queue.Queue()  
new_audio_alert_queue = queue.Queue() 
librarian_new_audio_queue = queue.Queue() 
crawler_cmd_queue = queue.Queue(maxsize=5) 
minds_eye_queue = queue.Queue(maxsize=1)   
vocal_queue = queue.Queue(maxsize=2)  
mood_pull_queue = queue.Queue() 
stop_threads = threading.Event()

current_validation = 0.5
expected_profile = None
expected_id = None
prediction_multiplier = 1.0 
wandering_drive = 0.1       

minds_eye_img = np.zeros((240, 427, 3), dtype=np.uint8)
minds_eye_status = "IDLE"
minds_eye_alpha = 0.0 

shared_live_vis_profile = np.zeros(512) 
is_daydreaming_audio = False 

# --- TALLY SYSTEM ---
prediction_tally = []
tally_path = os.path.join(STATE_DIR, "tally.json")
if os.path.exists(tally_path):
    try:
        with open(tally_path, 'r') as f:
            prediction_tally = json.load(f)
    except: pass

# --- PHASE 3: FLASK WEB SERVER ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
app = Flask(__name__, template_folder='web', static_folder='web')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', max_http_buffer_size=1e8)

# Identity trackers
active_head_sid = None
incubator_sid = None

web_video_queue = queue.Queue(maxsize=1)
raw_audio_queue = queue.Queue()

@app.route('/')
def index(): return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    pass

@socketio.on('identify_incubator')
def handle_identify_incubator():
    global incubator_sid
    incubator_sid = request.sid
    print(f"\n[MIND 6 (Bridge)] Incubator Control Panel Linked. (SID: {request.sid})")

@socketio.on('disconnect')
def handle_disconnect():
    global active_head_sid, incubator_sid
    if request.sid == active_head_sid:
        active_head_sid = None
        print("\n[MIND 6 (Bridge)] Sensory Head Detached! Entering Coma...")
    elif request.sid == incubator_sid:
        incubator_sid = None
        print("\n[MIND 6 (Bridge)] Incubator Control Panel Detached.")

@socketio.on('video_frame')
def handle_video(data):
    global active_head_sid
    if request.sid != active_head_sid:
        active_head_sid = request.sid
        print(f"\n[MIND 6 (Bridge)] Sensory Head Attached and Streaming! (SID: {request.sid})")
        
    try:
        np_arr = np.frombuffer(base64.b64decode(data.split(',')[1]), np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if frame is not None:
            with web_video_queue.mutex: web_video_queue.queue.clear()
            web_video_queue.put(frame)
    except: pass

@socketio.on('audio_chunk')
def handle_audio(data):
    if request.sid != active_head_sid: return
    if is_daydreaming_audio: return 
    try:
        np_arr = np.frombuffer(data, dtype=np.float32)
        raw_audio_queue.put(np_arr)
    except: pass

@socketio.on('force_sleep')
def handle_sleep():
    print("\n[MIND 1] Force Sleep command received from Incubator. Shutting down...")
    stop_threads.set()

def flask_worker():
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, use_reloader=False, ssl_context='adhoc')

# --- ORGAN 5: EMOTION SCOREBOARD ---
class EmotionScoreboard:
    def __init__(self):
        self.valence = 0.0
        self.energy = 0.0

    def update(self, audio_volume, v_velocity, validation_change, is_painful, is_pleasureful, is_soothing, is_bored):
        self.energy += (audio_volume * 2.0) + (abs(v_velocity) * 0.002)
        self.valence += (validation_change * 2.0)
        if is_painful: self.valence -= 0.3; self.energy += 0.3  
        if is_pleasureful: self.valence += 0.3; self.energy += 0.2
        if is_soothing: self.valence += 0.1; self.energy -= 0.3  
        if is_bored: self.energy -= 0.05; self.valence -= 0.005 
        self.valence = max(-1.0, min(1.0, self.valence * 0.915))
        self.energy = max(-1.0, min(1.0, self.energy * 0.900))

    def apply_gravity(self, target_v, target_e, weight):
        pull_strength = min(0.3, 0.05 * weight) 
        self.valence = max(-1.0, min(1.0, self.valence + (target_v - self.valence) * pull_strength))
        self.energy = max(-1.0, min(1.0, self.energy + (target_e - self.energy) * pull_strength))

    def get_emotion_name(self):
        if self.valence >= 0.1 and self.energy >= 0.1: return "JOY / EXCITEMENT"
        elif self.valence < -0.1 and self.energy >= 0.1: return "PANIC / FEAR"
        elif self.valence < -0.1 and self.energy < -0.1: return "SADNESS / LETHARGY"
        elif self.valence >= 0.1 and self.energy < -0.1: return "CONTENTMENT / CALM"
        else: return "NEUTRAL / OBSERVING"

organ_5_emotion = EmotionScoreboard()
def get_grid_index(val): return min(9, max(0, int((val + 1.0) / 2.0 * 10)))

# --- MIND 4: VOCODER ---
is_speaking = False
def vocoder_worker():
    global is_speaking
    import scipy.signal 
    while not stop_threads.is_set():
        try:
            data = vocal_queue.get(timeout=0.5)
            audio_array, vol, speed_mult, quiver, lethargy = data
            is_speaking = True 
            
            with raw_audio_queue.mutex: raw_audio_queue.queue.clear()
            max_raw = np.max(np.abs(audio_array))
            if max_raw > 0: audio_array = audio_array / max_raw
                
            pitch_factor = 1.6 * speed_mult 
            window_size = int(SAMPLE_RATE * 0.04)  
            in_hop = int(window_size * 0.25)       
            out_hop = int(in_hop * pitch_factor)   
            
            window = np.hanning(window_size)
            num_grains = (len(audio_array) - window_size) // in_hop
            
            if num_grains > 0:
                stretched_length = (num_grains * out_hop) + window_size
                stretched_audio = np.zeros(stretched_length)
                for i in range(num_grains):
                    in_start, out_start = i * in_hop, i * out_hop
                    stretched_audio[out_start:out_start + window_size] += audio_array[in_start:in_start + window_size] * window
                old_indices = np.arange(len(stretched_audio))
                new_length = int(len(stretched_audio) / pitch_factor)
                pitch_shifted_audio = np.interp(np.linspace(0, len(stretched_audio) - 1, new_length), old_indices, stretched_audio)
            else:
                pitch_shifted_audio = audio_array
                
            silk_kernel = np.ones(4) / 4
            final_audio = np.convolve(pitch_shifted_audio, silk_kernel, mode='same')
            t = np.arange(len(final_audio)) / SAMPLE_RATE
            
            if quiver > 0.0: final_audio = final_audio * (1.0 - quiver * 0.5 * (1.0 - np.sin(2 * np.pi * 8.0 * t)))
            if lethargy > 0.0:
                l_window = int(lethargy * 100)
                if l_window > 0: final_audio = np.convolve(final_audio, np.ones(l_window) / l_window, mode='same')
                    
            max_val = np.max(np.abs(final_audio))
            if max_val > 0: final_audio = (final_audio / max_val) * vol * 0.8
            
            try:
                if active_head_sid:
                    socketio.emit('vocal_audio', final_audio.astype(np.float32).tobytes(), room=active_head_sid)
            except: pass
            
            time.sleep(0.4) 
            with raw_audio_queue.mutex: raw_audio_queue.queue.clear()
            is_speaking = False 
        except queue.Empty: pass

# --- ORGAN 2: ENTROPY (FIXED DNA) ---
class EnvironmentalEntropy:
    def __init__(self, size=FOVEA_SIZE):
        self.size = size
        self.entropy_pool = []
        self.lock = threading.Lock()
        self.phase = 0.0 
        
        gene_path = "Unit1/gene.txt"
        if not os.path.exists(gene_path):
            col, row = np.random.rand(size), np.random.rand(size)
            toeplitz_dna = scipy.linalg.toeplitz(col, row)
            np.savetxt(gene_path, toeplitz_dna, delimiter=",", fmt="%.6f")
        else:
            toeplitz_dna = np.loadtxt(gene_path, delimiter=",")
            
        self.toeplitz = cp.array(toeplitz_dna, dtype=cp.float32)

    def update(self, v_layer_0):
        self.phase = (self.phase + 0.01) % np.pi
        vis_1d = cp.mean(v_layer_0, axis=(0, 2)) / 511.0
        vis_1d = vis_1d + self.phase
        scrambled = cp.dot(vis_1d, self.toeplitz)
        chaos = cp.abs(cp.sin(scrambled * 1234.5678))
        with self.lock: self.entropy_pool = cp.asnumpy(chaos).tolist()

    def random(self):
        with self.lock:
            if self.entropy_pool: return self.entropy_pool.pop()
            return random.random() 

    def choice(self, options, p=None):
        r = self.random()
        if p is None: return options[int(r * len(options))]
        cumulative = 0.0
        for i, prob in enumerate(p):
            cumulative += prob
            if r <= cumulative: return options[i]
        return options[-1]

entropy_engine = EnvironmentalEntropy(FOVEA_SIZE)

# --- STATIC CLUSTER CACHE ---
static_cluster_cache = {'visual': [], 'audio': []}
if os.path.exists(CONSOLIDATED_FILE):
    deep_lock.acquire(2)
    try:
        with h5py.File(CONSOLIDATED_FILE, 'r') as f:
            for c_type in ['visual', 'audio']:
                if f'clusters/{c_type}' in f:
                    for grid_name in f[f'clusters/{c_type}'].keys():
                        for c_id in f[f'clusters/{c_type}/{grid_name}'].keys():
                            prof_key = 'vis_profile' if c_type == 'visual' else 'aud_profile'
                            static_cluster_cache[c_type].append({
                                'id': f"clusters/{c_type}/{grid_name}/{c_id}",
                                'profile': np.array(f[f'clusters/{c_type}/{grid_name}/{c_id}'].attrs[prof_key])
                            })
    except: pass
    finally: deep_lock.release()

DIFFUSION_KERNEL = cp.array([[0.125, 0.125, 0.125],[0.125, 0.000, 0.125],[0.125, 0.125, 0.125]], dtype=cp.float32)[:, :, cp.newaxis]
Y_GRID, X_GRID = cp.mgrid[0:HEIGHT, 0:WIDTH]
X_GRID, Y_GRID = X_GRID.astype(cp.float32), Y_GRID.astype(cp.float32)

def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

# --- MIND 2: LIBRARIAN ---
def librarian_worker():
    last_vis_key, last_aud_key = None, None
    vis_counter, aud_counter = 0, 0
    visual_buffer = []
    
    shallow_lock.acquire(4)
    try:
        with h5py.File(UNCONSOLIDATED_FILE, 'a') as f:
            if 'deposit' not in f: f.create_group('deposit')
            else:
                v_keys = sorted([k for k in f['deposit'].keys() if k.startswith('vis_')])
                a_keys = sorted([k for k in f['deposit'].keys() if k.startswith('aud_')])
                if v_keys: last_vis_key = v_keys[-1]
                if a_keys: last_aud_key = a_keys[-1]
    finally: shallow_lock.release()

    def save_visual(v_data, paired_aud='None'):
        nonlocal last_vis_key, vis_counter
        v_frame, v_ts_str, v_epoch, v_vel, v_w, v_val, v_egy = v_data
        vis_prof = get_visual_profile(v_frame)
        
        temp_cluster = 'None'
        if static_cluster_cache['visual']:
            best_c, min_d = None, 999.0
            for c in static_cluster_cache['visual']:
                d = np.linalg.norm(np.array(vis_prof) - c['profile'])
                if d < min_d: min_d, best_c = d, c['id']
            if min_d < MAX_VIS_DIST: temp_cluster = best_c
        
        prio = 1 if len(visual_buffer) > 5 else 4
        shallow_lock.acquire(prio)
        try:
            with h5py.File(UNCONSOLIDATED_FILE, 'a') as f:
                grp = f['deposit']
                vis_key = f"vis_{v_ts_str}_{vis_counter}"
                v_dset = grp.create_dataset(vis_key, data=v_frame, compression="gzip", compression_opts=4)
                v_dset.attrs.update({'timestamp': v_ts_str, 'epoch': v_epoch, 'velocity': v_vel, 
                                     'type': 'visual', 'vis_profile': vis_prof, 'weight': v_w, 
                                     'paired_audio': paired_aud, 'next_ID': 'None',
                                     'valence': v_val, 'energy': v_egy, 'temp_cluster': temp_cluster})
                if last_vis_key and last_vis_key in grp:
                    v_dset.attrs['prev_ID'] = last_vis_key
                    grp[last_vis_key].attrs['next_ID'] = vis_key
                else: v_dset.attrs['prev_ID'] = 'None'
                last_vis_key = vis_key
                vis_counter += 1
        finally: shallow_lock.release()
        return vis_key

    def save_audio(a_data, start_t, end_t, paired_vis_list, a_val, a_egy):
        nonlocal last_aud_key, aud_counter
        aud_prof = get_audio_profile(a_data) # [MIGRATION]: This is now 2D
        ts_str = datetime.datetime.fromtimestamp(end_t).strftime("%Y-%m-%d_%H-%M-%S")
        
        temp_cluster = 'None'
        if static_cluster_cache['audio']:
            best_c, min_d = None, 999.0
            for c in static_cluster_cache['audio']:
                # [MIGRATION FIX]: Safely clamp the static 3D target profile to match the incoming 2D profile length
                target_prof = c['profile'][:len(aud_prof)]
                d = np.linalg.norm(np.array(aud_prof) - np.array(target_prof))
                if d < min_d: min_d, best_c = d, c['id']
            if min_d < MAX_AUD_DIST: temp_cluster = best_c
        
        prio = 1 if len(visual_buffer) > 5 else 4
        shallow_lock.acquire(prio)
        try:
            with h5py.File(UNCONSOLIDATED_FILE, 'a') as f:
                grp = f['deposit']
                aud_key = f"aud_{ts_str}_{aud_counter}"
                a_dset = grp.create_dataset(aud_key, data=a_data, compression="gzip", compression_opts=4)
                a_dset.attrs.update({'timestamp': ts_str, 'start_epoch': start_t, 'end_epoch': end_t,
                                     'type': 'audio', 'aud_profile': aud_prof, 'weight': 1.0, 
                                     'paired_visuals': json.dumps(paired_vis_list), 'next_ID': 'None',
                                     'valence': a_val, 'energy': a_egy, 'temp_cluster': temp_cluster})
                if last_aud_key and last_aud_key in grp:
                    a_dset.attrs['prev_ID'] = last_aud_key
                    grp[last_aud_key].attrs['next_ID'] = aud_key
                else: a_dset.attrs['prev_ID'] = 'None'
                last_aud_key = aud_key
                aud_counter += 1
        finally: shallow_lock.release()
            
        new_audio_alert_queue.put((aud_key, aud_prof, a_data))
        librarian_new_audio_queue.put(aud_prof) 
        return aud_key

    while not stop_threads.is_set():
        try:
            while not visual_queue.empty(): visual_buffer.append(visual_queue.get())
            try:
                a_data, start_t, end_t, a_val, a_egy = audio_queue.get(timeout=0.1)
                overlapping_vis, independent_vis = [], []
                for v in visual_buffer:
                    if start_t <= v[2] <= end_t: overlapping_vis.append(v)
                    elif v[2] < start_t: independent_vis.append(v)
                for v in independent_vis:
                    save_visual(v, paired_aud='None')
                    visual_buffer.remove(v)
                
                predicted_aud_key = f"aud_{datetime.datetime.fromtimestamp(end_t).strftime('%Y-%m-%d_%H-%M-%S')}_{aud_counter}"
                saved_vis_ids = []
                for v in overlapping_vis:
                    vid = save_visual(v, paired_aud=predicted_aud_key)
                    saved_vis_ids.append(vid)
                    visual_buffer.remove(v)
                save_audio(a_data, start_t, end_t, saved_vis_ids, a_val, a_egy)
            except queue.Empty:
                now = time.time()
                stale_vis = [v for v in visual_buffer if (now - v[2]) > 6.0]
                for v in stale_vis:
                    save_visual(v, paired_aud='None')
                    visual_buffer.remove(v)
        except Exception as e: pass

# --- MIND 8: CURATOR INITIATION ---
curator_engine = CognitiveCurator(CONSOLIDATED_FILE, STATE_DIR)

def curator_worker():
    while not stop_threads.is_set():
        time.sleep(5.0) 
        deep_lock.acquire(3) 
        try: curator_engine.run_waking_cycle(prediction_tally, entropy_engine)
        except: pass
        finally: deep_lock.release()

threading.Thread(target=curator_worker, daemon=True).start()

# --- MIND 3: CRAWLER (STORY & TRANCE) ---
def play_audio_trance(audio_data):
    global is_daydreaming_audio
    is_daydreaming_audio = True
    vocal_queue.put((audio_data, 1.0, 1.0, 0.0, 0.0))
    while not vocal_queue.empty() or is_speaking: time.sleep(0.1)
    is_daydreaming_audio = False

def execute_story(story, memory_id, raw_mems, drive_type):
    seq, s_type = story['sequence'], story['type']
    story_score = 0
    
    if drive_type in ['WANDER', 'PREDICT_VISUAL'] and s_type == 'IMAGINE':
        for m_id in seq:
            if m_id.startswith('vis_'):
                prof = raw_mems[m_id].attrs['vis_profile']
                minds_eye_queue.put((raw_mems[m_id][:], list(prof), 'IMAGINING (VIS)', m_id))
                best_dist = 999.0
                for _ in range(20):
                    time.sleep(0.1)
                    best_dist = min(best_dist, np.linalg.norm(np.array(shared_live_vis_profile) - prof))
                story_score += 1 if best_dist < MAX_VIS_DIST else -1
            elif m_id.startswith('aud_'): play_audio_trance(raw_mems[m_id][:])
            elif 'clusters' in m_id:
                minds_eye_queue.put((None, [], 'SYNTHESIS', m_id))
                time.sleep(0.5)
                
        safe_reward(raw_mems, memory_id, 0.5) if story_score >= 0 else safe_reward(raw_mems, memory_id, -0.2)

    elif drive_type in ['WANDER', 'PREDICT_VISUAL'] and s_type == 'REFLECT':
        for m_id in seq:
            if m_id.startswith('vis_'):
                minds_eye_queue.put((raw_mems[m_id][:], list(raw_mems[m_id].attrs['vis_profile']), 'REFLECTING (VIS)', m_id))
                mood_pull_queue.put((float(raw_mems[m_id].attrs.get('valence',0)), float(raw_mems[m_id].attrs.get('energy',0)), 1.0))
                time.sleep(2.0)
            elif m_id.startswith('aud_'): play_audio_trance(raw_mems[m_id][:])
            elif 'clusters' in m_id:
                minds_eye_queue.put((None, [], 'SYNTHESIS', m_id))
                time.sleep(0.5)
        
        owner_v = raw_mems[memory_id].attrs.get('valence', 0)
        owner_e = raw_mems[memory_id].attrs.get('energy', 0)
        if math.hypot(organ_5_emotion.valence - owner_v, organ_5_emotion.energy - owner_e) < 0.3:
            safe_reward(raw_mems, memory_id, 0.5)
        else:
            safe_reward(raw_mems, memory_id, -0.2)
            raw_mems[memory_id].attrs['valence'] = organ_5_emotion.valence
            raw_mems[memory_id].attrs['energy'] = organ_5_emotion.energy

    elif drive_type == 'DIGEST_AUDIO' and s_type == 'IMAGINE':
        for i, m_id in enumerate(seq):
            if m_id.startswith('aud_'):
                if i != 0: play_audio_trance(raw_mems[m_id][:])
                mood_pull_queue.put((float(raw_mems[m_id].attrs.get('valence',0)), float(raw_mems[m_id].attrs.get('energy',0)), 1.0))
            elif m_id.startswith('vis_'):
                minds_eye_queue.put((raw_mems[m_id][:], list(raw_mems[m_id].attrs['vis_profile']), 'IMAGINING (VIS)', m_id))
                time.sleep(2.0)
            elif 'clusters' in m_id:
                minds_eye_queue.put((None, [], 'SYNTHESIS', m_id))
                time.sleep(0.5)
                
        owner_v = raw_mems[memory_id].attrs.get('valence', 0)
        owner_e = raw_mems[memory_id].attrs.get('energy', 0)
        if math.hypot(organ_5_emotion.valence - owner_v, organ_5_emotion.energy - owner_e) < 0.3:
            safe_reward(raw_mems, memory_id, 0.5)
        else:
            safe_reward(raw_mems, memory_id, -0.2)
            raw_mems[memory_id].attrs['valence'] = organ_5_emotion.valence
            raw_mems[memory_id].attrs['energy'] = organ_5_emotion.energy

    elif drive_type == 'DIGEST_AUDIO' and s_type == 'REFLECT':
        for i, m_id in enumerate(seq):
            if i == len(seq) - 1 and m_id.startswith('aud_'):
                target_prof = np.array(raw_mems[m_id].attrs['aud_profile'])
                minds_eye_queue.put((None, list(target_prof), 'LISTENING FOR CUE...', m_id))
                matched = False
                while not librarian_new_audio_queue.empty(): librarian_new_audio_queue.get() 
                
                for _ in range(50): 
                    time.sleep(0.1)
                    while not librarian_new_audio_queue.empty():
                        new_prof = librarian_new_audio_queue.get()
                        # [MIGRATION FIX]: Dynamically clamp target profile based on the live 2D profile length
                        if np.linalg.norm(np.array(new_prof) - target_prof[:len(new_prof)]) < MAX_AUD_DIST:
                            matched = True; break
                    if matched: break
                
                if matched: safe_reward(raw_mems, memory_id, 1.0)
                else: safe_reward(raw_mems, memory_id, -0.5)
            
            elif m_id.startswith('aud_'): play_audio_trance(raw_mems[m_id][:])
            elif m_id.startswith('vis_'):
                minds_eye_queue.put((raw_mems[m_id][:], list(raw_mems[m_id].attrs['vis_profile']), 'REFLECTING (VIS)', m_id))
                time.sleep(2.0)
            elif 'clusters' in m_id:
                minds_eye_queue.put((None, [], 'SYNTHESIS', m_id))
                time.sleep(0.5)

def safe_reward(raw_mems, m_id, amount=0.1):
    if m_id in raw_mems:
        raw_mems[m_id].attrs['weight'] = max(0.1, raw_mems[m_id].attrs.get('weight', 1.0) + amount)
        curator_engine.add_to_collection(m_id) if raw_mems[m_id].attrs['weight'] > 10 else None

def crawler_worker():
    def trigger_gravity(cluster_grp, c_id):
        mood_pull_queue.put((float(cluster_grp[c_id].attrs.get('valence', 0)), float(cluster_grp[c_id].attrs.get('energy', 0)), float(cluster_grp[c_id].attrs.get('weight', 1))))

    while not stop_threads.is_set():
        try:
            try: cmd, data = crawler_cmd_queue.get(timeout=0.5)
            except queue.Empty: continue
            
            if not os.path.exists(CONSOLIDATED_FILE): continue
            
            deep_lock.acquire(2) 
            try:
                with h5py.File(CONSOLIDATED_FILE, 'a') as f:
                    raw_mems = f.get('raw_memories')
                    if not raw_mems: continue
                    
                    v, e = organ_5_emotion.valence, organ_5_emotion.energy
                    grid_name = f"grid_{get_grid_index(v)}_{get_grid_index(e)}"
                    active_vis_clusters = f.get(f'clusters/visual/{grid_name}')
                    active_aud_clusters = f.get(f'clusters/audio/{grid_name}')

                    if cmd == 'WANDER':
                        if active_vis_clusters:
                            c_keys = list(active_vis_clusters.keys())
                            if c_keys:
                                rand_c = entropy_engine.choice(c_keys)
                                trigger_gravity(active_vis_clusters, rand_c) 
                                members = json.loads(active_vis_clusters[rand_c].attrs.get('members', '{}'))
                                valid_m = [k for k in members.keys() if k in raw_mems]
                                if valid_m:
                                    target_id = entropy_engine.choice(valid_m)
                                    safe_reward(raw_mems, target_id)
                                    stories = json.loads(raw_mems[target_id].attrs.get('stories', '[]'))
                                    
                                    if stories and entropy_engine.random() < 0.7:
                                        execute_story(entropy_engine.choice(stories), target_id, raw_mems, cmd)
                                    elif not minds_eye_queue.full():
                                        minds_eye_queue.put((raw_mems[target_id][:], list(raw_mems[target_id].attrs['vis_profile']), 'DAYDREAM (VISUAL)', target_id))

                    elif cmd == 'PREDICT_VISUAL':
                        if active_vis_clusters:
                            best_c_id, min_dist = None, 999.0
                            for c_id in active_vis_clusters.keys():
                                dist = np.linalg.norm(np.array(data) - np.array(active_vis_clusters[c_id].attrs['vis_profile']))
                                if dist < min_dist: min_dist, best_c_id = dist, c_id
                                
                            if best_c_id and min_dist < MAX_VIS_DIST:
                                trigger_gravity(active_vis_clusters, best_c_id) 
                                members = json.loads(active_vis_clusters[best_c_id].attrs.get('members', '{}'))
                                if members:
                                    best_mem = max(members.items(), key=lambda x: raw_mems[x[0]].attrs.get('weight', 1.0) if x[0] in raw_mems else -1)[0]
                                    if best_mem in raw_mems:
                                        n_id = raw_mems[best_mem].attrs.get('next_ID', 'None')
                                        target_id = n_id if (n_id != 'None' and n_id in raw_mems) else best_mem
                                        safe_reward(raw_mems, target_id)
                                        
                                        stories = json.loads(raw_mems[target_id].attrs.get('stories', '[]'))
                                        
                                        if stories and entropy_engine.random() < 0.7:
                                            execute_story(entropy_engine.choice(stories), target_id, raw_mems, cmd)
                                        elif not minds_eye_queue.full(): 
                                            minds_eye_queue.put((raw_mems[target_id][:], list(raw_mems[target_id].attrs['vis_profile']), 'PREDICTION', target_id))

                    elif cmd == 'DIGEST_AUDIO':
                        if active_aud_clusters:
                            best_c_id, min_dist = None, 999.0
                            for c_id in active_aud_clusters.keys():
                                # [MIGRATION FIX]: Safely clamp 3D targets to match 2D live data
                                target_prof = np.array(active_aud_clusters[c_id].attrs['aud_profile'])[:len(data)]
                                dist = np.linalg.norm(np.array(data) - target_prof)
                                if dist < min_dist: min_dist, best_c_id = dist, c_id
                                
                            if best_c_id and min_dist < MAX_AUD_DIST:
                                trigger_gravity(active_aud_clusters, best_c_id) 
                                members = json.loads(active_aud_clusters[best_c_id].attrs.get('members', '{}'))
                                if members:
                                    best_mem = min(members.items(), key=lambda x: x[1])[0] 
                                    if best_mem in raw_mems:
                                        safe_reward(raw_mems, best_mem, 0.2)
                                        stories = json.loads(raw_mems[best_mem].attrs.get('stories', '[]'))
                                        
                                        if stories and entropy_engine.random() < 0.7:
                                            execute_story(entropy_engine.choice(stories), best_mem, raw_mems, cmd)
                                        elif not minds_eye_queue.full():
                                            minds_eye_queue.put((None, list(raw_mems[best_mem].attrs['aud_profile']), 'DIGESTING AUDIO', best_mem))

            finally: deep_lock.release()
        except Exception as e: print(f"Crawler Error: {e}")

# --- PERSISTENCE ---
def load_state():
    try:
        v_l = [cp.array(np.load(os.path.join(STATE_DIR, f"v_layer_{i}.npy"))) for i in range(5)]
        v_h = [cp.array(np.load(os.path.join(STATE_DIR, f"v_heat_{i}.npy"))) for i in range(5)]
        p = {"ATTENTION": cp.array(np.load(os.path.join(STATE_DIR, "param_ATTENTION.npy")))}
        return v_l, v_h, p
    except:
        return ([cp.zeros((FOVEA_SIZE, FOVEA_SIZE, 3), dtype=cp.float32) for _ in range(5)],
                [cp.zeros((FOVEA_SIZE, FOVEA_SIZE, 3), dtype=cp.float32) for _ in range(5)],
                {"ATTENTION": cp.full((FOVEA_SIZE, FOVEA_SIZE, 1), 100.0, dtype=cp.float32)})

def save_state(v_layers, v_heats, params):
    if not os.path.exists(STATE_DIR): os.makedirs(STATE_DIR)
    for i in range(5):
        np.save(os.path.join(STATE_DIR, f"v_layer_{i}.npy"), cp.asnumpy(v_layers[i]))
        np.save(os.path.join(STATE_DIR, f"v_heat_{i}.npy"), cp.asnumpy(v_heats[i]))
    np.save(os.path.join(STATE_DIR, "param_ATTENTION.npy"), cp.asnumpy(params["ATTENTION"]))
    with open(tally_path, 'w') as f: json.dump(prediction_tally, f)

if not os.path.exists("Unit1"): os.makedirs("Unit1")

# --- BOOT DIAGNOSTICS FOR THE INCUBATOR ---
print("[MIND 2 (Librarian)] Archival Thread Online.")
threading.Thread(target=librarian_worker, daemon=True).start()

print("[MIND 3 (Crawler)] Deep-Brain Search Engine Online.")
threading.Thread(target=crawler_worker, daemon=True).start()

print("[MIND 4 (Vocoder)] Acoustic Synthesis Online.")
threading.Thread(target=vocoder_worker, daemon=True).start()

print("[MIND 6 (Bridge)] Socket.IO Nervous System Online.")
threading.Thread(target=flask_worker, daemon=True).start() 

v_layers, v_heats, params = load_state()
interval = 0
audio_basket = []
basket_samples = 0
is_recording_audio = False
audio_status_text = "HEARING: DEAD AIR"

last_web_update = time.time() 
last_telemetry_time = time.time() 

print("[MIND 1 (Core)] Headless Engine Online. Broadcasting to Localhost.")

latest_web_frame = None
last_frame_time = 0.0

try:
    while not stop_threads.is_set():
        if not web_video_queue.empty():
            latest_web_frame = web_video_queue.get()
            last_frame_time = time.time()
            
        if latest_web_frame is None or (time.time() - last_frame_time > 2.0):
            now = time.time()
            if now - last_telemetry_time > 1.0:
                last_telemetry_time = now
                try:
                    if incubator_sid:
                        socketio.emit('dashboard_telemetry', {'is_coma': True, 'state': 'COMA (AWAITING SENSORY LINK)'}, room=incubator_sid)
                except: pass
            time.sleep(0.1)
            continue
            
        try:
            frame = latest_web_frame.copy()
            now = time.time()
            live_audio_vol = 0.0
            
            # --- AUDIO ACQUISITION ---
            if is_daydreaming_audio:
                with raw_audio_queue.mutex: raw_audio_queue.queue.clear()
                audio_status_text = "HEARING: DEAF REFLEX (DAYDREAMING)"
            else:
                sticks = []
                while not raw_audio_queue.empty(): sticks.append(raw_audio_queue.get())
                if sticks:
                    stick = np.concatenate(sticks)
                    live_audio_vol = float(np.std(stick))
                    if live_audio_vol > NOISE_THRESHOLD:
                        if not is_recording_audio: is_recording_audio = True
                        audio_basket.append(stick)
                        basket_samples += len(stick)
                        audio_status_text = f"HEARING: RECORDING ({basket_samples/SAMPLE_RATE:.1f}s)"
                        if basket_samples >= MAX_BASKET_SAMPLES:
                            audio_queue.put((np.concatenate(audio_basket), now - (basket_samples/SAMPLE_RATE), now, organ_5_emotion.valence, organ_5_emotion.energy))
                            audio_basket, basket_samples = [], 0
                            is_recording_audio = False 
                    else:
                        if is_recording_audio:
                            audio_basket.append(stick)
                            audio_queue.put((np.concatenate(audio_basket), now - (basket_samples/SAMPLE_RATE), now, organ_5_emotion.valence, organ_5_emotion.energy))
                            audio_basket, basket_samples = [], 0
                            is_recording_audio = False
                            audio_status_text = "HEARING: SAVING BASKET"
                        else: audio_status_text = "HEARING: DEAD AIR"

            # --- VISUAL ACQUISITION ---
            if frame.shape[1] != WIDTH: frame = cv2.resize(frame, (WIDTH, HEIGHT))
            gpu_full_frame = cp.array(frame, dtype=cp.float32)

            curr_gray = (0.299*gpu_full_frame[:,:,2] + 0.587*gpu_full_frame[:,:,1] + 0.114*gpu_full_frame[:,:,0])
            if prev_gpu_frame is None: prev_gpu_frame = curr_gray
            delta_frame = cp.abs(curr_gray - prev_gpu_frame)
            prev_gpu_frame = curr_gray
            
            motion_mask = (delta_frame > PERIPHERAL_THRESHOLD)
            weighted_motion = delta_frame * motion_mask * cp.where(curr_gray > 240, 0.05, 1.0)
            if cp.count_nonzero(motion_mask) > MIN_TOTAL_MOTION and cp.sum(weighted_motion) > 0:
                target_x = (cp.sum(X_GRID * weighted_motion) / cp.sum(weighted_motion)) - (FOVEA_SIZE / 2.0)
                target_y = (cp.sum(Y_GRID * weighted_motion) / cp.sum(weighted_motion)) - (FOVEA_SIZE / 2.0)
            
            eye_x += (target_x - eye_x) * SACCADE_SPEED; eye_y += (target_y - eye_y) * SACCADE_SPEED
            final_x, final_y = int(np.clip(float(eye_x), 0, WIDTH - FOVEA_SIZE)), int(np.clip(float(eye_y), 0, HEIGHT - FOVEA_SIZE))
            gpu_fovea = gpu_full_frame[final_y:final_y+FOVEA_SIZE, final_x:final_x+FOVEA_SIZE]

            entropy_engine.update(v_layers[0])

            gray_fov = (0.299*gpu_fovea[:,:,2] + 0.587*gpu_fovea[:,:,1] + 0.114*gpu_fovea[:,:,0])
            gx, gy = cp.abs(gray_fov[:,1:] - gray_fov[:,:-1]), cp.abs(gray_fov[1:,:] - gray_fov[:-1,:])
            edges = cp.zeros_like(gray_fov); edges[:,:-1] += gx; edges[:-1,:] += gy
            params["ATTENTION"] = cp.clip((convolve(gray_fov*0.5 + edges*2.0, DIFFUSION_KERNEL[:,:,0]) / 10.0) + 50.0, 10, 300)[:,:,cp.newaxis]

            v_layers[0] += gpu_fovea; v_heats[0] += gpu_fovea * params["ATTENTION"]
            for i in range(5):
                ni = (i+1)%5
                sum_arr = ((v_layers[i] + v_heats[i]) / SCATTER) * current_decay
                pm = v_heats[i] >= v_heats[ni]; nm = ~pm
                v_layers[ni][pm] += sum_arr[pm]; v_heats[ni][pm] += v_heats[i][pm] / SCATTER; v_heats[i][nm] -= v_heats[i][nm] / SCATTER
                v_layers[ni][pm] += convolve(sum_arr, DIFFUSION_KERNEL)[pm]

            interval += 1
            for i in range(5):
                v_layers[i] = cp.clip(v_layers[i] * current_decay, 0, 511)
                if interval % HEAT_INTERVAL == 0: v_heats[i] = cp.clip(v_heats[i] * HEAT_DECAY, 0, 4294967295)
            if interval % HEAT_INTERVAL == 0: interval = 0

            h_norm = cp.clip(v_heats[2], 0, cp.percentile(v_heats[2], 95)) / (cp.percentile(v_heats[2], 95)+1e-6) * 255.0
            coh_perc = float(cp.count_nonzero(cp.abs(gpu_fovea - h_norm) < COHERENCE_TOLERANCE) / gpu_fovea.size * 100)
            v_velocity = coh_perc - v_coherence_history[-1]

            live_3d = get_visual_profile(frame)
            shared_live_vis_profile = live_3d 
            decision = None
            override_save = False

            if entropy_engine.random() < 0.02: wandering_drive = 1.0
            else: wandering_drive = max(0.1, wandering_drive - 0.02)
                
            norm_vel = min(abs(v_velocity) / 10.0, 1.0)
            vis_probs = softmax([norm_vel * 2.5, (coh_perc / 100.0) * prediction_multiplier * 1.5, wandering_drive * 1.5])
            
            if is_recording_audio: last_noise_time = now
            time_since_noise = now - last_noise_time

            if not new_audio_alert_queue.empty():
                if pending_audio_alert is not None and crawler_cmd_queue.empty(): 
                    crawler_cmd_queue.put(('DIGEST_AUDIO', pending_audio_alert[1]))
                pending_audio_alert = None
                while not new_audio_alert_queue.empty():
                    if pending_audio_alert is not None and crawler_cmd_queue.empty(): 
                        crawler_cmd_queue.put(('DIGEST_AUDIO', pending_audio_alert[1]))
                    pending_audio_alert = new_audio_alert_queue.get()

            validation_change = 0.0
            is_pleasureful = False

            if pending_audio_alert is not None:
                if time_since_noise >= 1.5:
                    decision = 'DIGEST'
                    if crawler_cmd_queue.empty(): crawler_cmd_queue.put(('DIGEST_AUDIO', pending_audio_alert[1]))
                    pending_audio_alert = None 
                else: decision = 'WAITING FOR FLOOR' 
            else:
                prev_val = current_validation
                
                if expected_profile is not None:
                    dist = np.linalg.norm(np.array(live_3d) - np.array(expected_profile))
                    
                    prediction_tally.append(1 if dist <= (MAX_VIS_DIST / 2.0) else 0)
                    if len(prediction_tally) > 10: prediction_tally.pop(0)

                    if dist < 0.20: 
                        current_validation = min(1.0, current_validation + 0.15)
                        prediction_multiplier = min(3.0, prediction_multiplier + 0.5) 
                        minds_eye_status = f"VALIDATED! [{dist:.2f}]"
                        is_pleasureful = True 
                    elif dist > 0.45: 
                        current_validation = max(0.0, current_validation - 0.25)
                        prediction_multiplier = 1.0 
                        minds_eye_status = f"SURPRISE! [{dist:.2f}]"
                        override_save = True 
                    expected_profile, expected_id = None, None

                current_validation += (0.5 - current_validation) * 0.05 
                validation_change = current_validation - prev_val
                
                try:
                    c_img, c_prof, c_type, c_id = minds_eye_queue.get_nowait()
                    if c_img is not None: minds_eye_img = cv2.resize(c_img, (427, 240))
                    else: 
                        minds_eye_img = np.zeros((240, 427, 3), dtype=np.uint8)
                        cv2.putText(minds_eye_img, "[ ACOUSTIC ]", (150, 120), 0, 0.6, (255, 150, 50), 2)
                    minds_eye_status = c_type
                    if "AUDIO" not in c_type and "SYNTHESIS" not in c_type and "VIS" not in c_type: 
                        expected_profile, expected_id = c_prof, c_id
                    minds_eye_alpha = 1.0
                except queue.Empty: pass

                decision = entropy_engine.choice(['SAVE', 'PREDICT', 'WANDER'], p=vis_probs)
                if override_save: decision = 'SAVE'
                
                if decision == 'SAVE' and (now - last_save_time) > SAVE_COOLDOWN:
                    last_save_time = now
                    with crawler_cmd_queue.mutex: crawler_cmd_queue.queue.clear() 
                    ts_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    visual_queue.put((frame, ts_str, time.time(), float(abs(v_velocity)), 1.0, organ_5_emotion.valence, organ_5_emotion.energy))
                    minds_eye_alpha, minds_eye_status = 0.0, "INTERRUPTED"
                elif decision == 'PREDICT' and crawler_cmd_queue.empty(): crawler_cmd_queue.put(('PREDICT_VISUAL', live_3d))
                elif decision == 'WANDER' and crawler_cmd_queue.empty(): crawler_cmd_queue.put(('WANDER', None))

            is_painful = live_audio_vol > 0.5 or abs(v_velocity) > 40.0
            is_soothing = (0.001 < live_audio_vol < NOISE_THRESHOLD) and abs(v_velocity) < 5.0 
            is_bored = (live_audio_vol < NOISE_THRESHOLD) and (abs(v_velocity) < 1.5) 
            
            organ_5_emotion.update(live_audio_vol, v_velocity, validation_change, is_painful, is_pleasureful, is_soothing, is_bored)

            while not mood_pull_queue.empty():
                tv, te, tw = mood_pull_queue.get()
                organ_5_emotion.apply_gravity(tv, te, tw)

            if now - last_web_update > 0.06:
                last_web_update = now
                live_talk_amp = float(np.random.uniform(0.2, 0.8)) if is_speaking else 0.0
                try:
                    if active_head_sid:
                        socketio.emit('emotion_update', {'valence': float(organ_5_emotion.valence), 'energy': float(organ_5_emotion.energy), 'talk': live_talk_amp}, room=active_head_sid)
                except: pass

            v_coherence_history[:-1], v_coherence_history[-1] = v_coherence_history[1:], coh_perc
            v_velocity_history[:-1], v_velocity_history[-1] = v_velocity_history[1:], v_velocity
            validation_history[:-1], validation_history[-1] = validation_history[1:], current_validation * 100.0
            current_decay = 0.005 if cp.count_nonzero(gpu_fovea > 20) < SLEEP_PIXEL_THRESHOLD else np.clip((BASE_DECAY if abs(v_velocity) <= 2.0 else (current_decay - 0.02)), 0.1, BASE_DECAY)

            minds_eye_alpha = max(0.0, minds_eye_alpha - 0.02)

            if now - last_telemetry_time > 0.05: 
                last_telemetry_time = now
                
                retina_view = cv2.resize(frame, (427, 240))
                fovea_view = cv2.resize(cp.asnumpy(cp.abs(gpu_fovea - h_norm) < COHERENCE_TOLERANCE).astype(np.uint8)*255, (427, 240), interpolation=cv2.INTER_NEAREST)
                me_display = cv2.addWeighted(minds_eye_img, minds_eye_alpha, np.zeros_like(minds_eye_img), 1-minds_eye_alpha, 0)
                
                _, ret_jpg = cv2.imencode('.jpg', retina_view, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                _, fov_jpg = cv2.imencode('.jpg', fovea_view, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                _, me_jpg = cv2.imencode('.jpg', me_display, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                
                action_map = {'SAVE':"MEMORIZING", 'PREDICT':"INQUIRING", 'WANDER':"DAYDREAMING", 'DIGEST':"DIGESTING AUDIO", 'WAITING FOR FLOOR':"WAITING"}
                
                payload = {
                    'is_coma': False,
                    'valence': float(organ_5_emotion.valence),
                    'energy': float(organ_5_emotion.energy),
                    'emotion_name': organ_5_emotion.get_emotion_name(),
                    'action': action_map.get(decision, str(decision)),
                    'state': "VOCALIZING" if is_speaking else audio_status_text,
                    'validation': float(current_validation),
                    'minds_eye_status': minds_eye_status,
                    'retina_bytes': base64.b64encode(ret_jpg.tobytes()).decode('utf-8'),
                    'fovea_bytes': base64.b64encode(fov_jpg.tobytes()).decode('utf-8'),
                    'minds_eye_bytes': base64.b64encode(me_jpg.tobytes()).decode('utf-8')
                }
                
                try:
                    if incubator_sid:
                        socketio.emit('dashboard_telemetry', payload, room=incubator_sid)
                except: pass

        except Exception as e:
            print(f"\n[CRITICAL WARNING] Visual Cortex Misfire: {e}")
            traceback.print_exc()
            time.sleep(0.5)

finally:
    save_state(v_layers, v_heats, params)
    print("\n[MIND 1 (Core)] State Saved. Goodnight.")
    sys.exit(0)