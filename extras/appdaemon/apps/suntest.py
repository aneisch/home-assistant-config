import hassapi as hass
class SunTest(hass.Hass):

    def initialize(self):
        self.log('Test sunset/sunrise:')
        self.log(self.parse_time('sunset'))
        self.log(self.parse_time('sunrise'))
        self.log(self.time())
