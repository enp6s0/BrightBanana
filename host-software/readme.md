# BRIGHTBANANA host software
A simple Python script that is designed to be run as a daemon (perhaps using `supervisord`) to control BRIGHTBANANA RGB LED systems.

Currently, this only supports a single mode of operation: `rainbow` (endless loop of colors). TODO: add more modes.

### Prerequisites
Python `>= 3.6`, Redis server, and the Python Redis library.

### HOWTO?
After installing all the prerequisites (`pip3 install -r requirements.txt`) and setting up the server software to run as a service (the environment variables `SERIAL_PORT` and `NUM_LEDS` are your friend here), the LEDs can be controlled through setting, as of v1.0, four Redis keys:

    * `colors`  : (string) comma separated, hex-formatted list of colors in the "rainbow".
    * `sleep`   : (float)  time to sleep between each step, in seconds. This controls the rainbow speed.
    * `blend`   : (int)    number of "blending" steps to use between colors to make the rainbow look smoother. MUST be divisible by 2 and non-negative. Set to `0` to disable blending entirely.
    * `block`   : (int)    size of each block of colors. Use this to make each color band wider or narrower.

If any of the values are invalid on startup, the software defaults to a small magenta band to indicate an error condition. If the values are valid on startup, but later an invalid value is passed to the software, it is simply ignored.
