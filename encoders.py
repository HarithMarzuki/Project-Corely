import numpy as np

def get_visual_profile(image_array):
    """
    Squashes a Fovea image into a 3D visual signature, normalized 
    so that dull rooms and bright rooms can be compared by 'shape' 
    rather than absolute brightness.
    """
    img = image_array.astype(np.float32)
    res = []
    
    # Calculate raw energy for Red, Green, and Blue
    for c in (2, 1, 0):
        res.append(float(np.sum(img[:, :, c] ** 2)))
        
    # Dynamic Scaling (L2 Normalization)
    res_array = np.array(res)
    norm = np.linalg.norm(res_array)
    if norm > 0:
        res_array = res_array / norm
        
    return res_array.tolist()


def get_audio_profile(audio_basket):
    """
    "Shadow Encoding" - Translates a raw audio stick into a 3D concept.
    X: Forward Shadow (Attack/Onset Shape)
    Y: Backward Shadow (Decay/Tail Shape)
    Z: Acoustic Roughness (Timbre/Chaos)
    """
    audio = np.array(audio_basket, dtype=np.float32).flatten()
    
    # Safety Check: If the basket is empty or too small, return zero-concept
    if len(audio) < 20: 
        return [0.0, 0.0, 0.0]

    # 1. Energy Normalization (Loudness Invariance)
    std_val = np.std(audio)
    if std_val < 1e-6: # Prevent division-by-zero on pure digital silence
        return [0.0, 0.0, 0.0]
    
    norm_audio = audio / std_val

    # 2. The Microscope (Downsampling to steepen the physical wave slopes)
    mini_audio = norm_audio[::10]

    # 3. Positive Shift (Lift everything above zero)
    shifted = mini_audio + 2.0

    # 4. Proportions (The Derivative / Shape Matrix)
    numerators = shifted[:-1]
    denominators = shifted[1:]
    proportions = numerators / denominators
    
    N = len(proportions)
    if N == 0: return [0.0, 0.0, 0.0]

    # 5. The Gaussian Fovea (Dynamic Bell Curve)
    # We set the 'spread' so the curve decays to roughly 1% at the very end of the sound
    spread = max(1.0, N / 3.0) 
    distances = np.arange(N)
    
    # Create the weights
    weights_forward = np.exp(-0.5 * (distances / spread) ** 2)
    weights_backward = weights_forward[::-1] # Flip the curve for the tail

    # 6. Cast the Shadows & Squash (Duration Invariance via division by N)
    X = float(np.sum(proportions * weights_forward) / N)
    Y = float(np.sum(proportions * weights_backward) / N)
    
    # 7. Acoustic Roughness
    Z = float(np.std(proportions))

    return [X, Y, Z]