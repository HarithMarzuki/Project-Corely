# Project Corely

#### Project Corely is an experimental AI architecture that models consciousness not as a single loop, but as a biological system. Unit 1 - Corely is split into two distinct categories: The Minds (active, asynchronous computational threads) and The Organs (passive physical structures, mathematical regulators, and hierarchical databases).

#### Everything is monitored and controlled via the Incubator—a retro-styled, zero-lag diagnostic dashboard.

## 
## 

# System Requirements

**Minimum**

- OS: Windows 10 64-bit
- Processor: Intel Core i3 or AMD Ryzen 3
- Memory: 8 GB RAM
- Graphics: NVIDIA GeForce GTX 1050 or equivalent with CUDA support, 2 GB VRAM
- Storage: 5 GB available space
- Network: Local Wi-Fi or LAN connection
- Additional Notes: Requires a smartphone or secondary device with a modern browser, camera, and microphone

**Recommended**

- OS: Windows 11 64-bit
- Processor: Intel Core i5 or AMD Ryzen 5
- Memory: 16 GB RAM
- Graphics: NVIDIA GeForce GTX 1660, RTX 2060, or better with 4 GB+ VRAM and CUDA support
- Storage: SSD with 10 GB available space
- Network: Stable local Wi-Fi or LAN connection
- Additional Notes: Recent smartphone with Chrome or Safari recommended for best camera/audio compatibility

**Important**

- An NVIDIA CUDA-capable GPU is required for the current build.
- Project Corely requires two devices in normal use:
  - a Windows host machine running the core and control panel
  - a phone or second device acting as the sensory head through the browser
- Performance may degrade as memory files grow over time.

##
##

# How to use

### Setup

1. Connect your phone onto your local network.
2. Run ipconfig in your computer's terminal and take note of your device's IPv4 address

### Run

1. Open 'Control Panel.py' and run the code
2. Once open, click on the green BOOT button on the left to start to program.
3. Once running, open a browser (preferably chrome) and enter https://[your IPv4]:5000
4. You'll be greeted with 'insecure credential' page. Simply click advanced > trust this IP anyway
5. On the web page, click on the green button in middle once you're ready to start.
6. If you see a face, you've successfully run Corely!

### Cleanup

1. To close the program, click on the red STOP button.
2. Then, click on the blue DREAM button to consolidate the new memories. This process takes time, so please do not turn off your computer.
3. Once done, you may close the control panel.

OR

1. Click on yellow SLEEP button to immediately stop the program and start consolidating new memories right away.

##
##

# Control Panel explanation:

1. Three 'BANASONIC' TVs at the top: these are Corely's visions.
    - left: raw vision
    - middle: foveal vision. 
    - right: mind's vision (vision of her memory)

2. left box with buttons and a switch
    - Telemetry switch: switch for displaying the telemetry. Is it switched on by default.
    - Green button: Boot button, to start the program
    - Red button: Stop button, to stop the program
    - Blue button: Dream button, to consolidate new memories after running
    - Yellow button: Sleep button, to stop the program and immediately start dreaming

3. Middle 'MACARONI' monitor
    - Display the system messages from the program

4. Right box with bars and lights
    - Top: action monitor, display what is going on in Corely's brain
    - Middle: emotion monitor, display the emotional state of Corely
    - Bottom: Minds monitor, display which minds are active. The list of minds are:
        a. M1 -> Core
        b. M2 -> Librarian
        c. M3 -> Crawler
        d. M4 -> Vocoder
        e. M5 -> Consolidator
        f. M6 -> Bridge
        g. M7 -> Face
        h. M8 -> Curator

# Toolkits explanation
1. attribute_viewer.py
    - This is for you to view the structure of the memories and its attributes. more sophisticated version of this will come in the future.
2. DNAweaver.py
    - Project Corely utilises the camera and a toeplitz matrix as its randomizer when awake. DNAweaver is for you to generate a fixed toeplitz matrix for the program to use.
    - Without the fixed toeplitz matric, the program would generate its own toeplitz matrix at the start of the program. 


