#pragma once

// --- Brochage Arduino Nano ESP32 ---
// SEN0308 : rouge -> 3V3, noir -> GND, jaune -> A0
// L'ADC de l'ESP32 sature vers 3,1 V : sous 3,3 V la sonde sort < 3 V, OK.
#define PIN_SEN0308        A0
#define SEN_SAMPLES        32      // lectures par mesure (mediane)
#define MEASURE_PERIOD_MS  1000UL  // periode d'affichage serie

// --- Calibration niveau 1 (mV, mesures sur CE montage) : voir docs/calibration_sen0308.md ---
#define AIR_MV     2500.0f   // sonde seche dans l'air  -> indice 0 %
#define WATER_MV   50.0f     // sonde dans l'eau        -> indice 100 %

// --- Calibration niveau 2 (optionnelle) : theta[%] = VWC_A * mV + VWC_B ---
#define USE_VWC    0
#define VWC_A      (-0.0180f)
#define VWC_B      (46.0f)

// ======================= Variante LoRaWAN (env nano_esp32_lorawan) =======================
#ifdef WITH_LORAWAN
#include <lmic.h>
// Cles OTAA TTN : APPEUI/DEVEUI little-endian, APPKEY big-endian (convention LMIC)
static const u1_t PROGMEM APPEUI[8]  = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
static const u1_t PROGMEM DEVEUI[8]  = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
static const u1_t PROGMEM APPKEY[16] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
// RFM95 sur SPI du Nano ESP32 (D11 MOSI, D12 MISO, D13 SCK)
#define PIN_LMIC_NSS   D10
#define PIN_LMIC_RST   D9
#define PIN_LMIC_DIO0  D2
#define PIN_LMIC_DIO1  D3
#define PIN_LMIC_DIO2  LMIC_UNUSED_PIN
#define TX_INTERVAL_S  900   // uplink toutes les 15 min (comme la table CR1000)
#endif
