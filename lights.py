from rpi5_ws2812.ws2812  import Color, WS2812SpiDriver
self.strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=67).get_strip()

self.strip.set_all_pixels(Color(0, 0, 0))
self.strip.show()

