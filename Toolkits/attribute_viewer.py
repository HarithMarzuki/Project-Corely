import h5py
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

class MemoryExplorer:
    def __init__(self, filepath):
        """Initializes the explorer with the target HDF5 file."""
        self.filepath = filepath

    def print_structure(self, output_file=None):
        """
        Outputs the hierarchical structure of the HDF5 file, including attributes.
        If output_file is provided, it writes to the file. Otherwise, it prints to the terminal.
        """
        def process_node(name, obj):
            indent = "  " * name.count('/')
            output_lines = []
            
            if isinstance(obj, h5py.Dataset):
                output_lines.append(f"{indent}Dataset: {name.split('/')[-1]} | Shape: {obj.shape} | Type: {obj.dtype}")
            elif isinstance(obj, h5py.Group):
                output_lines.append(f"{indent}Group: {name.split('/')[-1]}/")
            
            # Extract and format attributes if they exist
            if obj.attrs:
                output_lines.append(f"{indent}  Attributes:")
                for key, val in obj.attrs.items():
                    output_lines.append(f"{indent}    - {key}: {val}")
                    
            return "\n".join(output_lines)

        with h5py.File(self.filepath, 'r') as f:
            if output_file:
                with open(output_file, 'w') as txt_file:
                    txt_file.write(f"--- Structure and Attributes of {self.filepath} ---\n")
                    
                    # The fix: This function explicitly returns None to keep the loop going
                    def write_to_file(name, obj):
                        result = process_node(name, obj)
                        if result:
                            txt_file.write(result + "\n")
                        return None 
                        
                    f.visititems(write_to_file)
                    txt_file.write("-" * 50 + "\n")
                print(f"Success: Structure and attributes exported to '{output_file}'")
            else:
                print(f"--- Structure and Attributes of {self.filepath} ---")
                
                def print_to_terminal(name, obj):
                    result = process_node(name, obj)
                    if result:
                        print(result)
                    return None
                    
                f.visititems(print_to_terminal)
                print("-" * 50)

    def view_visual_memory(self, dataset_path, is_spectrogram=False):
        """Displays an image array or spectrogram along with its attributes."""
        with h5py.File(self.filepath, 'r') as f:
            if dataset_path not in f:
                print(f"Error: Path '{dataset_path}' not found.")
                return
            
            dataset = f[dataset_path]
            data = dataset[:]
            attrs = dict(dataset.attrs)
            
            print(f"\n--- Attributes for '{dataset_path}' ---")
            if attrs:
                for k, v in attrs.items():
                    print(f"{k}: {v}")
            else:
                print("No attributes attached to this dataset.")
            print("-" * 40)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            plt.subplots_adjust(right=0.7) 
            
            if len(data.shape) == 2 or is_spectrogram:
                ax.imshow(data, cmap='viridis' if is_spectrogram else 'gray')
            else:
                ax.imshow(data)
                
            ax.set_title(f"Memory View: {dataset_path}")
            ax.axis('off')
            
            if attrs:
                attr_text = "Attributes:\n\n" + "\n".join([f"{k}: {v}" for k, v in attrs.items()])
            else:
                attr_text = "No attributes\nattached."
                
            fig.text(0.75, 0.5, attr_text, fontsize=10, va='center', ha='left',
                     bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgrey', alpha=0.5))
            plt.show()

    def view_memory_links(self, links_dataset_path):
        """Visualizes the clustered memories as a network graph."""
        with h5py.File(self.filepath, 'r') as f:
            if links_dataset_path not in f:
                print(f"Error: Links path '{links_dataset_path}' not found.")
                return
            
            edges = f[links_dataset_path][:]
            
            G = nx.Graph()
            G.add_edges_from(edges)
            
            plt.figure(figsize=(10, 8))
            pos = nx.spring_layout(G, seed=42) 
            nx.draw(G, pos, with_labels=True, node_color='lightblue', 
                    edge_color='gray', node_size=500, font_size=10, font_weight='bold')
            
            plt.title(f"Memory Cluster Links: {links_dataset_path}")
            plt.show()

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    explorer = MemoryExplorer("Unit1/consolidated_memory.h5")

    # Pass a filename to export to a .txt file
    explorer.print_structure(output_file="C:/Users/admin/Desktop/Project Corely/Checkers/consolidated_structure.txt")
    
    # Or call it empty to print to the terminal
    # explorer.print_structure()