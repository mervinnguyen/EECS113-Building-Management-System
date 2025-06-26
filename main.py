import time
from LCD import LCD
from gpiozero import Button, LED, MotionSensor
from signal import pause
import board
import adafruit_dht
import requests
import threading

# Initialize components
lcd = LCD()

dht_sensor = adafruit_dht.DHT11(board.D17)

api_key = '312335857f6f96be1485c25b97a04f70'

# Initialize buttons
# Increase button at GPIO 25
inc_temp_btn = Button(25, pull_up=True)

# Decrease button at GPIO 18
dec_temp_btn = Button(18, pull_up=True)

# Door button at GPIO 27
door_btn = Button(27, pull_up=True)

# Initialize LEDs
# Red LED at GPIO 16
# Blue LED at GPIO 20
# Green LED at GPIO 32
red_led = LED(16)
blue_led = LED(20)
green_led = LED(32)

# Initialize variables
# Initial desired temperature, current temperature, min and max temperature, door status, lights status,
# HVAC status, emergency status, door message flag, door message timeout, temperature readings, motion detected,
# no motion time, and last time motion was detected 
desired_temp = 70
current_temp = 0
min_temp = 65
max_temp = 95
door_status = True 
lights_status = "OFF"
hvac_status = "OFF"
emergency_status = False
door_message_flag = False
door_message_timeout = 0
temp_readings = []
motion_detected = False
no_motion_time = 10
last_time_motion = time.time()

# Function to turn on the lights ambient for PIR
# This function sets the lights_status to "ON" and turns on the green LED
def turn_on_lights():
    global lights_status
    lights_status = "ON"
    green_led.value = 1

# Function to turn off the lights ambient for PIR
# This function sets the lights_status to "OFF" and turns off the green LED
def turn_off_lights():
    global lights_status
    lights_status = "OFF"
    green_led.value = 0

# Event handler for motion detected
# This function updates the last_time_motion variable and calls turn_on_lights
def motion_handler():
    global last_time_motion
    last_time_motion = time.time()
    turn_on_lights()

# Event handler for no motion detected
# This function checks if the time since the last motion exceeds no_motion_time
def no_motion_handler():
    if time.time() - last_time_motion >= no_motion_time:
        turn_off_lights()

# Function to monitor motion continuously
# This function checks for motion detection and calls the appropriate handler
# It prints "Motion" or "No motion" based on the detection status
def motion_monitor():
    while True:
        if pir.motion_detected:
            motion_handler()
            print("Motion")
        else:
            no_motion_handler()
            print("No motion")
        time.sleep(0.2)

# Initialize PIR motion sensor
# This sets up the PIR sensor on GPIO 23 and assigns the motion and no motion handlers
pir = MotionSensor(23)
pir.when_motion = motion_handler
pir.when_no_motion = no_motion_handler

# Increase temperature button
# This function increments the desired temperature by 1, ensuring it does not exceed max_temp
def inc_pressed():
    global desired_temp
    if not emergency_status:
        desired_temp = min(desired_temp + 1, max_temp)  #desired_temp doesn't exceed max_temp

# Decrease temperature button
# This function decrements the desired temperature by 1, ensuring it does not go below min
def dec_pressed():
    global desired_temp
    if not emergency_status:
        desired_temp = max(desired_temp - 1, min_temp)  #desired_temp doesn't go below min_temp

# Door button
# This function toggles the door status, updates the door message flag and timeout,
def door_pressed():
    global door_status, hvac_status, door_message_flag, door_message_timeout
    door_status = not door_status  # Toggle door status
    door_message = "open" if not door_status else "closed"  # Determine door status message
    door_message_flag = True
    door_message_timeout = time.time() + 3  # Set timeout for 3 seconds

    # Turn off HVAC if door/window is open
    if not door_status:
        hvac_status = "OFF"
    else:  # Restore HVAC status if door/window is closed
        hvac_status = hvac_status

# Function to request humidity data from OpenWeatherMap API
# This function fetches humidity data based on latitude and longitude
# It returns the humidity value or None if the request fails
def humidity_request():
    # fix api portion !!!!!!!!!!!
    api_url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "appKey": api_key,
        "lat": "33.68",
        "lon": "117.82",
    }

    try:
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            humidity_data = data["Data"]["Providers"][-1]["Records"][0]["HlyRelHum"]["Value"]
            humidity = int(humidity_data)
            return humidity
        else:
            print(f"Failed to fetch humidity data. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Assign button event handlers
# These handlers are called when the respective buttons are pressed
inc_temp_btn.when_pressed = inc_pressed
dec_temp_btn.when_pressed = dec_pressed
door_btn.when_pressed = door_pressed


# Create a separate thread for motion monitoring
# This thread runs the motion_monitor function to continuously check for motion
motion_thread = threading.Thread(target=motion_monitor)
motion_thread.daemon = True  # Set daemon thread, so it exits when the main program exits
motion_thread.start()  # Start the motion monitoring thread


def blink_leds():
    while True:
        if emergency_status:
            red_led.toggle()
            blue_led.toggle()
            time.sleep(0.5)
            lcd.clear()
            red_led.on()
            lcd.message("FIRE!  Dr:O", 1)
            lcd.message("EVACUATE", 2)
        else:
            time.sleep(0.1)

# Create a separate thread for blinking LEDs
blink_thread = threading.Thread(target=blink_leds)
blink_thread.daemon = True  # Set daemon thread, so it exits when the main program exits
blink_thread.start()  # Start the blinking LEDs thread

# Main loop
while True:
    try:
        # Read temperature and humidity data
        temp_c = dht_sensor.temperature
        if temp_c is not None:
            temp_f = int(temp_c * (9/5) + 32)
            temp_readings.append(temp_f)
            if len(temp_readings) > 3:
                temp_readings.pop(0)
        current_temp = sum(temp_readings) // len(temp_readings)

        humidity = humidity_request()
        if humidity is not None:
            weather_index = round(current_temp + 0.05 * humidity)
            current_temp = weather_index

            if current_temp - desired_temp == - 3 and door_status:
                lcd.clear()
                lcd.message('HEAT TURNING',1)
                lcd.message('      ON',2)
                time.sleep(3)
                lcd.clear()
                hvac_status = "HEAT"
                lights_status  = "ON"
                blue_led.off()
                red_led.on()
            elif current_temp - desired_temp == 3 and door_status:
                lcd.clear()
                lcd.message('AC TURNING',1)
                lcd.message('      ON',2)
                time.sleep(3)
                lcd.clear()
                hvac_status = "AC"
                lights_status  = "ON"
                red_led.off()
                blue_led.on()
            else:
                hvac_status = "OFF"
                lights_status = "OFF"
                red_led.off()
                blue_led.off()
        else:
            weather_index = current_temp  # Fallback to current_temp if humidity data is not available

        print("current temp:",current_temp)
        # Check for emergency conditions and update display
        if current_temp > 95:
            emergency_status = True
        elif door_message_flag and time.time() < door_message_timeout:
            emergency_status = False
            door_message = "open" if not door_status else "closed"
            lcd.clear()
            lcd.message(f"Door/window {door_message}!", 1)
        else:
            emergency_status = False
            door_message_flag = False
            door_message = "O" if not door_status else "C"
            lcd.clear()
            lcd.message(f"{desired_temp}/{current_temp} Dr:{door_message}", 1)
            lcd.message(f"H:{hvac_status} L:{lights_status}", 2)


    except RuntimeError as error:
        time.sleep(2)
        continue

    except Exception as error:
        dht_sensor.exit()
        raise error

    time.sleep(0.5)

pause()  # Wait for button events