#!/usr/bin/python3
# /dev/ttyACM1
import serial
import time

serialPort = serial.Serial(port = "/dev/ttyACM0", baudrate=1000000, bytesize=8, timeout=2, stopbits=serial.STOPBITS_ONE)

# LED color "block" size
blockSize = 8

# How many LEDs?
leds = 33

# How long to sleep after each iteration (controls speed)
sleep = 0.06

# Set color blending steps. This must be divisible by 2.
# A value of 0 disables color blending.
blendSteps = 4

# ============================================================================== #

colors = ["FF0000", "FFA500", "FFFF00", "00FF00", "0000FF", "4B0082"]

# Create blending maps
if(blendSteps > 0 and blendSteps % 2 == 0):
    blendingMap = []
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


colorsNew = []
for colorID, color in enumerate(colors):

    # Make section bigger
    for i in range(blockSize):
        colorsNew.append(color)

    # Append blending... if enabled
    if(blendSteps > 0):
        blendThis = blendingMap[colorID]
        colorsNew.extend(blendThis)

colors = colorsNew
maxColorIndex = len(colors) - 1

# Create color list
colorList = []
colorIndex = 0
for x in range(leds):
    if(colorIndex > maxColorIndex):
        colorIndex = 0
    colorList.append(colors[colorIndex])
    colorIndex += 1

newColorIndex = 0
while(True):

    # Reset new color index if it gets too high
    if(newColorIndex > maxColorIndex):
        newColorIndex = 0

    # We insert this into list
    colorList.insert(0, colors[newColorIndex])
    colorList = colorList[0:leds]

    serialString = f"$0|{''.join(colorList)}\n"
    serialPort.write(bytes(serialString, "utf-8"))
    print(f"Time: {time.perf_counter()}")

    # Also read to prevent the serial buffer from getting full
    time.sleep(0.001)
    inp = serialPort.readline()
    print(f"\t{inp}")

    time.sleep(sleep)

    newColorIndex += 1