#include <WiFi.h>
#include <WiFiUdp.h>
#include <ESP32Servo.h>

// ========== WIFI CONFIG ==========
const char* ssid = "iPhone";
const char* password = "11111111";

WiFiUDP udp;
const int udpPort = 4210;

// ========== SERVOS ==========
Servo servoX;
Servo servoY;
Servo servoZ;
Servo servoClaw;

// ========== PINS ==========
#define PIN_X     12
#define PIN_Y     13
#define PIN_Z     14
#define PIN_CLAW  27

// default positions
int default_angle[4] = {75, 35, 90, 30};

// received buffer
uint8_t angle[4];
uint8_t last_angle[4];

unsigned long lastReceiveTime = 0;

void setup() {
  Serial.begin(115200);

  // attach servos (ESP32 PWM safe)
  servoX.attach(PIN_X, 500, 2400);
  servoY.attach(PIN_Y, 500, 2400);
  servoZ.attach(PIN_Z, 500, 2400);
  servoClaw.attach(PIN_CLAW, 500, 2400);

  // init positions
  servoX.write(default_angle[0]);
  servoY.write(default_angle[1]);
  servoZ.write(default_angle[2]);
  servoClaw.write(default_angle[3]);

  memcpy(last_angle, default_angle, 4);

  // WIFI CONNECT
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  udp.begin(udpPort);
}

void loop() {

  int packetSize = udp.parsePacket();

  if (packetSize >= 4) {
    udp.read(angle, 4);
    lastReceiveTime = millis();

    // SERVO 0 -> X (0-180)
    if (angle[0] != last_angle[0]) {
      servoX.write(angle[0]);
      last_angle[0] = angle[0];
    }

    // SERVO 1 -> Y (0-70 but limited later)
    if (angle[1] != last_angle[1]) {
      servoY.write(angle[1]);
      last_angle[1] = angle[1];
    }

    // SERVO 2 -> Z (0-180)
    if (angle[2] != last_angle[2]) {
      servoZ.write(angle[2]);
      last_angle[2] = angle[2];
    }

    // CLAW (0-90)
    if (angle[3] != last_angle[3]) {
      servoClaw.write(angle[3]);
      last_angle[3] = angle[3];
    }
  }

  // SAFE MODE (no signal)
  if (millis() - lastReceiveTime > 1000) {
    servoX.write(default_angle[0]);
    servoY.write(default_angle[1]);
    servoZ.write(default_angle[2]);
    servoClaw.write(default_angle[3]);
  }
}