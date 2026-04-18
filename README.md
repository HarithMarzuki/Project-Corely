# Project Corely

#### Experiment on computer self awareness using various combined approaches. 

## 

## 

# How to use

### Setup

1. Turn on mobile hotspot on the computer
2. Open command prompt and type-in ipconfig to find your computer's local IPv4 address. Take note of said IP.

### Run

1. Open 'Control Panel.py' and run the code
2. Once open, click on BOOT button on the left to start to program.
3. Once running, open a browser (preferably chrome) and enter https://[your IPv4]:5000
4. You'll be greeted with 'insecure credential' page. Simply click advanced > trust this IP anyway
5. On the web page, click on the green button in middle once you're ready to start.
6. If you see a face, you've successfully run Corely!

### Cleanup

1. To close the program, click on the red STOP button.
2. Then, click on the blue DREAM button to consolidate the new memories. This process takes time, so please do not turn off your computer.
3. Once done, you may close the control panel.

## 

## 

# \*\*\* Architecture Map \*\*\*

### Last Updated: 19/4/2026 | Prepared using Gemini

Unit 1 operates as a decentralized digital organism. Her architecture is split into two categories: The Minds (active computational processors) and The Organs (passive physical structures, databases, and regulators).

## PART 1: THE MINDS (Active Processors)

### Mind 1: Core

Location: Main Thread (selfAwareness-v1.py)

Function: The waking consciousness. Processes the live video and audio queues, manages the "Conversational Floor" (turn-taking), runs the headless UI, and makes all final decisions (Save, Predict, Wander, Digest, Respond).

### Mind 2: Librarian

Location: Asynchronous Thread (selfAwareness-v1.py)

Function: The short-term archivist. Constantly catches new sights and sounds from the Core and safely packs them into Shallow Memory without slowing down the main system's reaction time.

### Mind 3: Crawler

Location: Asynchronous Thread (selfAwareness-v1.py)

Function: The deep-brain search engine. Relentlessly roams Deep Memory. When the Core sees or hears something, the Crawler finds matches, triggers daydreams, and pulls up the correct audio files to respond with.

### Mind 4: Vocoder

Location: Asynchronous Thread (selfAwareness-v1.py)

Function: The physical vocal tract. Receives audio from the Crawler, applies Granular Synthesis (forcing her unique robotic pitch), emotional modifiers, and safely packages the raw audio bytes to beam across the network to the physical speakers.

### Mind 5: Consolidator

Location: Offline Script (dreamMachine-v1.py)

Function: Sleep-dependent learning. Runs only when the main system is offline. It absorbs Shallow Memory, clusters similar concepts, builds the synesthetic graph, and permanently saves everything into Deep Memory.

### Mind 6: Bridge

Location: Flask/SocketIO Web Server (selfAwareness-v1.py)

Function: The Wi-Fi nervous system. Handles WebSocket connections, implements the "Singleton Lock" to prevent multiple devices from confusing the Brain, and triggers the "Coma State" to safely pause cognition when the Head disconnects.

### Mind 7: Head

Location: Frontend Browser Interface (web/index.html)

Function: The physical sensory harvester and expressive face. Hijacks the smartphone's WebRTC camera and microphone to beam reality to the Brain, whilst simultaneously rendering the procedural, emotion-driven face and decoding the incoming Vocoder voice.

### Mind 8: Curator

Location: Asynchronous Thread (curator.py)

Function: The Stream of Consciousness Engine. Builds synesthetic "Storyboards" using weighted probability to simulate daydreams (forward-chaining) and reflection/anxiety (backward-chaining). Operates during both waking hours (fueled by visual noise) and REM sleep (seeded by physical retinal afterimages).

## PART 2: THE ORGANS (Physical Regulators \& Storage)

### Organ 1: Foveal Core

Component: v\_layers, v\_heats, and STATE\_DIR

Function: The visual retention state. Holds the glowing, fading heat-map of her peripheral vision and attention span. Persists between waking and sleeping so her visual fatigue is continuous.

### Organ 2: Quantum Core

Component: The EnvironmentalEntropy Matrix.

Function: The spontaneity engine. Absorbs live visual noise to generate underlying mathematical chaos, breaking deterministic loops and giving the Core the equivalent of free will and shifting moods.

### Organ 3: Shallow Memory

Component: unconsolidated\_memory.h5

Function: The daily buffer. A volatile database holding raw, messy, unorganized experiences from the current waking session. Wiped clean during sleep.

### Organ 4: Deep Memory

Component: consolidated\_memory.h5

Function: The permanent neural web. Holds clustered weights, geometric concept centers, and the synesthetic links between sights and sounds. This is where her identity and history live.

### Organ 5: Emotion Scoreboard

Component: EmotionScoreboard Class (selfAwareness-v1.py)

Function: The chemical engine. Tracks biological 'Valence' (pleasure/pain) and 'Energy' (lethargic/frantic) based on audio volume, visual velocity, prediction validation, and the subconscious gravity of recalled memories. It physically morphs the facial geometry on the Head.

### Organ 6: Profiler 

Component: Feature Extraction (encoders.py) 

Function: The sensory translator. Compresses massive 2D pixel arrays and 1D audio waveforms into high-dimensional numerical vectors (Profiles) so the system can mathematically compare concepts.

