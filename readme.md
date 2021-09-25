# BrightBanana
RGB LED controller based on an Arduino Uno and NeoPixel (WS2812) LED strips

### Using BrightBanana
* Install Adafruit's NeoPixel [library](https://github.com/adafruit/Adafruit_NeoPixel)
* Load this code onto an Arduino. This code is written specifically for the Uno, but should work on other models as well.
* Two channels (channel 1, channel 2) are supported on pins 9 and 10, respectively
* Send command strings through serial at `500000 baud` to specify what LED should light up, and what color should it be
    * Command string begins with the flag `$`, followed by channel number `(0, 1, 2)` with channel `0` having a special meaning of "all channels", and a comma (`,`).
    * Colors will then follow in hex string format, one LED at a time. Capitalization does not matter.

### Command examples
Set LED 1 on all channels to white:
```
$0,FFFFFF
```

On channel 1, set LED 1 to white, LED2 off, LED3 to red:
```
$1,FFFFFF000000FF0000
```

### Known issues
* Repeatedly sending command strings that is too long will eventually result in the Arduino locking up (probably due to bad buffer disclipine)

### License
MIT; see license.md for more info
