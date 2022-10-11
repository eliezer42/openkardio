#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ADS1X15.h>

#define FIRMWARE_MAJOR_VERSION 1
#define FIRMWARE_MINOR_VERSION 0

#define MAX_BATTERY_VOLTAGE 4.2     // V
#define MIN_BATTERY_VOLTAGE 3.0     // V

#define BLE_MIN_CONN_INTERVAL 40    // ms
#define BLE_MAX_CONN_INTERVAL 80    // ms

#define BATTERY_PIN 35
#define AD8232_LODM 2
#define AD8232_LODP 15
#define DATA_RDY_PIN 4
#define STAT_LED_PIN 0
#define PUSH_BTN_PIN 2

#define ADC_RESOLUTION 16
#define ADC_STEPS_PER_V 7999.756
#define FRONTEND_GAIN 1100.0
#define FRONTEND_LEADS 1

#define EKG_SAMPLE_RATE 240             // SPS Multiples of 10 is recomended
#define SAMPLES_PER_FRAME EKG_SAMPLE_RATE/24              // 1000/BLE_MIN_CONN_INTERVAL >= FPS >= 1000/BLE_MAX_CONN_INTERVAL
#define BUFFER_LENGTH 50                // Bytes > 2 * EKG_SAMPLE_RATE / (1000/BLE_MAX_CONN_INTERVAL)
#define BLE_L2CAP_MTU BUFFER_LENGTH + 3 // Bytes
#define COMMAND 0
#define PAYLOAD 1

const uint8_t ERROR_FLAG = 0xFF;
const uint8_t LEADS_OFF = 0xF1;
const uint8_t NO_ADC = 0xE1;
const uint8_t WAITING = 0x00;

//// BLE definitions
#define BLE_SERVER_NAME "OKDevice"
#define SERVICE_UUID "5e6c5000-05d8-463b-b21d-eed2204c2002"
#define OK_DATA_UUID "5e6c5001-05d8-463b-b21d-eed2204c2002"
#define OK_CTRL_UUID "5e6c5002-05d8-463b-b21d-eed2204c2002"

//// Type definitions
union sample{
  volatile int16_t raw;
  volatile uint8_t bytes[2];
};
struct info {
  uint8_t battery_level;
  uint8_t samples_per_frame;
  uint16_t sample_rate;
  const uint8_t lead_count;
  const uint8_t resolution;
  const uint8_t fw_major_version;
  const uint8_t fw_minor_version;
  const double conv_factor;
};