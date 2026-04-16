# Project Corely

#### Experiment on computer self awareness using various combined approaches

#### Please do not ask what are the combined approaches are since I designed the architecture by instinct alone and have Gemini vibecoded the idea

## 

## 

# How to use

### Setup

1. Turn on mobile hotspot on the computer
2. Open command prompt and type-in ipconfig to find the computer's local IP address. Take note of this IP. This computer's default should be 192.168.137.1

### Run

1. Open 'selfAwarenessDelta3-1.py' and run the code
2. Once running, open a browser (preferably chrome) and enter https://192.168.137.1:5000 (use your acquired IP address)
3. You'll be greeted with 'insecure credential' page. Simply click advanced > trust this IP anyway
4. On the web page, click on the green button in middle once you're ready to start.
5. If you see a face, you've successfully run Corely!

### Cleanup

1. To close the program, you can either click the X button on the dashboard on the computer, or close the tab on the browser. Both ways work.
2. Once everything is nicely stopped, open 'dreamMachine2-1.py' to consolidate her new memories.

## 

## 

# \*\*\* Architecture Map \*\*\*

### Last Updated: 7/4/2026 | Prepared using Gemini

Unit 1 operates as a decentralized digital organism. Her architecture is split into two categories: The Minds (active computational processors) and The Organs (passive physical structures, databases, and regulators).

## PART 1: THE MINDS (Active Processors)

### Mind 1: Core

Location: Main Thread (selfAwareness.py)

Function: The waking consciousness. Processes the live video and audio queues, manages the "Conversational Floor" (turn-taking), runs the headless UI, and makes all final decisions (Save, Predict, Wander, Digest, Respond).

### Mind 2: Profiler

Location: Feature Extraction (encoders.py)

Function: The sensory translator. Compresses massive 2D pixel arrays and 1D audio waveforms into high-dimensional numerical vectors (Profiles) so the system can mathematically compare concepts.

### Mind 3: Librarian

Location: Asynchronous Thread (selfAwarenessDelta3-1.py)

Function: The short-term archivist. Constantly catches new sights and sounds from the Core and safely packs them into Shallow Memory without slowing down the main system's reaction time.

### Mind 4: Crawler

Location: Asynchronous Thread (selfAwarenessDelta3-1.py)

Function: The deep-brain search engine. Relentlessly roams Deep Memory. When the Core sees or hears something, the Crawler finds matches, triggers daydreams, and pulls up the correct audio files to respond with.

### Mind 5: Vocoder

Location: Asynchronous Thread (selfAwarenessDelta3-1.py)

Function: The physical vocal tract. Receives audio from the Crawler, applies Granular Synthesis (forcing her unique robotic pitch), emotional modifiers, and safely packages the raw audio bytes to beam across the network to the physical speakers.

### Mind 6: Consolidator

Location: Offline Script (dreamMachineDelta3.py)

Function: Sleep-dependent learning. Runs only when the main system is offline. It absorbs Shallow Memory, clusters similar concepts, builds the synesthetic graph, and permanently saves everything into Deep Memory.

### Mind 7: Bridge

Location: Flask/SocketIO Web Server (selfAwarenessDelta3-1.py)

Function: The Wi-Fi nervous system. Handles WebSocket connections, implements the "Singleton Lock" to prevent multiple devices from confusing the Brain, and triggers the "Coma State" to safely pause cognition when the Head disconnects.

### Mind 8: Head

Location: Frontend Browser Interface (web/index.html)

Function: The physical sensory harvester and expressive face. Hijacks the smartphone's WebRTC camera and microphone to beam reality to the Brain, whilst simultaneously rendering the procedural, emotion-driven face and decoding the incoming Vocoder voice.

### Mind 9: Curator

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

Component: EmotionScoreboard Class (selfAwarenessDelta3-1.py)

Function: The chemical engine. Tracks biological 'Valence' (pleasure/pain) and 'Energy' (lethargic/frantic) based on audio volume, visual velocity, prediction validation, and the subconscious gravity of recalled memories. It physically morphs the facial geometry on the Head.

