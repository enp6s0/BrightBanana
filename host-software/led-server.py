#!/usr/bin/python3
import serial, time, redis, os, sys, threading

# ================================================================================
# Initialization
# ================================================================================

sys.stdout.write(f"\nLEDserver v1.0 starting at timestamp {int(time.time())}\n\n")

# Figure out what serial port will we be using?
serialPortName = "/dev/ttyACM0"
try:
    serialPortName = str(os.environ["SERIAL_PORT"])
except:
    pass
sys.stdout.write(f"Using serial port: {serialPortName}\n")

# Actually open the serial port
serialPort = serial.Serial(port = serialPortName, baudrate=1000000, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)

# How many LEDs do we have?
ledCount = 33
try:
    ledCount = int(str(os.environ["NUM_LEDS"]))
except:
    pass
sys.stdout.write(f"Total number of LEDs: {ledCount}\n")

# Redis
r = redis.Redis(host = "127.0.0.1")
sys.stdout.write(f"Redis connection complete: {int(time.time())}\n")

# How long to sleep after each iteration (controls speed)
sleep = 0.08

# ================================================================================
# Helper functions
# ================================================================================

def buildBlendingMap(colors, blendSteps):
    """
    Create color blending map
    """
    # Create blending maps
    blendingMap = []

    if(blendSteps > 0 and blendSteps % 2 == 0):
        for i, color in enumerate(colors):

            # We want to blend this and next color
            nextColor = colors[(i + 1) % len(colors)]

            # Get ints for each channel
            channels = {
                "red": [int(color[0:2], 16), int(nextColor[0:2], 16)],
                "green": [int(color[2:4], 16), int(nextColor[2:4], 16)],
                "blue": [int(color[4:6], 16), int(nextColor[4:6], 16)]
            }

            # Get difference for each channel
            channelStepping = {}

            for color in channels:
                channel = channels[color]

                start = channel[0]
                end = channel[1]

                difference = channel[1] - channel[0]

                # Find stepping
                step = round(difference / blendSteps)
                steps = []
                currentValue = start
                for i in range(blendSteps):
                    currentValue += step

                    # Bounding
                    if((currentValue > end and step > 0) or (currentValue < end and step < 0)):
                        currentValue = end

                    steps.append(currentValue)

                channelStepping[color] = steps

            #print(f"{i} - {color} - {nextColor}")
            blendColors = []
            for i in range(blendSteps):
                red = format(channelStepping['red'][i], "02x")
                green = format(channelStepping['green'][i], "02x")
                blue = format(channelStepping['blue'][i], "02x")
                blendColors.append(f"{red}{green}{blue}".upper())

            blendingMap.append(blendColors)

    return blendingMap

def buildColorList(colors, blend = 4, block = 16):
    """
    Given a list of hex-formatted colors, build the complete RGB list that
    can be passed to BrightBanana for rendering. Also does blending of colors!

    Blend -> blending steps. MUST be divisible by 2. A value of 0 disables blending.
    Block -> size of each color's "block"

    Note: this will return a "complete" list that may overflow the number of LEDs.
          The LED driver function should handle "windowing" as needed!
    """

    # Get color blending map
    blendingMap = buildBlendingMap(colors, blend)

    # Resize color to blocks as needed
    bigColors = []
    for colorID, color in enumerate(colors):

        # Make section bigger
        for i in range(block):
            bigColors.append(color)

        # Append blending... if enabled
        if(blend > 0 and blend % 2 == 0):
            blendThis = blendingMap[colorID]
            bigColors.extend(blendThis)

    return bigColors


# Small embedded helper function to get the 5-tuple config value
# (validity, colorList, sleepTime, blendSteps, blockSize)
def ledConfig():

    # Read these from Redis...
    colorList = r.get("colors").decode("utf-8")
    sleepTime = r.get("sleep").decode("utf-8")
    blendSteps = r.get("blend").decode("utf-8")
    blockSize = r.get("block").decode("utf-8")

    # Make sure we can parse it (valid?)
    try:
        # Get colors and make sure this works
        if(colorList is None):
            raise Exception("No color list given")
        inColors = str(colorList).upper().split(",")
        for color in inColors:
            test = int(color, 16)
        colorList = inColors

        # Sleep time must be float(able)
        sleepTime = float(sleepTime)

        # Blend steps must be an integer, more than or equal to 0, divisible by two
        blendSteps = int(blendSteps)
        if(blendSteps < 0 or blendSteps % 2 != 0):
            raise Exception(f"Invalid blend steps: {blendSteps}")

        # Block size must be POSITIVE integer
        blockSize = int(blockSize)
        if(blockSize < 1):
            raise Exception(f"Invalid block size: {blockSize}")

        return (True, colorList, sleepTime, blendSteps, blockSize)
    except Exception as e:
        print(f"Config parser exception: {e}")
        return (False, None, None, None, None)

# ================================================================================
# LED driver thread
# ================================================================================
def ledThread():
    # Get initial color list
    currentColors = clist
    currentSleep = sleep

    # "One Infinite Loop"
    while True:
        print(f"LEDthread: process loop start at {int(time.time())}")

        # Find max color index
        maxColorIndex = len(currentColors) - 1
        print(f"\t -> Max index: {maxColorIndex}")

        # Create color list
        colorList = []
        colorIndex = 0
        for x in range(ledCount):
            if(colorIndex > maxColorIndex):
                colorIndex = 0
            colorList.append(currentColors[colorIndex])
            colorIndex += 1
        newColorIndex = 0

        # Colorizer loop
        while True:

            # Reset new color index if it gets too high
            if(newColorIndex > maxColorIndex):
                newColorIndex = 0

            # We insert this into list
            colorList.insert(0, currentColors[newColorIndex])
            colorList = colorList[0:ledCount]

            # Create BRIGHTBANANA serial string and send it out
            serialString = f"$0|{''.join(colorList)}\n"
            serialPort.write(bytes(serialString, "utf-8"))
            #print(f"Time: {time.perf_counter()}")

            # Also read to prevent the serial buffer from getting full
            time.sleep(0.001)
            inp = serialPort.readline()
            #print(f"\t{inp}")

            time.sleep(currentSleep)
            newColorIndex += 1

            # If color list changed, update and break inner loop so we
            # can reinitialize ourselves
            if(clist != currentColors or (sleep != currentSleep)):
                currentColors = clist
                currentSleep = sleep
                print(f"LEDthread: Color list or speed changed at {int(time.time())}")
                break

# ================================================================================
# Redis monitor thread
# ================================================================================
def busThread():
    global clist
    global sleep

    # Get initial config
    runningConfig = ledConfig()
    print(f"BusThread: Loaded initial configuration from bus at {int(time.time())}: {runningConfig}")

    # First run variable
    firstRun = True

    while True:

        # Get new config and check if it's valid or not
        newConfig = ledConfig()
        if(newConfig[0] == True):
            # Valid new config! Is it the same?
            if(runningConfig != newConfig or firstRun):
                # New configuration detected!
                # (validity, colorList, sleepTime, blendSteps, blockSize)
                colors = ["FF00FF", "000000", "000000", "000000", "000000", "000000", "000000", "000000", "000000"]
                clist = buildColorList(colors = newConfig[1], blend = newConfig[3], block = newConfig[4])
                sleep = newConfig[2]

                # Make sure we don't repeatedly apply this...
                runningConfig = newConfig
                firstRun = False

                print(f"BusThread: Loaded new configuration from bus at {int(time.time())}: {runningConfig}")

        time.sleep(0.1)

# ================================================================================
# Default colors
# ================================================================================
colors = ["FF00FF", "000000", "000000", "000000", "000000", "000000", "000000", "000000", "000000"]
clist = buildColorList(colors, blend = 2, block = 2)

# ================================================================================
# Main thread
# ================================================================================

if __name__ == "__main__":
    # Start LED processing thread
    lt = threading.Thread(target = ledThread)
    lt.start()

    # Start bus monitoring thread
    bt = threading.Thread(target = busThread)
    bt.start()

    # Keep main thread running
    while True:
        time.sleep(1)
