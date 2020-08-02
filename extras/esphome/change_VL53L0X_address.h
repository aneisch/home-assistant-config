#include "esphome.h"
#include <VL53L0X.h>

// Change i2c address of the attached VL53L0X sensors

class ChangeAddress : public Component {
 public:
  void setup() override {

    ESP_LOGD("custom", "Beginning address change");

    VL53L0X sensor1;
    VL53L0X sensor2;

    ESP_LOGD("custom", "Turning off all sensors");
    pinMode(D2, OUTPUT);
    pinMode(D3, OUTPUT);
    digitalWrite(D2, LOW);
    digitalWrite(D3, LOW);

    delay(500);

    // Change address of sensor 1
    pinMode(D2, INPUT);
    delay(150);
    sensor1.init(true);
    delay(100);
    ESP_LOGD("custom", "Changing address 1");
    sensor1.setAddress((uint8_t)35); // 0x23
    
    // Change address of sensor 2
    pinMode(D3, INPUT);
    delay(150);
    sensor2.init(true);
    delay(100);
    ESP_LOGD("custom", "Changing address 2");
    sensor2.setAddress((uint8_t)25); // 0x19
  }
};
