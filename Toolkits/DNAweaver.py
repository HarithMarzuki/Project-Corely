import numpy as np
import scipy.linalg

# Create a 300-length sequence
col = np.random.rand(300)
row = np.random.rand(300)

# Generate the 300x300 Toeplitz matrix
dna_matrix = scipy.linalg.toeplitz(col, row)

# Save to gene.txt (Comma separated)
np.savetxt("gene.txt", dna_matrix, delimiter=",", fmt="%.6f")
print("gene.txt successfully created! Unit 1's DNA is ready.")