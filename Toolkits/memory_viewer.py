import h5py
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

class MemoryExplorer:
    def __init__(self, filepath):
        """Initializes the explorer with the target HDF5 file."""
        self.filepath = filepath

    def view_visual_memory(self, dataset_path, is_spectrogram=False, is_bgr=True):
        """Displays an image array or spectrogram along with its attributes, with BGR correction."""
        with h5py.File(self.filepath, 'r') as f:
            if dataset_path not in f:
                print(f"Error: Path '{dataset_path}' not found.")
                return
            
            dataset = f[dataset_path]
            data = dataset[:]
            attrs = dict(dataset.attrs)
            
            # --- THE COLOR CORRECTION ---
            # If the image is 3D (height, width, channels) and has 3 channels,
            # we reverse the last dimension to swap BGR to RGB.
            if is_bgr and not is_spectrogram and len(data.shape) == 3 and data.shape[2] == 3:
                data = data[:, :, ::-1] 
            
            #print(f"\n--- Attributes for '{dataset_path}' ---")
            #if attrs:
            #    for k, v in attrs.items():
            #        print(f"{k}: {v}")
            #else:
            #    print("No attributes attached to this dataset.")
            #print("-" * 40)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            plt.subplots_adjust(right=0.7) 
            
            # Spectrograms and single-channel images use grayscale/viridis
            if len(data.shape) == 2 or is_spectrogram:
                ax.imshow(data, cmap='viridis' if is_spectrogram else 'gray')
            else:
                # Standard 3-channel images (now properly formatted as RGB)
                ax.imshow(data)
                
            ax.set_title(f"Memory View: {dataset_path}")
            ax.axis('off')
            
            #if attrs:
            #    attr_text = "Attributes:\n\n" + "\n".join([f"{k}: {v}" for k, v in attrs.items()])
            #else:
            #    attr_text = "No attributes\nattached."
            #    
            #fig.text(0.75, 0.5, attr_text, fontsize=10, va='center', ha='left',
            #         bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgrey', alpha=0.5))
            plt.show()

    def view_memory_links(self, links_dataset_path):
        """
        Visualizes the clustered/linked memories as a network graph.
        Assumes the dataset contains pairs of linked node IDs (e.g., shape (N, 2)).
        """
        
        
        with h5py.File(self.filepath, 'r') as f:
            if links_dataset_path not in f:
                print(f"Error: Links path '{links_dataset_path}' not found.")
                return
            
            # Load the edge connections
            edges = f[links_dataset_path][:]
            
            # Create a network graph
            G = nx.Graph()
            G.add_edges_from(edges)
            
            plt.figure(figsize=(10, 8))
            
            # Generate a layout for the nodes
            pos = nx.spring_layout(G, seed=42) 
            
            # Draw the graph
            nx.draw(G, pos, with_labels=True, node_color='lightblue', 
                    edge_color='gray', node_size=500, font_size=10, font_weight='bold')
            
            plt.title(f"Memory Cluster Links: {links_dataset_path}")
            plt.show()

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    # 1. Initialize with your specific file
    # You can swap this to 'unconsolidatedMemory.h5' to check raw data
    explorer = MemoryExplorer("Unit1/consolidated_memory.h5")

    # 3. View a specific visual frame or spectrogram (Replace with your actual paths)
    # explorer.view_visual_memory("clusters/audio/a_cluster_108/")
    explorer.view_visual_memory("raw_memories/vis_2026-04-15_21-36-03_38")