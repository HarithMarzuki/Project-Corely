import numpy as np
import scipy.linalg
import time

# Create a 300-length sequence
col = np.random.rand(300)
row = np.random.rand(300)

print("Welcome to the DNA weaver, where you generate fixed toeplitz matrix for Corely's randomizer")
print('\nIMPORTANT: You\'ll need to move the generated gene.txt later manually to \'Project Corely/Unit 1\'')
print('\nEnter:\n\t1-> to generate the matrix\n\t2 -> to cancel and close the program')
choice = input('input: ')

if choice == '1':
    # Generate the 300x300 Toeplitz matrix
    dna_matrix = scipy.linalg.toeplitz(col, row)

    # Save to gene.txt (Comma separated)
    np.savetxt("gene.txt", dna_matrix, delimiter=",", fmt="%.6f")
    print("gene.txt successfully created! Unit 1's DNA is ready.")
elif choice == '2':
    print('gene.txt generation canceled')
    time.sleep(3)
else:
    print('Error! Please restart the program')
    time.sleep(3)