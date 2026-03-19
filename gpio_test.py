from smbus2 import SMBus
from time import sleep

I2C_ADDR = 0x39

def read_channel(bus, lsb_reg):
	lsb = bus.read_byte_data(I2C_ADDR, lsb_reg)
	msb = bus.read_byte_data(I2C_ADDR, lsb_reg + 0x10)
	return (msb << 8) | lsb

with SMBus(1) as bus:
	bus.write_byte_data(I2C_ADDR, 0x80, 0x01)
	bus.write_byte_data(I2C_ADDR, 0x81, 0x01)
	bus.write_byte_data(I2C_ADDR, 0x83, 0xF6)
	bus.write_byte_data(I2C_ADDR, 0x8F, 0x01)
	sleep(0.2)
	try:
		while True:
			bus.write_byte_data(I2C_ADDR, 0xAF, 0x10)
			print("Sensor value 415mm:", read_channel(bus, 0x95))
			print("Sensor value 445mm:", read_channel(bus, 0x96))
			print("Sensor value 480mm:", read_channel(bus, 0x97))
			print("Sensor value 515mm:", read_channel(bus, 0x98))
			bus.write_byte_data(I2C_ADDR, 0xAF, 0x00)
			print("Sensor value 555mm:", read_channel(bus, 0x99))
			print("Sensor value 590mm:", read_channel(bus, 0x9A))
			print("Sensor value 630mm:", read_channel(bus, 0x9B))
			print("Sensor value 680mm:", read_channel(bus, 0x9C))
			sleep(1)
			
	except Exception as e:
		print("Error:", e)
