# Nutrislice Home Assistant Integration

A custom integration for Home Assistant to fetch school menu data from Nutrislice.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![GitHub Release](https://img.shields.io/github/v/release/jbiral/nutrislice-ha?style=for-the-badge)

## Features

- Fetches school breakfast and lunch menus.
- Supports multiple schools and meal types.
- Provides a detailed 3-week window of menu data.
- Configurable food categories (Entrees, Sides, Fruit, etc.).
- Custom Lovelace card for an elegant display.

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

## Frontend Card

To display the menu in a beautiful way, this integration comes with a built-in [Nutrislice Card](https://github.com/jbiral/nutrislice-ha/tree/main/custom_components/nutrislice/www).

**Note:** When installed through HACS, the card is automatically registered as a Lovelace resource and is ready to use immediately.

Add the following to your Lovelace configuration:

```yaml
type: custom:nutrislice-card
entity: sensor.your_school_lunch
title: 'School Menu' # Optional
categories: # Optional: list categories to display
  - entree
  - sides
```

### Configuration Options

| Name         | Type   | Requirement  | Description                                                           |
| ------------ | ------ | ------------ | --------------------------------------------------------------------- |
| `type`       | string | **Required** | `custom:nutrislice-card`                                              |
| `entity`     | string | **Required** | The Nutrislice sensor entity (e.g., `sensor.elementary_school_lunch`) |
| `title`      | string | Optional     | Header title for the card. Defaults to "School Menu".                 |
| `categories` | list   | Optional     | List of food categories to display. Defaults to `['entree']`.         |

**Note:** The `categories` list in the card should match the ones you selected during the integration setup. Common categories include `entree`, `sides`, `fruit`, `veggies`, and `milk`.

## Automations & Notifications

You can easily send the daily menu to your phone via an automation using the `today_menu` attribute.

**Example Automation:**

```yaml
alias: 'Send School Lunch Notification'
trigger:
  - platform: time
    at: '07:30:00'
condition:
  - condition: template
    value_template: "{{ state_attr('sensor.elementary_school_lunch', 'today_menu') != 'No menu' }}"
action:
  - service: notify.mobile_app_your_phone
    data:
      title: "Today's Lunch"
      message: "On the menu today: {{ state_attr('sensor.elementary_school_lunch', 'today_menu') }}"
```

---

_Disclaimer: This project is not affiliated with, authorized, maintained, sponsored or endorsed by Nutrislice, Inc or any of its affiliates or subsidiaries._
