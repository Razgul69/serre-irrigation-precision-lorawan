#pragma once

// --- Clés OTAA TTN (à remplacer par vos valeurs) ---
// APPEUI et DEVEUI en little-endian, APPKEY en big-endian (convention LMIC)
static const u1_t PROGMEM APPEUI[8] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
static const u1_t PROGMEM DEVEUI[8] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
static const u1_t PROGMEM APPKEY[16] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

// --- Brochage ---
#define PIN_VALVE       25   // relais/MOSFET électrovanne
#define PIN_FLOWMETER   27   // entrée impulsions débitmètre (interruption)
#define PIN_LMIC_NSS    5
#define PIN_LMIC_RST    14
#define PIN_LMIC_DIO0   26
#define PIN_LMIC_DIO1   33
#define PIN_LMIC_DIO2   32

// --- Débitmètre YF-S201 : F(Hz) = 7.5 * Q(L/min) => 450 impulsions/L ---
#define FLOW_PULSES_PER_LITER  450.0f

// --- Sécurités locales (autonomes même sans réseau) ---
#define MAX_OPEN_DURATION_MS   (15UL * 60UL * 1000UL)  // 15 min max
#define MAX_VOLUME_ML          10000UL                  // 10 L max par cycle

// --- Uplink période (état + volume) ---
#define TX_INTERVAL_S          300
