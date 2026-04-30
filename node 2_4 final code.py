from microbit import *
from ssd1306 import initialize, clear_oled
from ssd1306_text import add_text
import radio

# ===== RADIO SETUP =====
radio.on()
radio.config(channel=7)

# ===== PIN DEFINITIONS =====
RED = pin0
GREEN = pin1
BLUE = pin2

# ===== WATER REMINDER TIMER =====
_water_reminder_last_time = running_time()
_WATER_REMINDER_INTERVAL = 3600000  # 1 hour

# ===== DATA STORAGE (No Defaults - Will be updated by radio) =====
posture = None          # Will be "GOOD" or "BAD" from radio
temp = None             # Will be "GOOD", "HOT", or "COLD" from radio
temp_value = None       # Will be temperature value from radio
timer_seconds = None    # Will be break time from radio
light_value = 100
light_status = "GOOD"
water_break_active = False
water_break_start = 0

# ===== LED FUNCTIONS =====
def turn_off_all():
    RED.write_digital(0)
    GREEN.write_digital(0)
    BLUE.write_digital(1)

def set_light_color(value):
    turn_off_all()
    if value < 80:
        BLUE.write_digital(0)
    elif value > 180:
        RED.write_digital(1)
    else:
        GREEN.write_digital(1)

def update_light():
    global light_value, light_status
    light_value = display.read_light_level()
    
    if light_value < 80:
        light_status = "DARK"
    elif light_value > 180:
        light_status = "BRIGHT"
    else:
        light_status = "GOOD"
    
    if not water_break_active:
        set_light_color(light_value)
    
    return light_value

# ===== RADIO MESSAGE PARSING (More Robust) =====
def parse_radio_message(msg):
    global posture, temp, temp_value, timer_seconds
    
    print("Received raw message:", msg)  # Debug: print to REPL
    
    # Handle POSTURE messages
    if msg.startswith("POSTURE:"):
        posture = msg.split(":")[1]
        print("Posture updated to:", posture)
    
    # Handle TEMPERATURE messages
    elif msg.startswith("TEMP:"):
        parts = msg.split(":")
        print("Temperature parts:", parts)
        
        # First part after TEMP is the status (GOOD/HOT/COLD)
        if len(parts) >= 2:
            temp = parts[1]
            print("Temperature status:", temp)
        
        # If there's a third part, it's the numeric value
        if len(parts) >= 3 and parts[2].isdigit():
            temp_value = int(parts[2])
            print("Temperature value:", temp_value)
    
    # Handle BREAK messages
    elif msg.startswith("BREAK:"):
        parts = msg.split(":")
        if len(parts) >= 2:
            try:
                timer_seconds = int(parts[1])
                print("Break timer updated to:", timer_seconds)
            except ValueError:
                print("Failed to parse break value:", parts[1])

# ===== WATER BREAK FUNCTIONS =====
def start_water_break_alert():
    global water_break_active, water_break_start
    
    water_break_active = True
    water_break_start = running_time()
    
    display.scroll("WATER BREAK", delay=80)
    
    clear_oled()
    add_text(0, 2, "WATER BREAK!")
    add_text(0, 4, "Time to drink")
    
    sleep(200)

def update_water_break_alert():
    global water_break_active
    
    if not water_break_active:
        return
    
    elapsed = running_time() - water_break_start
    
    if elapsed > 5000:
        water_break_active = False
        set_light_color(light_value)

def get_water_time_display():
    remaining_ms = _WATER_REMINDER_INTERVAL - (running_time() - _water_reminder_last_time)
    remaining_seconds = remaining_ms // 1000
    
    if remaining_seconds >= 60:
        minutes = remaining_seconds // 60
        return str(minutes) + "m"
    else:
        return str(remaining_seconds) + "s"

def check_water_reminder():
    global _water_reminder_last_time
    
    now = running_time()
    
    if not water_break_active:
        if now - _water_reminder_last_time >= _WATER_REMINDER_INTERVAL:
            start_water_break_alert()
            _water_reminder_last_time = now
            return True
    
    return False

# ===== COMFORT CALCULATION =====
def calculate_comfort():
    score = 0
    if posture == "GOOD":
        score += 25
    if light_status == "GOOD":
        score += 25
    if temp == "GOOD":
        score += 25
    if timer_seconds is not None and timer_seconds <= 0:
        score -= 25
    return max(0, min(100, score))

# ===== OLED DISPLAY FUNCTIONS =====
def show_statistics():
    comfort = calculate_comfort()
    clear_oled()
    add_text(0, 0, "SMARTDESK")
    
    # Posture - show "?" if not received yet
    posture_display = posture if posture is not None else "?"
    add_text(0, 1, "P:" + posture_display)
    
    add_text(0, 2, "L:" + light_status + "(" + str(light_value) + ")")
    
    # Temperature - show "?" if not received yet
    temp_display = temp if temp is not None else "?"
    temp_value_display = str(temp_value) if temp_value is not None else "?"
    add_text(0, 3, "T:" + temp_display + "(" + temp_value_display + "C)")
    
    # Break timer - show "?" if not received yet
    if timer_seconds is not None:
        add_text(0, 4, "B:" + str(timer_seconds) + "m")
    else:
        add_text(0, 4, "B:?")
    
    add_text(0, 5, "W:" + get_water_time_display())

def show_progress():
    comfort = calculate_comfort()
    clear_oled()
    add_text(0, 0, "SMARTDESK")
    add_text(0, 2, "COMFORT: " + str(comfort) + "%")
    bar_length = comfort // 10
    bar = "*" * bar_length + "-" * (10 - bar_length)
    add_text(0, 3, bar)
    add_text(0, 5, "Water: " + get_water_time_display())

def show_reminders():
    clear_oled()
    add_text(0, 0, "SMARTDESK")
    add_text(0, 1, "REMINDERS")
    
    # Break reminder - show "?" if not received yet
    if timer_seconds is not None:
        if timer_seconds <= 0:
            add_text(0, 2, "BREAK: NOW!")
        else:
            add_text(0, 2, "BREAK: " + str(timer_seconds) + "m")
    else:
        add_text(0, 2, "BREAK: ?")
    
    add_text(0, 3, "WATER: " + get_water_time_display())
    add_text(0, 5, "Stand & Stretch")

# ===== SETUP =====
initialize()
clear_oled()
display.scroll("READY")
sleep(1000)

mode = 0
last_light_update = 0
last_display_update = 0
update_light()
show_statistics()

while True:
    # Update light (every 500ms)
    if running_time() - last_light_update > 500:
        update_light()
        last_light_update = running_time()
    
    # Check for radio messages
    msg = radio.receive()
    
    if msg:
        parse_radio_message(msg)
    
    # Handle water break alert
    if water_break_active:
        update_water_break_alert()
    else:
        check_water_reminder()
        set_light_color(light_value)
        
        # Update OLED display (every 3 seconds)
        if running_time() - last_display_update > 3000:
            # Recalculate comfort with latest data
            comfort = calculate_comfort()
            
            if mode == 0:
                show_statistics()
            elif mode == 1:
                show_progress()
            else:
                show_reminders()
            mode = (mode + 1) % 3
            last_display_update = running_time()
    
    sleep(50)