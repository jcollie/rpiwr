# Raspberry Pi Weather Radio

These are the instructions for installing and configuring the
Raspberry Pi Weather Radio hardware and software.

## Basic setup

If you're starting out with a fresh Raspberry Pi, follow your favorite
guide for the first time setup of your Raspberry Pi. There are many
guides and videos out there on the first time setup of a Raspberry Pi
- the world doesn't need another one from me.

I'd recommend not installing the AIW Industries add-on board until
after you've finished the first-time setup of your Raspberry Pi.

## Install the add-on board

AIW Industries does not provide any instructions on installing the add
on board, but the process is fairly straightforward. The instructions
that I provide here assume that you purchased the acrylic case and
standoff kit. The acrylic case and standoff kit is optional, but I'd
highly recommend it. The kit is well designed and manufactured, easy
to assemble and will help protect your investment.

1. Unpack the parts. The kit I received had the nylon screws, nuts and
   standoffs screwed together - you'll need to take them apart. There
   are a lot of small parts in the standoff kit - don't lose any.

2. Remove the protective covering from the acrylic case parts.

3. Insert the four nylon screws into the four small holes of the
   acrylic base plate and push them all the way through to the
   head. The base plate is the one that does not have the two large
   holes in the middle.

4. Place one of the short nylon standoffs on each nylon screw.

5. Insert the nylon screws into the four mounting holes of your
   Raspberry Pi. This may require a small bit of persuasion - the
   screws in my kit were just barely small enough to fit through the
   mounting holes. It should not require a lot of force though - you don't
   want to damage the threads of the screw.

6. Place one of the medium length nylon standoffs on each nylon screw.

7. Insert the nylon screws into the four mounting holes in the add-on
   board. Carefully lower the add-on board and seat the GPIO connector
   of the add-on onto the GPIO header of the Raspberry Pi. Make sure that
   the GPIO connectors are lined up correctly.

8. Place one of the long nylon standoffs on each nylon screw.

9. Place the volume knob onto the volume control shaft. Make sure that
   the set screw of the volume knob lines up with the flat side of the
   volume control shaft. Use a small allen wrench to tighten the set
   screw.

10. Place the acrylic top plate onto the nylon screws. Be sure that
   the holes for the volume knob, the antenna, and the terminal block
   line up properly.

11. Use the nylon nuts to fasten the case together.

12. Carefully screw the antenna onto the antenna connector.

Once everything is together you can power up your Raspberry Pi and
move on to the next step.

## Enable I2C

Create the file `/etc/modules-load.d/i2c.conf` with the following content:

```
i2c-bcm2708
i2c-dev
```

Edit `/boot/config.txt` and make sure that the following lines appear
(uncommented) in the file:

```
dtparam=i2c1=on
dtparam=i2c_arm=on
```

Install some I2C utilities that will be used for some testing:

``` sh
apt-get install i2c-tools
```

Reboot your Raspberry Pi. Once you're logged back running `i2cdetect
-y 1` should return this:


```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- 11 -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

## Python 3 virtualenv

The server I've written uses Python 3, plus a few pre-packaged modules so make sure that they are installed. We'll also need `git` to check out 

```sh
apt-get install python3-dev python3-smbus python3-virtualenv git
```

```sh
git clone https://github.com/jcollie/rpiwr.git /opt/rpiwr
```

Then turn that into a Python virtualenv:

```sh
virtualenv --python=python3 /opt/rpiwr
```

Raspbian comes with an ancient version of `pip` and `setuptools` so
let's get the latest version in our virtualenv:

```sh
/opt/rpiwr/bin/pip install --upgrade pip setuptools
```

Install the rest of the Python modules we'll need. We'll install them
from source since in most cases we need newer versions than are
packaged in Raspbian. Note that there are some additional packages
that need to be installed to make all of the Python modules install
properly (some of them are C extension modules). (At some point I need
to start with a fresh install of Raspbian to determine which Raspbian
packages need to be installed).

```sh
/opt/rpiwr/bin/pip install --upgrade --requirement /opt/rpiwr/radio/requirements.txt
```

## systemd service

