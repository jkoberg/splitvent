

# splitvent - Designs and Tools to help multiply available Ventilators

Contributors to this project submit their work under a Creative Commons ShareAlike 4.0 license. See `LICENSE.md` for more details


# News

* 2020-03-29 7:30PM EST - [Raspberry pi image now available for download at https://splitvent.s3.us-east-2.amazonaws.com/splitvent_rpi_image_20200329.zip](https://splitvent.s3.us-east-2.amazonaws.com/splitvent_rpi_image_20200329.zip)


# Quick Start

* Connect to the Sensirion sensor as shown in the image below:
       ![splitvent schematic of RPi connected to Sensirion sensor](./engineering/Schematic.jpg)

* Checkout the repo on your RPi

* Make sure the i2c-dev module is shown by `lsmod`, or run `sudo raspi-config` and turn on the I2C peripheral to load it.

* `./run.sh` 


# Thanks to the following contributors:

  * Tobin Greensweig
  * Joe Koberg
  
