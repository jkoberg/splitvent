

# *splitvent* - Designs and Tools to help multiply available Ventilators

This project includes designs for 3D-printed ventilator "Y" splitters, 3D printed flow restrictors, and Raspberry Pi software to monitor per-patient respiratory flow with a [Sensirion SFM-3x00 series inline flow sensor](https://www.sensirion.com/en/flow-sensors/mass-flow-meters-for-high-precise-measurement-of-gases/low-pressure-drop-mass-flow-meter/)

We are releasing our work early and often, and in a form that we hope interested individuals can reproduce. 

Contributors to this project submit their work under a Creative Commons ShareAlike 4.0 license. See `LICENSE.md` for more details


# News

* 2020-03-29 7:30PM EST - [Raspberry pi image now available for download](https://splitvent.s3.us-east-2.amazonaws.com/splitvent_rpi_image_20200329.zip)

# Video Updates

* [April 4th Video Update](https://www.youtube.com/watch?v=DOzIB2Yd5sI) - Tobin discusses their progress testing the SplitVent system at the simulation lab at Indiana University.

* [SplitVent Daily Update March 30](https://www.youtube.com/watch?v=iDRBVGAhckk&fbclid=IwAR0MqLy45Cyf8XVUFYoJnXzKGLTCjBQzCS5fej4EqMJXH3xToOxuD2Zqblo) - Showcase improvements to the UI, a 3D printed cap to the flow sensor, revisions to valves including larger handles that make it easier to operate.

* [SplitVent System Description March 29](https://www.youtube.com/watch?v=Um-QvDB08Cw&t=4s) - Demonstrate how restricter valves and flow monitoring can allow quality vantilation to multiple patients with one ventilator.


# Quick Start

## 3D Printing Models

* Models have been printed with FDM printers using PLA or PETG.
* TPU can be used for an o-ring.
* Other materials such as Med610, Dental SG/LT, and Teeth A2 can be used and should be considered for sterilization purposes. 

* Models printed with FDM should use 10-20% infill with supports touching buildplate.

## Monitoring Software

* Fabricate a cable to connect to the sensor's connector surface contact lands. 

* Connect your RPi to the Sensirion sensor as shown in the image below:
       ![splitvent schematic of RPi connected to Sensirion sensor](./engineering/Schematic.jpg)

* Download the [RPi disk image](https://splitvent.s3.us-east-2.amazonaws.com/splitvent_rpi_image_20200329.zip), unzip, and write to an 8GB or greater SD card. Follow the [instructions here](https://www.raspberrypi.org/documentation/installation/installing-images/README.md)

* Install the SD card into the RPi

* Plug in an HDMI monitor

* Power on the RPi

* Hit ctrl-c a few times to stop the console app

* run "git pull" to get latest GUI changes

* logout

You'll see a UI like this:

![splitvent simple ui](docs/graphical_ui.jpg)

# Thanks to the following contributors:

  * Tobin Greensweig
  * Nate Surls
  * Paul Holland
  * Timothy Nisi
  * Paul Yearling
  * Brian Overshiner
  * Joe Koberg
  * [Dan Lash](https://www.linkedin.com/in/danlash)
  
  
