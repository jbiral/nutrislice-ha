# Nutrislice Home Assistant Integration

A custom integration for Home Assistant to fetch school menu data from Nutrislice.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![GitHub Release](https://img.shields.io/github/v/release/jbiral/nutrislice-ha?style=for-the-badge)

## Features

- Fetches school breakfast and lunch menus across a 3-week window.
- Supports multiple schools and meal types.
- **Calendar Entity (`calendar.<school>_<meal>`)**: Browse past, current, and upcoming daily menus natively in the Home Assistant Calendar UI or Calendar dashboard card without bloating the Recorder database.
- **Daily Sensors (`sensor.<school>_<meal>_today` & `sensor.<school>_<meal>_tomorrow`)**: Displays the primary entrees (or holiday name) directly as the sensor state, with compact per-day attributes for easy dashboard tiles and push notifications.
- Configurable food categories (`entree`, `sides`, `fruit`, `vegetable`, `drink`, etc.) via both initial setup and the integration **Configure** options menu.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `https://github.com/jbiral/nutrislice-ha` with category **Integration**.
4. Click **Install**.
5. Restart Home Assistant.

### Manual

1. Download the latest release.
2. Copy the `custom_components/nutrislice` folder to your `custom_components` directory.
3. Restart Home Assistant.

## Setup

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **Nutrislice**.
3. Enter your **District** and **School Name**.
   - These are the parts of the Nutrislice URL: `https://mydistrict.nutrislice.com/menu/my-school-name`.
4. Select your **Meal Type** (Breakfast or Lunch).
5. On the next screen, select the **Food Categories** you wish to track.
   - You can change your selected categories anytime later by clicking **Configure** on the integration entry.

## Entities Created

For each configured school and meal type (e.g. `Elementary School` - `Lunch`), three entities are created:

| Entity | Description |
| --- | --- |
| `calendar.elementary_school_lunch` | All-day calendar events for each school day in the 3-week window, with items grouped by category in the event description. |
| `sensor.elementary_school_lunch_today` | State shows today's primary category items (e.g. `Chicken Tenders, Veggie Burger`), the holiday name, or `No menu`. Attributes include `date`, `is_holiday`, `holiday_name`, `menu_summary`, and `items_by_category`. |
| `sensor.elementary_school_lunch_tomorrow` | State shows tomorrow's primary category items, holiday name, or `No menu`, with the same per-day attributes. |

## Automations & Notifications

You can easily send today's or tomorrow's menu to your phone using the dedicated sensors:

```yaml
alias: 'Send Tomorrow School Lunch Notification'
trigger:
  - platform: time
    at: '19:00:00'
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: sensor.elementary_school_lunch_tomorrow
        state: 'No menu'
action:
  - action: notify.mobile_app_your_phone
    data:
      title: "Tomorrow's School Lunch"
      message: "Entrees: {{ states('sensor.elementary_school_lunch_tomorrow') }}"
```

---

_Disclaimer: This project is not affiliated with, authorized, maintained, sponsored or endorsed by Nutrislice, Inc or any of its affiliates or subsidiaries._
