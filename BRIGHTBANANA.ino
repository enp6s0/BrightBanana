// clang-format off
/*
 *  _____  _____  ___  _____  __ __  ____  _____  _____  _____  _____  _____  _____
 * /  _  \/  _  \/___\/   __\/  |  \/    \/  _  \/  _  \/  _  \/  _  \/  _  \/  _  \
 * |  _  <|  _  <|   ||  |_ ||  _  |\-  -/|  _  <|  _  ||  |  ||  _  ||  |  ||  _  |
 * \_____/\__|\_/\___/\_____/\__|__/ |__| \_____/\__|__/\__|__/\__|__/\__|__/\__|__/
 *
 * BRIGHTBANANA - RGB LED controller based on an Arduino Uno
 *
 */
// clang-format on
/* ====================================================================================== */

#include <Adafruit_NeoPixel.h>

// Channel pin definitions
#define CHANNEL1_PIN 9
#define CHANNEL2_PIN 10

// Status LED
#define STATUS_LED_PIN 13

// Heartbeat interval (ms)
#define HEARTBEAT_INTERVAL 1000

// Maximum # of LEDs per channel (mostly depends on device memory)
#define MAX_PIXELS_PER_CHANNEL 160

/* ====================================================================================== */

// Buffer space for incoming serial command line
const uint32_t serialBufferMaxSize = (MAX_PIXELS_PER_CHANNEL * 6) + 4;
char serialBuf[serialBufferMaxSize];

// NeoPixel channels
Adafruit_NeoPixel channel1(MAX_PIXELS_PER_CHANNEL, CHANNEL1_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel channel2(MAX_PIXELS_PER_CHANNEL, CHANNEL2_PIN, NEO_GRB + NEO_KHZ800);

/* ====================================================================================== */

// Convert two characters (hex string) into one unsigned 8-bit integer
uint8_t twoCharToInt(char c1, char c2) {
    byte tens = (c1 < '9') ? c1 - '0' : c1 - '7';
    byte ones = (c2 < '9') ? c2 - '0' : c2 - '7';
    byte number = (16 * tens) + ones;
    return (uint8_t)number;
}

// Turn channel off
void channelOff(Adafruit_NeoPixel &channel) {
    channel.clear();
    for (int i = 0; i < MAX_PIXELS_PER_CHANNEL; i++) {
        channel.setPixelColor(i, channel.Color(0, 0, 0));
    }
    channel.show();
}

/* ====================================================================================== */

// Heartbeat
unsigned long previousHeartbeat = 0;
bool ledState = false;
void heartbeat() {
    unsigned long currentTime = millis();
    if (currentTime - previousHeartbeat >= HEARTBEAT_INTERVAL) {
        ledState = !ledState;
        digitalWrite(STATUS_LED_PIN, ledState);
    }
}

/* ====================================================================================== */

void setup() {
    // Status LED pin is output
    pinMode(STATUS_LED_PIN, OUTPUT);

    // Start serial
    Serial.begin(500000);
    Serial.println("INFO,Initializing");

    // Start NeoPixel
    channel1.begin();
    channel2.begin();

    // Turn channels off
    channelOff(channel1);
    channelOff(channel2);

    // Ready
    Serial.println("INFO,Ready");
}

void loop() {

    /*
    Expected serial control format:

    $<channel>,<LED1 color in hex><LED2 color in hex>...<LEDn color in hex>

    i.e.:$0,FFFFFF000000FFFFFF
    sets channel 0 (all channels) LED1 = white, LED2 = off, LED3 = white

    */
    uint32_t serialCount = Serial.readBytesUntil('\n', serialBuf, serialBufferMaxSize);
    uint32_t serialBufferMaxIndex = serialCount - 1;

    // We must at least have the header part to start processing
    if (serialCount >= 3) {
        // Is the first byte our starting byte? ($)
        if (serialBuf[0] == '$') {
            // Figure out channels to work with. If channel is invalid, assume (all)
            Adafruit_NeoPixel *channels[2];
            uint8_t channelCount = 1;
            uint8_t channel = serialBuf[1] - '0';
            if (channel == 1) {
                channels[0] = &channel1;
            } else if (channel == 2) {
                channels[0] = &channel2;
            } else {
                channel = 0;
                channelCount = 2;
                channels[0] = &channel1;
                channels[1] = &channel2;
            }

            // Clear buffer for channel(s) requested
            for (int i = 0; i < channelCount; i++) {
                channels[i]->clear();
            }

            // Now, for each RGB hex...
            uint32_t currentIndex = 3;
            uint32_t ledNumber = 0;

            // We parse the string until we can't parse it anymore
            while (currentIndex <= serialBufferMaxIndex && currentIndex + 5 <= serialBufferMaxIndex &&
                   ledNumber <= (MAX_PIXELS_PER_CHANNEL - 1)) {

                // Read 6 chars from currentIndex to currentIndex + 5
                char thisHex[6] = {0, 0, 0, 0, 0, 0};
                for (int i = 0; i < 6; i++) {
                    thisHex[i] = serialBuf[currentIndex];
                    currentIndex++;
                }

                // Get values for each color
                uint8_t red = twoCharToInt(thisHex[0], thisHex[1]);
                uint8_t green = twoCharToInt(thisHex[2], thisHex[3]);
                uint8_t blue = twoCharToInt(thisHex[4], thisHex[5]);

                // Set pixel color for channel(s) requested
                for (int i = 0; i < channelCount; i++) {
                    channels[i]->setPixelColor(ledNumber, channels[i]->Color(red, green, blue));
                }

                // Increment LED number and move right along
                ledNumber++;
            }

            // Let those colors out
            for (int i = 0; i < channelCount; i++) {
                channels[i]->show();
            }

            // Send acknowledgement
            Serial.print("OK,");
            Serial.print(channel);
            Serial.print(",");
            Serial.print(ledNumber);
            Serial.print(",");
            Serial.println(micros());
        } else {
            Serial.println("ERROR,InvalidCmd,NoStartFlag");
        }
    } else if (serialCount != 0) {
        Serial.println("ERROR,InvalidCmd,TooShort");
    }

    // Run the heartbeat loop, too
    heartbeat();
}
