// Kisan Cold Link — ESP32 chamber node (ADR-024)
//
// Sensors (same wiring as the original sketch):
//   DHT11   on GPIO 4  -> chamber air temperature + humidity
//   DS18B20 on GPIO 5  -> coil / heat-sink water temperature (cooling loop)
//   Pump relay/driver on GPIO 18
//
// Every 5 s it POSTs readings to the backend and GETs the pump state it should apply.
// The backend decides ON/OFF (manual from the admin portal, or its auto thermostat).
// If Wi-Fi or the backend is unreachable, the pump KEEPS its last state.
//
// Libraries: "DHT sensor library" (Adafruit), "OneWire", "DallasTemperature". WiFi/HTTPClient come with the ESP32 core.

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------- EDIT THESE ----------
const char* WIFI_SSID     = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
// Laptop running the backend: its Wi-Fi IP and API port (start it with API_HOST=0.0.0.0, see README).
const char* BACKEND_URL   = "http://192.168.1.100:8000/api/v1";
// Must equal DEVICE_KEY in backend/.env
const char* DEVICE_KEY    = "PASTE_DEVICE_KEY_HERE";
// ---------------------------------

#define DHT_PIN 4
#define DHT_TYPE DHT11
#define DS18B20_PIN 5
#define MOTOR_PIN 18

const unsigned long SEND_INTERVAL_MS = 5000;
const unsigned long POLL_INTERVAL_MS = 5000;
const unsigned long HTTP_TIMEOUT_MS  = 4000;

DHT dht(DHT_PIN, DHT_TYPE);
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);

bool motorState = false;
unsigned long lastSend = 0;
unsigned long lastPoll = 2500;  // offset so send and poll don't run in the same loop

void setPump(bool on) {
  if (on != motorState) {
    motorState = on;
    digitalWrite(MOTOR_PIN, on ? HIGH : LOW);
    Serial.println(on ? "PUMP: ON" : "PUMP: OFF");
  }
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  Serial.print("Connecting to Wi-Fi");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(WiFi.status() == WL_CONNECTED ? "\nWi-Fi connected, IP: " + WiFi.localIP().toString()
                                                : "\nWi-Fi not connected; pump keeps last state");
}

// The backend replies {"pump_on": true|false, ...}; a tiny search avoids a JSON library.
void applyCommand(const String& body) {
  if (body.indexOf("\"pump_on\":true") >= 0) setPump(true);
  else if (body.indexOf("\"pump_on\":false") >= 0) setPump(false);
}

String jsonNumber(float v) {
  return isnan(v) ? String("null") : String(v, 2);
}

void sendTelemetry(float airTemp, float humidity, float waterTemp) {
  String body = "{\"chamber_temp_c\":" + jsonNumber(airTemp) +
                ",\"humidity_pct\":" + jsonNumber(humidity) +
                ",\"coil_temp_c\":" + (waterTemp == DEVICE_DISCONNECTED_C ? String("null") : jsonNumber(waterTemp)) +
                ",\"pump_on\":" + (motorState ? "true" : "false") +
                ",\"uptime_s\":" + String(millis() / 1000) + "}";
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(String(BACKEND_URL) + "/device/telemetry");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.POST(body);
  if (code == 200) applyCommand(http.getString());
  else Serial.printf("Telemetry failed (HTTP %d)\n", code);
  http.end();
}

void pollCommand() {
  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  http.begin(String(BACKEND_URL) + "/device/command");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.GET();
  if (code == 200) applyCommand(http.getString());
  else Serial.printf("Command poll failed (HTTP %d)\n", code);
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  dht.begin();
  ds18b20.begin();
  Serial.println("\n=== Kisan Cold Link (Wi-Fi) ===");
  connectWifi();
}

void loop() {
  unsigned long now = millis();

  if (now - lastSend >= SEND_INTERVAL_MS) {
    lastSend = now;
    float humidity = dht.readHumidity();
    float airTemp = dht.readTemperature();
    ds18b20.requestTemperatures();
    float waterTemp = ds18b20.getTempCByIndex(0);

    Serial.printf("Chamber %.1f C | Humidity %.0f %% | Coil %.1f C | Pump %s\n",
                  airTemp, humidity, waterTemp, motorState ? "ON" : "OFF");
    connectWifi();
    if (WiFi.status() == WL_CONNECTED) sendTelemetry(airTemp, humidity, waterTemp);
  }

  if (now - lastPoll >= POLL_INTERVAL_MS) {
    lastPoll = now;
    if (WiFi.status() == WL_CONNECTED) pollCommand();
  }
}
