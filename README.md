# home-assistant-barry

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/fbjerggaard/home-assistant-barry)
![Version](https://img.shields.io/github/v/release/fbjerggaard/home-assistant-barry)

Sets up Barry integration in Home-Assistant.

Provides a sensor showing current price both with all tariffs and the raw spot price.

## Requirements
You must be a customer with [Barry](https://barry.energy) and have generated an API token in the app

# Installation
## Option 1 (Preferred): HACS
Under HACS -> Integrations click the three dots in the upper right corner and click "Custom repositories". Paste `https://github.com/fbjerggaard/home-assistant-barry` in the "Repository" field and select "Integration" in the category and click "Add". 

Afterwards click "+", search for `barry` and install it.

## Option 2: Manual
From the [latest release](https://github.com/fbjerggaard/home-assistant-barry/releases)
```bash
cd HASS_CONFIG_DIRECTORY # where your configuration.yaml is located
mkdir -p custom_components/barry
cd custom_components/barry
unzip barry.x.y-z.zip
```

# Usage
Setup the sensor using the webui, pasting your access token you got from the Barry app. You can then select the meter you want data from and a sensor will be automatically created.

The sensor has the following fields:
| Sensor field        | Description                             |
|---------------------|-----------------------------------------|
| current_total_price | Current price including all tariffs     |
| current_spot_price  | Current spot price                      |
| currency            | The currency used                       |
| raw_today           | All data points for prices today        |
| raw_tomorrow        | All data points for prices tomorrow     |
| today               | All prices for today                    |
| tomorrow            | All prices for tomorrow                 |
| average             | Average price today                     |
| off_peak_1          | Todays mean average between hours 0-7   |
| off_peak_2          | Todays mean average between hours 19-00 |
| peak                | Todays mean average between hours 8-16  |
| min                 | Todays minimum price                    |
| max                 | Todays maximum price                    |

## Lovelace examples
### Prices card
![https://raw.githubusercontent.com/fbjerggaard/home-assistant-barry/main/doc/prices_card.png]()
To show a simple card with todays prices you could use the `multiple-entity-row` card with the following yaml configuration:
```yaml
entity: sensor.barry_sensor
type: custom:multiple-entity-row
name: Todays prices (kr/kWh)
unit: ' '
icon: mdi:cash-multiple
show_state: false
entities:
  - attribute: min
    name: Min
  - attribute: max
    name: Max
  - attribute: current_total_price
    name: Current
secondary_info:
  entity: sensor.barry_sensor
  attribute: average
  name: 'Average:'
```
**Remember to change the entity to the correct entity generated for your setup**

### Price graph
![https://raw.githubusercontent.com/fbjerggaard/home-assistant-barry/main/doc/price_graph.png]()
To show a graph with today and tomorrows prices you can utilize the `apexcharts-card` card with the following example yaml configuration:
```yaml
type: custom:apexcharts-card
apex_config:
  chart:
    height: 350px
graph_span: 2d
header:
  title: Electricity cost (kr/kWh) - Barry
  standard_format: true
  show_states: true
span:
  start: day
now:
  show: true
  label: Current
  color: purple
yaxis:
  - min: 0
series:
  - entity: sensor.barry_sensor
    name: Total price
    type: area
    curve: stepline
    color: b58e31
    stroke_width: 2
    float_precision: 2
    extend_to_end: false
    show:
      extremas: true
      legend_value: false
    data_generator: >
      return
      entity.attributes.raw_today.concat(entity.attributes.raw_tomorrow).map((entry)
      => {
        return [new Date(entry.start), entry.value];
      });
```
**Remember to change the entity to the correct entity generated for your setup**