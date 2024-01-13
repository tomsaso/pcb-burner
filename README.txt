FIRMWARE FLASHING GUIDE

MCU:  ESP32-WROOM-32

1. ESP32 FLASHING –
1A) Burning Environment
Operating System: Windows/Linux/macOS
Device: USB-TTL Dongle (Serial Flasher)
Connection Type: UART TTL
Baud Rate: 115200

1B) Burning Software
Python - Scripts
	Software Directory: /software/ 

Search and select the CSV file and all of the bin files for burning.
	Question – Which is the best UX / UI for this? Suggestions?

For  every different “Model” value in the CSV - view them as UI Buttons
Underneath it will show the number which have been burned out of the total for  example 0/10

User can click the UI button – e.g. Button “1”

	Program will display rows under the model

Program will search / highlight the first available line in CSV where burned = 0  or empty
	
It will display message saying – Install the PCB then tap Flash

Flash button will appear.

User can click the Flash Button

Attempt Burning 

	Normal Instructions
1.	Open Terminal or Equivalent and enter the directory: /HS-SS/

2. Run the following Python Scripts in Order:

//ERASE
sudo python ./software/esptool_py/esptool/esptool.py --port /dev/cu.SLAB_USBtoUART erase_flash

//FLASH
sudo python ./software/esptool_py/esptool/esptool.py --chip esp32 --port /dev/cu.SLAB_USBtoUART --baud 115200 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 40m --flash_size detect 0x10000 ./HS-SS/a.bin 0x8000 ./HS-SS/b.bin 0x314000 ./HS-SS/c.bin 0x1000 ./HS-SS/d.bin 0x310000 ./HS-SS/other/sw-1.bin
	
Display Status of Firmware Progress

If successful – Display Success
-	Increment “burned” by +1 in csv

Display Timer Countdown 30 seconds. (As PCB goes through internal encryption)
Display: 
REBOOTING - (DO NOT INTERUPT POWER)
Wait for successful Status of PCB

User can now physically test the PCB

Display buttons 
 	PCB Passed / Failed
 User is asked if test Succeeded or Failed (Success / Failed Button)- This information is updated in the CSV

If succeeded, then show a button such as "Print" to send a value in the CSV to a printer by UART. UART format as following (Serial Bit Rate): X-HM://0056H80DH7OSX\r\n

\r: return
\n: newline
The corresponding serial port hexadecimal data as below:
-	Increment “printed” by +1 in csv