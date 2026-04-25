import os
import sys

# --- DIRECTORY OVERRIDE (VSCode Independence) ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import h5py
import numpy as np
import json
import shutil
import time

try:
    from sklearn.cluster import HDBSCAN
except ImportError:
    try:
        import hdbscan
        HDBSCAN = hdbscan.HDBSCAN
    except ImportError:
        print("ERROR: HDBSCAN not found. Please run 'pip install scikit-learn --upgrade'")
        sys.exit(1)

from encoders import get_visual_profile
from curator import CognitiveCurator

# --- SETTINGS ---
UNCONSOLIDATED_FILE = "Unit1/unconsolidated_memory.h5"
CONSOLIDATED_FILE = "Unit1/consolidated_memory.h5"
TEMP_DREAM_BUFFER = "Unit1/temp_dream_buffer.h5" 
STATE_DIR = "Unit1/simulation_state"

PRUNE_THRESHOLD = 0.50  
MIN_CLUSTER_SIZE = 3    
MIN_SAMPLES = 2         

# --- GRAVITY MATH ---
def get_grid_index(val):
    return min(9, max(0, int((val + 1.0) / 2.0 * 10)))

def get_overlapping_sectors(v, e, weight):
    sectors = []
    radius = 0.05 + (weight * 0.02) 
    
    for x in range(10):
        for y in range(10):
            min_v = -1.0 + (x * 0.2)
            max_v = min_v + 0.2
            min_e = -1.0 + (y * 0.2)
            max_e = min_e + 0.2
            
            closest_v = max(min_v, min(v, max_v))
            closest_e = max(min_e, min(e, max_e))
            
            dist = np.sqrt((v - closest_v)**2 + (e - closest_e)**2)
            if dist <= radius:
                sectors.append(f"grid_{x}_{y}")
                
    if not sectors:
        sectors.append(f"grid_{get_grid_index(v)}_{get_grid_index(e)}")
    return sectors

def perform_deep_sleep():
    print("\n[MIND 5 (Consolidator): DEEP SLEEP INITIATED]")
    
    if os.path.exists(TEMP_DREAM_BUFFER):
        os.remove(TEMP_DREAM_BUFFER) 
        
    if os.path.exists(CONSOLIDATED_FILE):
        shutil.copy(CONSOLIDATED_FILE, TEMP_DREAM_BUFFER)
        print("-> Transferred current mind state to Atomic Dream Buffer.")

    try:
        num_absorbed = 0
        
        with h5py.File(TEMP_DREAM_BUFFER, 'a') as c_db:
            if 'raw_memories' not in c_db: c_db.create_group('raw_memories')
            raw_grp = c_db['raw_memories']

            print("\n--- PHASE 1: SYNAPTIC PRUNING ---")
            mem_keys = list(raw_grp.keys())
            to_delete = []

            for m_id in mem_keys:
                weight = raw_grp[m_id].attrs.get('weight', 1.0)
                if weight < PRUNE_THRESHOLD:
                    to_delete.append(m_id)

            print(f"-> Found {len(to_delete)} decayed memories to forget.")

            for m_id in to_delete:
                attrs = raw_grp[m_id].attrs
                m_type = attrs.get('type')
                
                prev_id = attrs.get('prev_ID', 'None')
                next_id = attrs.get('next_ID', 'None')
                
                if prev_id != 'None' and prev_id in raw_grp:
                    raw_grp[prev_id].attrs['next_ID'] = next_id
                if next_id != 'None' and next_id in raw_grp:
                    raw_grp[next_id].attrs['prev_ID'] = prev_id

                if m_type == 'visual':
                    paired_aud = attrs.get('paired_audio', 'None')
                    if paired_aud != 'None' and paired_aud in raw_grp:
                        a_v_list = json.loads(raw_grp[paired_aud].attrs.get('paired_visuals', '[]'))
                        if m_id in a_v_list:
                            a_v_list.remove(m_id)
                            raw_grp[paired_aud].attrs['paired_visuals'] = json.dumps(a_v_list)
                
                elif m_type == 'audio':
                    paired_vis = json.loads(attrs.get('paired_visuals', '[]'))
                    for v_id in paired_vis:
                        if v_id in raw_grp:
                            raw_grp[v_id].attrs['paired_audio'] = 'None'

                del raw_grp[m_id]

            print("\n--- PHASE 2: INGESTING SHALLOW MEMORY ---")
            if os.path.exists(UNCONSOLIDATED_FILE):
                # FIX: Open in read-only mode so we don't lock it for modification
                with h5py.File(UNCONSOLIDATED_FILE, 'r') as u_db:
                    if 'deposit' in u_db:
                        dep_grp = u_db['deposit']
                        new_keys = list(dep_grp.keys())
                        num_absorbed = len(new_keys)
                        
                        for k in new_keys:
                            if k not in raw_grp:
                                dset = raw_grp.create_dataset(k, data=dep_grp[k][:], compression="gzip", compression_opts=4)
                                for attr_name, attr_val in dep_grp[k].attrs.items():
                                    if attr_name != 'temp_cluster':
                                        dset.attrs[attr_name] = attr_val
                                
                                if 'valence' not in dset.attrs: dset.attrs['valence'] = 0.0
                                if 'energy' not in dset.attrs: dset.attrs['energy'] = 0.0
                
                # FIX: After safely closing the file, delete it from the hard drive entirely!
                try:
                    os.remove(UNCONSOLIDATED_FILE)
                    print(f"-> Absorbed {num_absorbed} new memories into Dream Buffer.")
                    print("-> Purged Shallow Memory drive to reclaim physical disk space.")
                except Exception as e:
                    print(f"-> Absorbed {num_absorbed} memories, but failed to purge Shallow Memory file: {e}")

            all_visuals = [k for k in raw_grp.keys() if raw_grp[k].attrs.get('type') == 'visual']
            all_audios = [k for k in raw_grp.keys() if raw_grp[k].attrs.get('type') == 'audio']

            if 'clusters' in c_db: del c_db['clusters']
            clust_grp = c_db.create_group('clusters')
            vis_clust_grp = clust_grp.create_group('visual')
            aud_clust_grp = clust_grp.create_group('audio')

            print("\n--- PHASE 3: VISUAL ABSTRACTION (HDBSCAN SPATIAL MAPPING) ---")
            if all_visuals:
                v_profiles = np.array([raw_grp[k].attrs['vis_profile'] for k in all_visuals])
                v_clustering = HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, min_samples=MIN_SAMPLES, metric='euclidean').fit(v_profiles)
                
                v_clusters = {}
                for idx, label in enumerate(v_clustering.labels_):
                    if label == -1: continue 
                    if label not in v_clusters: v_clusters[label] = []
                    v_clusters[label].append((all_visuals[idx], v_clustering.probabilities_[idx]))
                    
                for c_id, members_data in v_clusters.items():
                    members = [m[0] for m in members_data]
                    probs = [m[1] for m in members_data]
                    
                    total_w = sum(raw_grp[m].attrs.get('weight', 1.0) for m in members)
                    avg_val = np.mean([raw_grp[m].attrs.get('valence', 0.0) for m in members])
                    avg_egy = np.mean([raw_grp[m].attrs.get('energy', 0.0) for m in members])
                    
                    # Blend visuals perfectly based on HDBSCAN probability score
                    prob_sum = sum(probs)
                    if prob_sum == 0: prob_sum = 1e-6
                    
                    c_img = np.zeros_like(raw_grp[members[0]][:], dtype=np.float32)
                    for i, m in enumerate(members):
                        c_img += raw_grp[m][:] * (probs[i] / prob_sum)
                    
                    c_img = np.clip(c_img, 0, 255).astype(np.uint8)
                    c_prof = get_visual_profile(c_img)
                    
                    member_dists = {m: float(np.linalg.norm(np.array(c_prof) - np.array(raw_grp[m].attrs['vis_profile']))) for m in members}
                    
                    c_name = f"v_concept_{c_id}"
                    sectors = get_overlapping_sectors(avg_val, avg_egy, total_w)
                    primary_sector = f"grid_{get_grid_index(avg_val)}_{get_grid_index(avg_egy)}"
                    
                    p_grp = vis_clust_grp.require_group(primary_sector)
                    cdset = p_grp.create_dataset(c_name, data=c_img, compression="gzip", compression_opts=4)
                    cdset.attrs.update({'vis_profile': c_prof, 'members': json.dumps(member_dists), 
                                        'member_count': len(members), 'valence': float(avg_val), 
                                        'energy': float(avg_egy), 'weight': float(total_w)})
                    
                    target_path = cdset.name 
                    for s in sectors:
                        if s != primary_sector:
                            link_grp = vis_clust_grp.require_group(s)
                            link_grp[c_name] = h5py.SoftLink(target_path)
                            
                print(f"-> Formed {len(v_clusters)} Visual Concepts mapped across spatial grid.")

            print("\n--- PHASE 4: ACOUSTIC ABSTRACTION (HDBSCAN SPATIAL MAPPING) ---")
            if all_audios:
                # [MIGRATION FIX] Force old 3D audio memory profiles down to 2D
                for m_id in all_audios:
                    prof = list(raw_grp[m_id].attrs['aud_profile'])
                    if len(prof) > 2:
                        raw_grp[m_id].attrs['aud_profile'] = prof[:2]

                a_profiles = np.array([raw_grp[k].attrs['aud_profile'] for k in all_audios])
                a_clustering = HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE, min_samples=MIN_SAMPLES, metric='euclidean').fit(a_profiles)
                
                a_clusters = {}
                for idx, label in enumerate(a_clustering.labels_):
                    if label == -1: continue 
                    if label not in a_clusters: a_clusters[label] = []
                    a_clusters[label].append((all_audios[idx], a_clustering.probabilities_[idx]))
                    
                for c_id, members_data in a_clusters.items():
                    members = [m[0] for m in members_data]
                    probs = [m[1] for m in members_data]
                    
                    total_w = sum(raw_grp[m].attrs.get('weight', 1.0) for m in members)
                    avg_val = np.mean([raw_grp[m].attrs.get('valence', 0.0) for m in members])
                    avg_egy = np.mean([raw_grp[m].attrs.get('energy', 0.0) for m in members])
                    
                    # Native HDBSCAN probability allows us to instantly find the "Alpha" memory
                    alpha_idx = int(np.argmax(probs))
                    alpha_id = members[alpha_idx]
                            
                    alpha_audio_data = raw_grp[alpha_id][:]
                    alpha_profile = raw_grp[alpha_id].attrs['aud_profile']
                    
                    member_dists = {m: float(np.linalg.norm(np.array(alpha_profile) - np.array(raw_grp[m].attrs['aud_profile']))) for m in members}
                        
                    c_name = f"a_concept_{c_id}"
                    sectors = get_overlapping_sectors(avg_val, avg_egy, total_w)
                    primary_sector = f"grid_{get_grid_index(avg_val)}_{get_grid_index(avg_egy)}"
                    
                    p_grp = aud_clust_grp.require_group(primary_sector)
                    cdset = p_grp.create_dataset(c_name, data=alpha_audio_data, compression="gzip", compression_opts=4)
                    cdset.attrs.update({'aud_profile': alpha_profile, 'members': json.dumps(member_dists), 
                                        'member_count': len(members), 'alpha_prototype_id': alpha_id,
                                        'valence': float(avg_val), 'energy': float(avg_egy), 'weight': float(total_w)})
                    
                    target_path = cdset.name 
                    for s in sectors:
                        if s != primary_sector:
                            link_grp = aud_clust_grp.require_group(s)
                            link_grp[c_name] = h5py.SoftLink(target_path)
                    
                print(f"-> Formed {len(a_clusters)} Acoustic Concepts mapped across spatial grid.")
                
        print("\n--- PHASE 5: REM SLEEP (MIND 8 STORYBOARD SYNTHESIS) ---")
        
        tally_path = os.path.join(STATE_DIR, "tally.json")
        prediction_tally = []
        if os.path.exists(tally_path):
            try:
                with open(tally_path, 'r') as f:
                    prediction_tally = json.load(f)
            except: pass
            
        curator_engine = CognitiveCurator(TEMP_DREAM_BUFFER, STATE_DIR)
        curator_engine.run_sleep_cycle(prediction_tally, num_absorbed)

        shutil.move(TEMP_DREAM_BUFFER, CONSOLIDATED_FILE)
        print("\n[DEEP SLEEP COMPLETE. MEMORY AND DREAMS SAFELY COMMITTED.]")
        
    except Exception as e:
        print(f"\n[CRITICAL ERROR DURING CONSOLIDATION: {e}]")
        print("-> The process was interrupted. The main brain file is unharmed.")
        if os.path.exists(TEMP_DREAM_BUFFER):
            os.remove(TEMP_DREAM_BUFFER)

if __name__ == "__main__":
    perform_deep_sleep()