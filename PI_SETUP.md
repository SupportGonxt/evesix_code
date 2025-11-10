# Raspberry Pi Robot Setup Guide (v1.0)

Date: 4 Nov 2025  
Target Device: Raspberry Pi (with SPI LED strip + MariaDB + Kivy UI)

---
## 0. Overview
This document formalizes the manual setup process you listed into a clean, ordered, reproducible procedure. It covers:
- Base OS configuration (SSH, SPI, hostname, boot mode, auto-login)
- System package updates & dependencies
- MariaDB installation, hardening & schema prep
- Python environment + required packages (Kivy, database drivers, LED strip driver)
- Peripheral access (SPI permissions)
- Crontab auto-start strategy
- Optional hardware/network tuning (power config, modem/APN) 
- Verification & troubleshooting

Where possible a safer/recommended alternative is provided (e.g. virtual environments rather than global pip break-system-packages).

---
## 1. Initial Raspberry Pi Configuration (raspi-config)
Launch configuration tool:
```bash
sudo raspi-config
```
Perform these changes inside the menu:
1. Interface Options:
   - Enable SSH
   - Enable SPI
2. System Options:
   - Change Hostname (e.g. `robot-unit-01`)
   - Enable auto-login to console (Console Autologin)
3. Advanced / Boot options:
   - Set boot to Console (not desktop)
   - Ensure boot sequence prefers SD card
4. Optional: Enable Raspberry Pi Connect (if applicable in your OS build)
5. Finish and reboot.

---
## 2. System Update & Upgrade
Keep the system fresh before adding dependencies:
```bash
sudo apt update
sudo apt upgrade -y
```
(Optional cleanup)
```bash
sudo apt autoremove -y
```

---
## 3. Base Dependencies for Kivy & Build Tools
Install libraries required by Kivy (graphics/image handling) and general build tooling:
```bash
sudo apt-get install -y build-essential python3-dev python3-pip \
  libfreetype6-dev libjpeg-dev libopenjp2-7 libtiff5
```
(If `libtiff5` not found on your image, you used a variant; you tried `libtiff6` also.)
```bash
sudo apt-get install -y libtiff6 || echo "libtiff6 not available on this release"
```

---
## 4. Install & Harden MariaDB
```bash
sudo apt install -y mariadb-server
sudo service mariadb status
```
Run the secure installation script (answer interactive prompts – remove anonymous users, disallow remote root, set root password, etc.):
```bash
sudo mysql_secure_installation
```
Then set/confirm root password (only if not already done inside secure installation):
```sql
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Robot123#';
FLUSH PRIVILEGES;
```
Launch MariaDB shell and create the database:
```bash
sudo mysql -u root -p
```
Inside the MariaDB prompt:
```sql
CREATE DATABASE robotdb;
EXIT;
```

---
## 5. Python Environment Strategy
Recommended: create a virtual environment (avoid using global break-system-packages if possible). If you must use system site-packages, you used:
```bash
python3 -m pip config set global.break-system-packages true
```
Instead, prefer:
```bash
python3 -m venv /home/gonxt/kivy/shatyenv
source /home/gonxt/kivy/shatyenv/bin/activate
python -m pip install --upgrade pip
```

---
## 6. Python Packages Installation
With the virtual environment activated:
```bash
pip install kivy
pip install mysql-connector-python   # preferred modern name
pip install PyMySQL
pip install rpi5-ws2812              # LED strip driver
```
(You previously used `pip install mysql` and `pip install mysql.connector` – these are legacy or ambiguous; `mysql-connector-python` is clearer.)

If you need a buzzer or GPIO libraries on newer Pi OS:
```bash
pip install gpiozero
```

---
## 7. SPI Device Permissions
Create the SPI group and add user:
```bash
sudo groupadd spidev 2>/dev/null || echo "Group spidev already exists"
sudo usermod -a -G spidev gonxt
```
(Log out/in or reboot to apply group membership.)

---
## 8. LED Strip & Hardware Validation
After installation and SPI enablement, test quickly (example placeholder):
```python
from rpi5_ws2812.ws2812 import Color, WS2812SpiDriver
strip = WS2812SpiDriver(spi_bus=0, spi_device=0, led_count=10).get_strip()
strip.set_all_pixels(Color(0,255,0))
strip.show()
```
Run with:
```bash
python test_leds.py
```

---
## 9. Crontab Auto-Start Configuration
Edit the root crontab or (recommended) the `gonxt` user crontab.
```bash
sudo crontab -e
```
Avoid multiple overlapping @reboot lines starting the same program; consolidate environment activation and script launching. Recommended single line:
```cron
@reboot sleep 15; /usr/bin/python3 /home/gonxt/kivy/dashboard.py >> /home/gonxt/kivy/logs/dashboard.log 2>&1
```
If you require virtual environment activation for secondary scripts:
```cron
@reboot sleep 15; /bin/bash -c "source /home/gonxt/kivy/shatyenv/bin/activate && /usr/bin/python3 /home/gonxt/kivy/dashboard.py" >> /home/gonxt/kivy/logs/dashboard.log 2>&1
```
To also run LocalStor sync after boot:
```cron
@reboot sleep 30; /bin/bash -c "source /home/gonxt/kivy/shatyenv/bin/activate && /usr/bin/python3 /home/gonxt/kivy/LocalStor.py" >> /home/gonxt/kivy/logs/localstor.log 2>&1
```
Separate entries provide clearer logs versus chaining with `&&`.

Remove older conflicting lines you listed:
```
@reboot sleep 15; python3 /home/gonxt/kivy/dashboard.py && source /home/gonxt/kivy/shatyenv/bin/activate
@reboot sleep 15; python3 /home/gonxt/kivy/dashboard.py & python3 /home/gonxt/kivy/LocalStor.py && source /home/gonxt/kivy/shatyenv/bin/activate
```
They mix activation order incorrectly and may background tasks without log capture.

---
## 10. Boot Mode & Auto Login
From `raspi-config` earlier:
- Boot Options → Console
- Enable auto-login (Console Autologin)
This ensures reduced resource load and faster app startup.

---
## 11. Firmware / Power Configuration (`/boot/firmware/config.txt`)
Edit config:
```bash
cd /boot/firmware
sudo nano config.txt
```
Add (CAUTION: ensure power supply supports this):
```
# Power limits
PSU_MAX_CURRENT=5000
usb_max_current_enable=1
```
Reboot to apply.

---
## 12. Optional Modem / Cellular Setup
(Commented in your notes – only apply if using a modem.)
Enable NetworkManager (if not default):
```bash
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
```
Install tools:
```bash
sudo apt install -y libqmi-utils udhcpc
```
Add APN (example placeholder):
```bash
sudo nmcli c add type gsm ifname '*' con-name Next apn ws.next.mvno connection.autoconnect yes
```
To inspect or use text UI:
```bash
nmtui
```
ADC reading (for power debug):
```bash
vcgencmd pmic_read_adc
```

---
## 13. Order of Operations (Recommended Sequential Flow)
| Step | Purpose | Why Order Matters |
|------|---------|-------------------|
| 1 | raspi-config (SSH/SPI/Hostname) | Interfaces must be enabled before tests |
| 2 | System update/upgrade | Ensures latest security patches before installs |
| 3 | Install build + Kivy deps | Required before `pip install kivy` |
| 4 | Install MariaDB & secure | DB must exist before app writes |
| 5 | Create DB/schema | Application expects `robotdb` |
| 6 | Create virtual env | Isolate Python deps |
| 7 | Install Python packages | After venv & system libs |
| 8 | Add SPI group membership | Needed for LED access without root |
| 9 | LED test script | Validates hardware early |
|10 | Configure crontab | Auto-start after validated manual run |
|11 | Firmware power tweaks | Done last; risky if misconfigured |
|12 | Optional modem/APN | Only if required for deployment |

---
## 14. Verification Checklist
Run these after setup:
```bash
# SPI enabled?
ls /dev/spi* 

# MariaDB service status
sudo service mariadb status

# Python env active?
which python
python -c "import kivy; import mysql.connector; print('Kivy & mysql OK')"

# Database present?
sudo mysql -u root -p -e "SHOW DATABASES LIKE 'robotdb';"

# LED test (see earlier snippet)
python /home/gonxt/kivy/test_leds.py
```
Crontab entries:
```bash
sudo crontab -l
```
Log tail example:
```bash
tail -f /home/gonxt/kivy/logs/dashboard.log
```

---
## 15. Troubleshooting
| Symptom | Possible Cause | Fix |
|---------|----------------|-----|
| LED script fails (permission) | User not in `spidev` group | `usermod -a -G spidev gonxt` then reboot |
| Kivy import error | Missing system libs | Re-run Kivy dependency apt installs |
| MariaDB auth failure | Incorrect root password changes | Reset via `sudo mysql` then ALTER USER again |
| Crontab didn’t start app | Wrong shebang / venv not sourced | Use bash -c with source inside quotes |
| High USB draw issue | PSU limits not applied | Verify `config.txt` edits and stable power supply |
| Modem not connecting | APN incorrect | Check `nmcli connection show` and logs |

---
## 16. Security & Hardening Notes
- Consider creating a non-root DB user with limited privileges rather than using `root` in application code.
- Use `ufw` or similar to restrict inbound ports if remote access exposed.
- Avoid storing raw credentials in scripts; move to environment variables or config files with restricted permissions.

---
## 17. Next Enhancements
1. Systemd service instead of crontab for `dashboard.py` (better restart behavior).  
2. Add a logging directory creation step: `mkdir -p /home/gonxt/kivy/logs`.  
3. Schema migration script for `robotdb` tables.  
4. Automate setup with a single provisioning script.

---
## 18. Quick Provision Script Skeleton (Optional)
```bash
#!/usr/bin/env bash
set -euo pipefail
sudo apt update && sudo apt upgrade -y
sudo apt install -y mariadb-server build-essential python3-dev python3-pip libfreetype6-dev libjpeg-dev libopenjp2-7 libtiff5 || true
sudo mysql -e "CREATE DATABASE IF NOT EXISTS robotdb;"
python3 -m venv /home/gonxt/kivy/shatyenv
source /home/gonxt/kivy/shatyenv/bin/activate
pip install --upgrade pip kivy mysql-connector-python PyMySQL rpi5-ws2812 gpiozero
sudo groupadd spidev 2>/dev/null || true
sudo usermod -a -G spidev gonxt
mkdir -p /home/gonxt/kivy/logs
echo "Setup complete." 
```

---
## 19. Final Notes
Follow the sequence strictly to minimize hardware driver or dependency surprises. Capture logs early; avoid multiple crontab lines for the same service.

---
End of document.
