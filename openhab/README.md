# openHAB

For purposes of this documentation, I'm going to assume that you
already have a working openHAB installation.  The openHAB
configuration for the Raspberry Pi Weather Radio has been tested with
openHAB 1.8.3.  I haven't made the jump to openHAB 2 yet so I don't know
how well these configs will work.

To begin with, you'll need to install and configure the MQTT binding
in openHAB.  See the [MQTT binding documentation](https://github.com/openhab/openhab/wiki/MQTT-Binding)
if you haven't already set up MQTT in openHAB.

To configure openHAB for the weather radio, edit the
`items/weather_radio.items` and `sitemaps/weather_radio.sitemap` files
and replace the following placeholders with the correct information:

Placeholder | Notes
----------- | -----
<serial_number> | Serial number of your Raspberry Pi. The serial number is used to distinguish multiple weather radios if you had them. The serial number can be found at the bottom of `/proc/cpuinfo`.
<name> | Friendly name for your weather radio.
<broker> | Name of the broker as configured in `openhab.cfg`.

Once you've edited the items and sitemap files copy these files to
the appropriate location in your openHAB installation:

* `items/weather_radio.items`
* `sitemaps/weather_radio.sitemap`
* `transform/weather_radio_volume_in.map`
* `transform/weather_radio_volume_out.map`

Depending on how you configure openHAB the new files should be loaded
automatically. If they aren't loaded automatically you'll need to
reload openHAB.

Once the configuration is loaded you should be able to go into openHAB
and view/control your weather radio.
