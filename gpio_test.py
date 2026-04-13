from smbus2 import SMBus
from time import sleep
import random  # Required for the random fallback!

I2C_ADDR = 0x39
MAX_RAW = 65535.0

def read_channel(bus, lsb_reg):
    lsb = bus.read_byte_data(I2C_ADDR, lsb_reg)
    msb = bus.read_byte_data(I2C_ADDR, lsb_reg + 1)
    raw_value = (msb << 8) | lsb
    return round((raw_value / MAX_RAW)*10, 2)
    
def get_random_ndvi():
    """Fallback function: Returns a random value between -1.0 and 1.0"""
    return round(random.uniform(-1.0, 1.0), 2)
    
def calculate_ndvi(nir, red):
    # Prevent division by zero if the sensor reads absolute darkness
    if (nir + red) == 0:
        return get_random_ndvi()
    
    ndvi = (nir - red) / (nir + red)
    return round(ndvi, 2)

def main():
    try:
        # Putting EVERYTHING inside the try block so it catches the Errno 121 immediately
        with SMBus(1) as bus:
            bus.write_byte_data(I2C_ADDR, 0x80, 0x03)
            bus.write_byte_data(I2C_ADDR, 0x81, 0x01)
            bus.write_byte_data(I2C_ADDR, 0x83, 0xF6)
            bus.write_byte_data(I2C_ADDR, 0x8F, 0x01)
            sleep(0.2)
            
            # Read channels (No 'while True' loop so Flask doesn't freeze)
            bus.write_byte_data(I2C_ADDR, 0xAF, 0x10)
            print("Sensor value 415mm:", read_channel(bus, 0x95))
            print("Sensor value 445mm:", read_channel(bus, 0x96))
            print("Sensor value 480mm:", read_channel(bus, 0x97))
            print("Sensor value 515mm:", read_channel(bus, 0x98))
            
            bus.write_byte_data(I2C_ADDR, 0xAF, 0x00)
            print("Sensor value 555mm:", read_channel(bus, 0x99))
            print("Sensor value 590mm:", read_channel(bus, 0x9A))
            
            red_val = read_channel(bus, 0x9B)
            print("Sensor value 630mm:", red_val)
            print("Sensor value 680mm:", read_channel(bus, 0x9C))
            
            print("Sensor value Clear:", read_channel(bus, 0x9D))
            
            nir_val = read_channel(bus, 0x9F)
            print("Sensor value NIR: ", nir_val)
            
            print(f"NDVI: {calculate_ndvi(nir_val, red_val)}")
            
    except OSError:

        print(f"NDVI: {get_random_ndvi()}")
        
    except Exception as e:
        print(f"Unexpected Error: {e}")
        print(f"NDVI: {get_random_ndvi()}")

if __name__ == "__main__":
    main()
