#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>

#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>

#include "secrets.h"

// ESP32-C6-Zero / BME280 I2C Pins
#define I2C_SDA 4
#define I2C_SCL 5

// BME280 I2C-Adressen
#define BME280_ADDRESS_PRIMARY 0x77
#define BME280_ADDRESS_SECONDARY 0x76

// Sendeintervall
const unsigned long SEND_INTERVAL_MS = 60000;

Adafruit_BME280 bme;

unsigned long lastSendAt = 0;


const char* getCollectorUrl() {
  if (USE_CLOUD) {
    return CLOUD_COLLECTOR_URL;
  }

  return LOCAL_COLLECTOR_URL;
}


const char* getCollectorToken() {
  if (USE_CLOUD) {
    return CLOUD_COLLECTOR_TOKEN;
  }

  return "";
}


void connectToWifi() {
  Serial.print("Verbinde mit WLAN: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 20000) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WLAN-Verbindung fehlgeschlagen. Neustart in 5 Sekunden...");
    delay(5000);
    ESP.restart();
  }

  Serial.println("WLAN verbunden.");
  Serial.print("IP-Adresse: ");
  Serial.println(WiFi.localIP());
}


void setupBme280() {
  Serial.println("--- BME280 Initialisierung ---");

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!bme.begin(BME280_ADDRESS_PRIMARY, &Wire)) {
    Serial.println("Sensor nicht gefunden auf 0x77, teste 0x76...");

    if (!bme.begin(BME280_ADDRESS_SECONDARY, &Wire)) {
      Serial.println("BME280 nicht gefunden.");
      Serial.println("Bitte Verkabelung prüfen: VCC, GND, SDA=GPIO4, SCL=GPIO5.");

      while (true) {
        delay(1000);
      }
    }
  }

  Serial.println("BME280 erfolgreich verbunden.");
}


String buildPayload(float temperatureC, float humidityPct, float pressureHpa) {
  String payload = "{";
  payload += "\"device_id\":\"";
  payload += DEVICE_ID;
  payload += "\",";
  payload += "\"temperature_c\":";
  payload += String(temperatureC, 2);
  payload += ",";
  payload += "\"humidity_pct\":";
  payload += String(humidityPct, 2);
  payload += ",";
  payload += "\"pressure_hpa\":";
  payload += String(pressureHpa, 2);
  payload += "}";

  return payload;
}


bool isHttpsUrl(const char* url) {
  String value = String(url);
  value.toLowerCase();

  return value.startsWith("https://");
}


void executePost(HTTPClient& http, const String& payload, const char* collectorToken) {
  http.addHeader("Content-Type", "application/json");

  if (String(collectorToken).length() > 0) {
    http.addHeader("X-Collector-Token", collectorToken);
  }

  int httpCode = http.POST(payload);

  Serial.print("HTTP Status: ");
  Serial.println(httpCode);

  String response = http.getString();

  Serial.print("Response: ");
  Serial.println(response);
}


void sendReading() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WLAN getrennt. Verbinde neu...");
    connectToWifi();
  }

  float temperatureC = bme.readTemperature();
  float humidityPct = bme.readHumidity();
  float pressureHpa = bme.readPressure() / 100.0F;

  if (isnan(temperatureC) || isnan(humidityPct) || isnan(pressureHpa)) {
    Serial.println("Ungültige Sensordaten gelesen. Sendevorgang übersprungen.");
    return;
  }

  Serial.println("--- Messwerte ---");
  Serial.print("Temperatur: ");
  Serial.print(temperatureC);
  Serial.println(" °C");

  Serial.print("Luftfeuchtigkeit: ");
  Serial.print(humidityPct);
  Serial.println(" %");

  Serial.print("Luftdruck: ");
  Serial.print(pressureHpa);
  Serial.println(" hPa");

  String payload = buildPayload(temperatureC, humidityPct, pressureHpa);

  const char* collectorUrl = getCollectorUrl();
  const char* collectorToken = getCollectorToken();

  Serial.println("--- HTTP POST ---");
  Serial.print("URL: ");
  Serial.println(collectorUrl);
  Serial.print("Payload: ");
  Serial.println(payload);

  HTTPClient http;

  if (isHttpsUrl(collectorUrl)) {
    WiFiClientSecure secureClient;

    // Für den MVP pragmatisch.
    // Später besser: echtes Root-CA-Zertifikat setzen statt setInsecure().
    secureClient.setInsecure();

    if (!http.begin(secureClient, collectorUrl)) {
      Serial.println("HTTPS-Verbindung konnte nicht initialisiert werden.");
      return;
    }

    executePost(http, payload, collectorToken);
    http.end();

    return;
  }

  WiFiClient client;

  if (!http.begin(client, collectorUrl)) {
    Serial.println("HTTP-Verbindung konnte nicht initialisiert werden.");
    return;
  }

  executePost(http, payload, collectorToken);
  http.end();
}


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("ESP32-C6 Wetterstation startet...");

  setupBme280();
  connectToWifi();

  sendReading();
  lastSendAt = millis();
}


void loop() {
  unsigned long now = millis();

  if (now - lastSendAt >= SEND_INTERVAL_MS) {
    sendReading();
    lastSendAt = now;
  }
}
