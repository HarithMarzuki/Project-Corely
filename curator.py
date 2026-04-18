import os
import h5py
import json
import numpy as np
import random
import math
import time

class CognitiveCurator:
    def __init__(self, deep_memory_file, state_dir):
        """
        MIND 8: THE CURATOR
        The Stream of Consciousness Engine responsible for Imagination and Reflection.
        """
        self.deep_memory_file = deep_memory_file
        self.state_dir = state_dir
        self.waking_collection = []  # Holds raw IDs of high-weight memories
        print("Mind 8 (Curator): Storyboard Synthesis & Internal Monologue Online.")

    def get_grid_index(self, val):
        return min(9, max(0, int((val + 1.0) / 2.0 * 10)))

    def add_to_collection(self, memory_id):
        """Called by the waking Core Engine. Only high-weight IDs are admitted."""
        if memory_id not in self.waking_collection:
            self.waking_collection.append(memory_id)
        if len(self.waking_collection) > 1000:
            self.waking_collection.pop(0)

    # ==========================================
    # MODE 1: WAKING HOURS (DAYDREAMING)
    # ==========================================
    def run_waking_cycle(self, tally, entropy_engine):
        if not self.waking_collection or not os.path.exists(self.deep_memory_file):
            return

        start_id = self.waking_collection.pop()

        num_1s = tally.count(1)
        num_0s = tally.count(0)
        mode = 'IMAGINE' if num_1s > num_0s else 'REFLECT'

        energy = int(entropy_engine.random() * 19) + 1
        self._build_story(start_id, mode, energy, random_func=entropy_engine.random)

    # ==========================================
    # MODE 2: REM SLEEP (DREAMING)
    # ==========================================
    def run_sleep_cycle(self, tally, num_memories_absorbed):
        if not os.path.exists(self.deep_memory_file):
            return
            
        print(f"\n[CURATOR] Initiating REM Sleep Cycle...")
        
        # 1. The Afterimage Seed (Fixed delimiter to read gene.txt properly)
        try:
            v_layer_0 = np.load(os.path.join(self.state_dir, "v_layer_0.npy"))
            dna_matrix = np.loadtxt("Unit1/gene.txt", delimiter=",")
            
            v_1d = np.mean(v_layer_0, axis=(0, 2)) / 511.0 
            
            # Ensure dimensions align for dot product
            if len(v_1d) == dna_matrix.shape[0]:
                scrambled = np.dot(v_1d, dna_matrix)
                seed_val = int(np.abs(np.sum(scrambled)) * 1000000) % (2**32 - 1)
                random.seed(seed_val)
                print(f"[CURATOR] Dream sequence seeded by Retinal Afterimage (Seed: {seed_val})")
            else:
                raise ValueError("DNA matrix dimension mismatch.")
        except Exception as e:
            random.seed(time.time())
            print(f"[CURATOR] Using standard temporal seed for dreams. (Reason: {e})")

        num_stories = max(1, int(math.log(max(2, num_memories_absorbed))))
        print(f"[CURATOR] Generating {num_stories} dream sequences tonight.")

        with h5py.File(self.deep_memory_file, 'a') as f:
            raw_mems = f.get('raw_memories')
            if not raw_mems: return
            all_ids = list(raw_mems.keys())

            if not all_ids: return

            for _ in range(num_stories):
                start_id = random.choice(all_ids)
                shuffled_tally = list(tally)
                random.shuffle(shuffled_tally)
                
                roll = shuffled_tally[random.randint(0, len(shuffled_tally)-1)] if shuffled_tally else 0
                mode = 'IMAGINE' if roll == 1 else 'REFLECT'
                energy = random.randint(1, 20)
                
                self._build_story(start_id, mode, energy, random_func=random.random, h5_file=f)
                
        print(f"[CURATOR] REM Sleep Sequence Complete.")

    # ==========================================
    # THE CORE STORYBOARD ENGINE (HEBBIAN CHAIN)
    # ==========================================
    def _build_story(self, start_id, mode, energy, random_func, h5_file=None):
        should_close_file = False
        if h5_file is None:
            h5_file = h5py.File(self.deep_memory_file, 'a')
            should_close_file = True

        try:
            raw_mems = h5_file.get('raw_memories')
            if not raw_mems or start_id not in raw_mems:
                return

            storyboard = [start_id]
            current_id = start_id

            while energy > 0:
                options = self._get_available_links(h5_file, current_id, mode)
                
                # Rule 4: Prevent Infinite Loops (No Duplicate Memories)
                options = {k: v for k, v in options.items() if k not in storyboard}
                
                if not options:
                    break 
                    
                chosen_id = self._weighted_choice(options, random_func())
                
                if not chosen_id:
                    break

                if mode == 'IMAGINE':
                    storyboard.append(chosen_id)
                else:
                    storyboard.insert(0, chosen_id)

                current_id = chosen_id
                energy -= 1

            if start_id in raw_mems:
                parent_mem = raw_mems[start_id]
                existing_stories = json.loads(parent_mem.attrs.get('stories', '[]'))
                
                new_story = {
                    "type": mode,
                    "sequence": storyboard,
                    "weight": 0.0 
                }
                existing_stories.append(new_story)
                parent_mem.attrs['stories'] = json.dumps(existing_stories)

        finally:
            if should_close_file:
                h5_file.close()

    # ==========================================
    # NETWORK NAVIGATION HELPERS
    # ==========================================
    def _get_available_links(self, h5_file, current_id, mode):
        options = {}
        raw_mems = h5_file.get('raw_memories')
        
        if current_id.startswith('vis_') or current_id.startswith('aud_'):
            mem = raw_mems.get(current_id)
            if not mem: return options
            
            # 1. Temporal Links
            if mode == 'IMAGINE':
                nxt = mem.attrs.get('next_ID', 'None')
                if nxt != 'None' and nxt in raw_mems:
                    options[nxt] = float(raw_mems[nxt].attrs.get('weight', 1.0))
            elif mode == 'REFLECT':
                prv = mem.attrs.get('prev_ID', 'None')
                if prv != 'None' and prv in raw_mems:
                    options[prv] = float(raw_mems[prv].attrs.get('weight', 1.0))
                    
            # 2. Synesthetic Pairings
            if current_id.startswith('vis_'):
                p_aud = mem.attrs.get('paired_audio', 'None')
                if p_aud != 'None' and p_aud in raw_mems:
                    options[p_aud] = float(raw_mems[p_aud].attrs.get('weight', 1.0))
            elif current_id.startswith('aud_'):
                p_vis_list = json.loads(mem.attrs.get('paired_visuals', '[]'))
                for p_vis in p_vis_list:
                    if p_vis in raw_mems:
                        options[p_vis] = float(raw_mems[p_vis].attrs.get('weight', 1.0))

            # 3. The "Intuition Lasso" (One-way link from Unconsolidated -> Deep Cluster)
            temp_c = mem.attrs.get('temp_cluster', 'None')
            if temp_c != 'None':
                options[temp_c] = 1.0 # Base weight to encourage Intuition jumping
                        
            # 4. Permanent Cluster Associations
            v, e = mem.attrs.get('valence', 0.0), mem.attrs.get('energy', 0.0)
            grid_name = f"grid_{self.get_grid_index(v)}_{self.get_grid_index(e)}"
            
            for cluster_type in ['visual', 'audio']:
                grp_path = f"clusters/{cluster_type}/{grid_name}"
                grp = h5_file.get(grp_path)
                if grp:
                    for c_id in grp.keys():
                        c_node = grp[c_id]
                        members = json.loads(c_node.attrs.get('members', '{}'))
                        if current_id in members:
                            c_weight = float(c_node.attrs.get('weight', 1.0))
                            num_members = max(1, len(members))
                            options[f"{grp_path}/{c_id}"] = c_weight / num_members

        elif current_id.startswith('clusters/'):
            c_node = h5_file.get(current_id)
            if c_node:
                members = json.loads(c_node.attrs.get('members', '{}'))
                for m_id in members.keys():
                    if m_id in raw_mems:
                        options[m_id] = float(raw_mems[m_id].attrs.get('weight', 1.0))
                        
        return options

    def _weighted_choice(self, options, random_val):
        if not options: return None
        
        total_weight = sum(options.values())
        if total_weight <= 0: 
            return list(options.keys())[0]
            
        target = random_val * total_weight
        cumulative = 0.0
        
        for opt_id, weight in options.items():
            cumulative += weight
            if cumulative >= target:
                return opt_id
                
        return list(options.keys())[-1]