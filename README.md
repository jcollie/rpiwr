# Raspberry Pi Weather Radio

This project is about developing a NOAA Weather Radio that connects
into your smart home, in particular to [openHAB](http://www.openhab.org/).

## Safety notes and disclaimer

Having a weather radio is an important safety tool for you and your
family. Every home should have at least one (and maybe more depending
on the size of the house). That said, this project is intended to be
fun and educational but _in no way should it be relied upon to protect
the safety of your family_. Before spending the money and the time on
this project invest in a standard weather radio. Basic weather radios
can be purchased for around US$20-US$30 from many retailers. Just be
sure to get a weather radio that has been approved by the
[NOAA](http://www.nws.noaa.gov/nwr/info/nwrrcvr.html#pad).

> This project is provided as is without any guarantees or
> warranty. In association with the project, Jeffrey C. Ollie makes no
> warranties of any kind, either express or implied, including but not
> limited to warranties of merchantability, fitness for a particular
> purpose, of title, or of noninfringement of third party rights. Use
> of the product by a user is at the user’s risk.
> 
> NO REPRESENTATIONS OR WARRANTIES, EITHER EXPRESS OR IMPLIED, OF
> MERCHANTABILITY, FITNESS FOR A SPECIFIC PURPOSE, THE PRODUCTS TO
> WHICH THE INFORMATION MENTIONS MAY BE USED WITHOUT INFRINGING THE
> INTELLECTUAL PROPERTY RIGHTS OF OTHERS, OR OF ANY OTHER NATURE ARE
> MADE WITH RESPECT TO INFORMATION OR THE PRODUCT TO WHICH INFORMATION
> MENTIONS. IN NO CASE SHALL THE INFORMATION BE CONSIDERED A PART OF
> OUR TERMS AND CONDITIONS OF SALE.

## Bill of Materials

The weather radio is built upon a Raspberry Pi and an add-on board
developed by [AIW Industries](http://www.aiwindustries/).  You'll need
a Raspberry Pi that has the 40 pin GPIO header. I'm using a Raspberry
Pi 2. The Raspberry Pi 3 should certainly work, although I haven't
tried the Pi 3 with this project. The Raspberry Pi A+ and Raspberry Pi
B+ should work as well. The Raspberry Pi Zero should work, but you'll
need to solder a header onto the GPIO pins to connect it to the add-on
board.

### From your favorite supplier

If you don't already have a Raspberry Pi you'll need to buy one.  If
you are buying a new Raspberry Pi I'd recommend getting the Raspberry
Pi 3 as it has the best performance and built-in wireless.

Item | Notes | Approximate Cost (as of 2016/6/1)
-----| ----- | ----------------------
Raspberry Pi | | US$35
MicroSD card formatted with your favorite distro | The instructions are going to assume you are using Raspbian Jessie, but just about anything will work | US$10
Power supply | I like the [CanaKit 5V 2.5A Raspberry Pi 3 Power Supply](http://smile.amazon.com/dp/B00MARDJZ4) but anything that can supply 2.0A or more should work. | US$10
Wireless adapter | Only if you're not using a Raspberry Pi 3 or connecting via the Ethernet adapter | US$10

### From [AIW Industries](http://www.aiwindistries.com/)

Item | Notes | Approximate Cost (as of 2016/6/1)
---- | ----- | ----------------------
Raspberry Pi B+/2 NWR Receiver/SAME Decoder | | US$69.95
SMA Wideband Antenna | An antenna of some kind is required. I'd recommend starting with the antenna from AIW Industries and then if you aren't getting a good enough signal you can upgrade to another antenna. | US$11.00
Acrylic Case w/Standoff Kit | Optional but highly recommended | US$7.50
Volume Knob | Optional but highly recommended | US$5.25

Contact AIW Industries about shipping costs, especially if you need to
ship to someplace outside the United States.

## openHAB and User Interfaces

I use [openHAB](http://www.openhab.org/) to control my home and so
I've included instructions in this guide on how to configure openHAB
to control the Raspberry Pi Weather Radio. openHAB is optional if you
can configure your smart home controller to use
[MQTT](http://mqtt.org/). That's left as an exercise for the reader
though. I'm open to pull requests that add instructions for other
smart home controllers.

In the future I'll be adding a REST interface to control the Raspberry
Pi Weather Radio. That will allow control from a wider variety of
systems. Potentially that would include a standalone HTML/JavaScript
front end but I suck at designing that sort of thing so again that
will be left as an exersise for someone else. Pull requests
definitely welcome.

The instructions that I provide for openHAB are going to assume that
you already have a functional openHAB installation. If you are
installing openHAB for the first time or are having other problems I
refer you to [openHAB's
documentation](https://github.com/openhab/openhab/wiki) and [openHAB's
excellent community forum](https://community.openhab.org/). I'm
somewhat of an openHAB newbie so any questions not directly related to
connecting openHAB to the Raspberry Pi Weather Radio are going to be
referred to the openHAB community forum.

## Raspberry Pi

The instructions that I provide for the Raspberry Pi are going to
assume that your Raspberry Pi is configured and connected to your
network (wireless or otherwise). There are a zillion guides and videos
out there on setting up a Raspberry Pi for the first time - the world
doesn't need another one from me.

These instructions are going to assume a fully up-to-date Raspbian
Jesse system. I'd recommend starting with the Raspbian Lite image as
running a GUI isn't necessary for the operation of the weather
radio. It probably won't hurt either, other than taking up resources
and possibly reducing performance.

If you'd prefer to use a distribution other than Raspbian Jessie
anyone with sufficient experience should be able to adapt these
instructions. I have limited or no experience with distribitions for
the Raspberry Pi other than Raspbian so I probably wouldn't be able to
help with any problems that are specific to a distribution.

I'd also reccommend that you do not run openHAB and the weather radio
on the same Raspberry Pi. In fact, I do not recommend that you run
openHAB on a Raspberry Pi at all but that's just my personal
opinion. Many people do run openHAB on Raspberry Pis and are perfectly
satisfied. However when I tried it I felt that the Raspberry Pi wasn't
able to deliver enough performance to satify my needs. Your mileage
may vary.

## MQTT

The primary method for controlling the Raspberry Pi Weather Radio is
through [MQTT](http://mqtt.org/). Again, I'm going to assume that you
already have a working MQTT broker. If you don't have one already
[Mosquitto](http://mosquitto.org/) is a popular
choice. [RabbitMQ](http://www.rabbitmq.com/) with the [RabbitMQ MQTT
Adapter](https://www.rabbitmq.com/mqtt.html) should work too.

Configuring and securing an MQTT broker is left as an exercise to the
reader.

## Continuing on

See the READMEs in the [radio](radio/) and [openHAB](openhab/)
subdirectories for specific instructions on configuring each part of
this project.
