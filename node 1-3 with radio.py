from microbit import *
import music
import utime
import radio

Song = [music.BA_DING, music.BIRTHDAY, music.DADADADUM, music.ENTERTAINER, music.NYAN, music.ODE]

timer_seconds = 2700
active = False 
Alarm = Song[0]
song_index = 0
slouch_counter = 0

# ===== RADIO SETUP =====
radio.on()
radio.config(channel=7)

last_slouch_time = utime.ticks_ms()
slouch_result = 0
last_break_send = utime.ticks_ms()
 # Track break time in minutes

display.show(Image.MUSIC_QUAVER)

def get_dist():
    # pin8=trig, pin9=echo, red=pin14, green=pin13
    pin8.write_digital(0)
    utime.sleep_us(2)
    pin8.write_digital(1)
    utime.sleep_us(10)
    pin8.write_digital(0)
    slouch_pulse_start = utime.ticks_us()
    slouch_pulse_end = slouch_pulse_start
    slouch_timeout = slouch_pulse_start + 30000 
    while pin9.read_digital() == 0:
        slouch_pulse_start = utime.ticks_us()
        if slouch_pulse_start > slouch_timeout: return False
    while pin9.read_digital() == 1:
        slouch_pulse_end = utime.ticks_us()
        if slouch_pulse_end > slouch_timeout: return False
    slouch_duration = utime.ticks_diff(slouch_pulse_end, slouch_pulse_start)
    slouch_dist_cm = (slouch_duration * 34300) // (2 * 1000000)
    return slouch_dist_cm

def slouch_check():
    global slouch_result
    slouch_result = get_dist()
    if slouch_result > 30:
        pin14.write_digital(1)
        pin13.write_digital(0)
        radio.send("POSTURE:GOOD")
    else:
        pin14.write_digital(0)
        pin13.write_digital(1)
        music.play(music.BA_DING)
        radio.send("POSTURE:BAD")

def update_rgb():
    temp = temperature()
    # ===== FIXED RADIO: SEND TEMPERATURE STATUS AND VALUE =====
    if temp >= 28:
        pin0.write_digital(0) # Red
        pin1.write_digital(1)
        pin2.write_digital(1)
        radio.send("TEMP:HOT:" + str(temp))  # Format: TEMP:HOT:28
    elif temp >= 20:
        pin0.write_digital(1)
        pin1.write_digital(1)
        pin2.write_digital(0) # Green
        radio.send("TEMP:GOOD:" + str(temp))  # Format: TEMP:GOOD:22
    else:
        pin0.write_digital(1)
        pin1.write_digital(0) # Blue
        pin2.write_digital(1)
        radio.send("TEMP:COLD:" + str(temp))  # Format: TEMP:COLD:15

# ===== FUNCTION TO SEND BREAK TIMER =====
def send_break_timer():
    """Send break timer in minutes (converted from seconds)"""
    minutes = timer_seconds // 60
    radio.send("BREAK:" + str(minutes))  # Format: BREAK:45

while True:
    update_rgb()
    
    sleep(10)
    
    # Send break timer in minutes (not seconds with text)
    send_break_timer()
    
    if utime.ticks_diff(utime.ticks_ms(), last_slouch_time) >= 5000:
        slouch_check()
        last_slouch_time = utime.ticks_ms()
    
    if not active:
        if button_a.was_pressed():
            song_index = (song_index + 1) % len(Song)
            Alarm = Song[song_index]
            music.play(Alarm, wait=False)
            sleep(500)
            music.stop()
        if button_b.was_pressed():
                display.show(Image.YES)
                sleep(500)
                active = True 
            
    elif active and timer_seconds > 0:
        display.show(str(timer_seconds // 60))  # Show minutes
        send_break_timer()
        for i in range(10):
            sleep(100) 
            if utime.ticks_diff(utime.ticks_ms(), last_slouch_time) >= 5000:
                slouch_check()
                last_slouch_time = utime.ticks_ms()
            
                
            if button_a.is_pressed(): 
                display.show(Image.NO)
                while True: 
                    if button_b.is_pressed():
                        update_rgb()
                        send_break_timer()
                        
                        if utime.ticks_diff(utime.ticks_ms(), last_slouch_time) >= 5000:
                            slouch_check()
                            last_slouch_time = utime.ticks_ms()
                        display.show(Image.YES)
                        sleep(500)
                        break
        timer_seconds -= 1
        
    elif timer_seconds == 0:
        for i in range(3):
            music.play(Alarm,wait=True)
        music.stop()
        display.clear()
        timer_seconds = 2700
        active = False
        display.show(Image.MUSIC_QUAVER)
                                  
    sleep(10)