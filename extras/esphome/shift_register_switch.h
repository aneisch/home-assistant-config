#include <ShiftRegister74HC595.h>
#include "esphome.h"
 
// Number of shift registers
// Data Pin
// Clock Pin
// Latch Pin
ShiftRegister74HC595 sr (1, 5, 4, 14);
 
using namespace esphome;
 
// namespace is called 'switch_' because 'switch' is a reserved keyword
class ShiftRegisterSwitch : public Component, public switch_::Switch {
 private:
  int index;
 
 public:
  ShiftRegisterSwitch(int output) {
    index = output;
  }
 
  void setup() override {
    sr.set(index, HIGH);
  }
 
  void write_state(bool state) override {
    if(state) {
      sr.set(index, LOW);
    } else {
      sr.set(index, HIGH);
    }
 
    // Acknowledge new state by publishing it
    publish_state(state);
  }
};
