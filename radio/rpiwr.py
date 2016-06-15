# -*- mode: python; coding: utf-8 -*-

# This code is based heavily on the sample code provided by AIW Industries at
# https://github.com/AIWIndustries/Pi_4707/blob/master/firmware/NWRSAME_v2.py
#
# It's been heavily refactored for use with the Twisted framework as well as code
# cleanups and additional functionality.

# Copyright 2016 by Jeffrey C. Ollie
# Copyright 2013 by Ray H. Dees
# Copyright 2013 by AIW Industries, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import time
import sys
import re
import json

from twisted.logger import Logger
from twisted.logger import globalLogBeginner
from twisted.logger import textFileLogObserver
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet import endpoints

from RPi import GPIO

from si4707 import SI4707

from mqtt.client.factory import MQTTFactory
from mqtt import v311

class Radio(object):
    log = Logger()

    # these GPIO pin numbers can't be changed because the AIW Industries
    # add-on board is hard wired into these pins

    radio_reset_pin = 17
    radio_interrupt_pin = 23
    relay_1_pin = 13
    relay_2_pin = 19

    def __init__(self, serial, config):
        self.serial = serial
        self.config = config
        self.radio = None
        self.mqtt = None
        reactor.callWhenRunning(self.radioSetup1)
        reactor.callWhenRunning(self.mqttSetup1)

    def radioSetup1(self):
        self.radio = SI4707()

        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.relay_1_pin, GPIO.OUT)
        GPIO.output(self.relay_1_pin, GPIO.LOW)
        GPIO.setup(self.relay_2_pin, GPIO.OUT)
        GPIO.output(self.relay_2_pin, GPIO.LOW)

        self.log.debug('Resetting the radio')
        GPIO.setup(self.radio_reset_pin, GPIO.OUT)
        GPIO.output(self.radio_reset_pin, GPIO.LOW)
        time.sleep(self.radio.PUP_DELAY)
        GPIO.output(self.radio_reset_pin, GPIO.HIGH)

        self.log.debug('Powering up and patching!')
        time.sleep(1)

        d = self.radio.patch()
        d.addCallback(self.radioSetup2)

    def radioSetup2(self, ignored):
        self.log.debug('Setting up interrupt callbacks')
        GPIO.setup(self.radio_interrupt_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)
        GPIO.add_event_detect(self.radio_interrupt_pin, GPIO.FALLING, callback = self.callback)
        # start watching for interrupts from the radio
        d = self.radio.setProperty(self.radio.GPO_IEN,
                                   (#self.radio.CTSIEN |
                                    self.radio.ERRIEN |
                                    self.radio.RSQIEN |
                                    self.radio.SAMEIEN |
                                    self.radio.ASQIEN |
                                    self.radio.STCIEN))
        d.addCallback(self.radioSetup3)

    def radioSetup3(self, ignored):
        d = self.radio.setProperty(self.radio.WB_SAME_INTERRUPT_SOURCE,
                                   (self.radio.HDRRDYIEN |
                                    self.radio.PREDETIEN |
                                    self.radio.SOMDETIEN |
                                    self.radio.EOMDETIEN))
        d.addCallback(self.radioSetup4)

    def radioSetup4(self, ignored):
        d = self.radio.setProperty(self.radio.WB_ASQ_INT_SOURCE,
                                   (self.radio.ALERTONIEN))
        d.addCallback(self.radioSetup5)

    def radioSetup5(self, ignored):
        d = self.radio.getRevision()
        d.addCallback(self.logRevision)
        d.addCallback(self.radioSetup6)

    def logRevision(self, result):
        self.log.debug('Revision: {result:}', result = result)

    def radioSetup6(self, ignored):
        d = self.radio.setMute(True)
        d.addCallback(self.radioSetup7)

    def radioSetup7(self, ignored):
        d = self.radio.setAGCStatus(0x01)
        d.addCallback(self.radioSetup8)

    def radioSetup8(self, ignored):
        d = self.radio.tune(0xfc)
        d.addCallback(self.radioSetup9)

    def radioSetup9(self, ignored):
        l = LoopingCall(self.periodicMuteStatus)
        reactor.callLater(5.0, l.start, 60)
        l = LoopingCall(self.periodicVolumeStatus)
        reactor.callLater(10.0, l.start, 60)
        l = LoopingCall(self.periodicRSQStatus)
        reactor.callLater(15.0, l.start, 60)
        l = LoopingCall(self.periodicTuneStatus)
        reactor.callLater(45.0, l.start, 60)

    def periodicRSQStatus(self):
        d = self.radio.getRSQStatus()
        d.addCallback(self.logRSQStatus)

    def periodicTuneStatus(self):
        d = self.radio.getTuneStatus()
        d.addCallback(self.logTuneStatus)

    def periodicMuteStatus(self):
        d = self.radio.getMute()
        d.addCallback(self.logMuteStatus)

    def periodicVolumeStatus(self):
        d = self.radio.getVolume()
        d.addCallback(self.logVolumeStatus)

    # this will end up being called from some thread in the RPi.GPIO library
    def callback(self, pin):
        reactor.callFromThread(self._callback1, pin)

    def _callback1(self, pin):
        self.log.debug('callback on pin: {pin:}', pin = pin)
        d = self.radio.getIntStatus()
        d.addCallback(self._callback2, pin)

    def _callback2(self, status, pin):
        self.log.debug('interrupt status: {status:}', status = status)

        if status & self.radio.STCINT:
            self.log.debug('STC interrupt')
            d = self.radio.getTuneStatus(self.radio.INTACK)
            d.addCallback(self.logTuneStatus)
            self.radio.sameFlush()

        if status & self.radio.RSQINT:
            self.log.debug('RSQ interrupt')
            d = self.radio.getRSQStatus(self.radio.INTACK)
            d.addCallback(self.logRSQStatus)

        if status & self.radio.SAMEINT:
            self.log.debug('SAME interrupt')
            d = self.radio.getSameStatus()
            d.addCallback(self.logSAMEStatus)

        if status & self.radio.ASQINT:
            self.log.debug('ASQ interrupt')
            d = self.radio.getASQStatus(self.radio.INTACK)
            d.addCallback(self.logASQStatus)

        if status & self.radio.ERRINT:
            self.log.debug('Error interrupt received')

    def logTuneStatus(self, result):
        self.log.debug('Tune status: {status:}', status = result)
        if self.mqtt is not None:
            self.mqtt.publish(topic = 'weather_radio/{}/rssi'.format(self.serial), qos = 0, message = '{}'.format(result['rssi']))
            self.mqtt.publish(topic = 'weather_radio/{}/snr'.format(self.serial), qos = 0, message = '{}'.format(result['snr']))
            self.mqtt.publish(topic = 'weather_radio/{}/frequency'.format(self.serial), qos = 0, message = '{}'.format(result['frequency']))
            self.mqtt.publish(topic = 'weather_radio/{}/channel'.format(self.serial), qos = 0, message = '{}'.format(result['channel']))

    def logRSQStatus(self, result):
        self.log.debug('RSQ status: {status:}', status = result)
        if self.mqtt is not None:
            self.mqtt.publish(topic = 'weather_radio/{}/rssi'.format(self.serial), qos = 0, message = '{}'.format(result['rssi']))
            self.mqtt.publish(topic = 'weather_radio/{}/snr'.format(self.serial), qos = 0, message = '{}'.format(result['snr']))
            self.mqtt.publish(topic = 'weather_radio/{}/frequency_offset'.format(self.serial), qos = 0, message = '{}'.format(result['frequency_offset']))

    def logSAMEStatus(self, result):
        self.log.debug('SAME status: {status:} {state:} {length:} {confidence:} {data:}', status = result.status, state = result.state, length = result.length, confidence = result.confidence, data = result.data)

        if result.status & self.radio.HDRRDY:
            self.log.debug('SAME header detected')

        if result.status & self.radio.PREDET:
            self.log.debug('SAME preamble detected')

        if result.status & self.radio.SOMDET:
            self.log.debug('SAME start of message detected')

        if result.status & self.radio.EOMDET:
            self.log.debug('SAME end of message detected')
            self.radio.sameFlush()

    def logASQStatus(self, result):
        self.log.debug('ASQ status: {status:}', status = result)

        #if result == 0x01:
        #    self.radio.sameFlush()
        #    self.log.debug('1050 Hz Alert Tone: ON')
        #
        #elif result == 0x02:
        #    self.log.debug('1050 Hz Alert Tone: OFF')

    def logMuteStatus(self, result):
        self.log.debug('Mute status: {status:}', status = result)

        if self.mqtt is not None:
            if result:
                message = 'ON'
            else:
                message = 'OFF'

            self.mqtt.publish(topic = 'weather_radio/{}/mute_status'.format(self.serial), qos = 0, message = message)

    def logVolumeStatus(self, result):
        self.log.debug('Volume status: {status:}', status = result)

        if self.mqtt is not None:
            self.mqtt.publish(topic = 'weather_radio/{}/volume_status'.format(self.serial), qos = 0, message = '{}'.format(result))

    def mqttSetup1(self):
        mqtt_tls = self.config.get('mqtt', {}).get('tls', False)
        if mqtt_tls:
            mqtt_endpoint_type = 'tls'
        else:
            mqtt_endpoint_type = 'tcp'
        mqtt_hostname = self.config.get('mqtt', {}).get('hostname', '127.0.0.1')
        mqtt_port = self.config.get('mqtt', {}).get('port', None)
        if mqtt_port is None:
            if mqtt_tls:
                mqtt_port = 8883
            else:
                mqtt_port = 1883

        self.mqtt_factory = MQTTFactory(profile = MQTTFactory.PUBLISHER | MQTTFactory.SUBSCRIBER)
        self.mqtt_endpoint = endpoints.clientFromString(reactor, '{}:{}:{}'.format(mqtt_endpoint_type, mqtt_hostname, mqtt_port))
        d = self.mqtt_endpoint.connect(self.mqtt_factory)
        d.addCallback(self.mqttGotProtocol)

    def mqttGotProtocol(self, mqtt):
        d = mqtt.connect('weather_radio', keepalive = 0, version = v311)
        d.addCallback(self.mqttConnected, mqtt)

    def mqttConnected(self, result, mqtt):
        self.mqtt = mqtt

        self.mqtt.setPublishHandler(self.mqttReceiveMessage)
        d = self.mqtt.subscribe([('weather_radio/{}/mute_control'.format(self.serial), 0),
                                 ('weather_radio/{}/volume_control'.format(self.serial), 0)])
        d.addCallback(self.mqttSubscribed)

    def mqttSubscribed(self, result):
        self.log.debug('Subscribed: {result:}', result = result)

    def mqttReceiveMessage(self, topic, payload, qos, dup, retain, msgid):
        self.log.debug('topic = {topic}, payload = {payload}, qos = {qos}, dup = {dup}, retain = {retain}, msgid = {msgid}',
                       topic = topic,
                       payload = payload,
                       qos = qos,
                       dup = dup,
                       retain = retain,
                       msgid = msgid)
        if topic.endswith('/mute_control'):
            if payload == b'ON':
                self.log.debug('Turning mute on!')
                self.radio.setMute(True)
            elif payload == b'OFF':
                self.log.debug('Turning mute off!')
                self.radio.setMute(False)
            self.periodicMuteStatus()
        if topic.endswith('/volume_control'):
            if payload == b'INCREASE':
                self.radio.volumeIncrease()
            elif payload == b'DECREASE':
                self.radio.volumeDecrease()
            else:
                try:
                    volume = int(payload)
                    self.radio.setVolume(volume)
                except ValueError:
                    pass
            self.periodicVolumeStatus()

# use the serial number embedded into the Raspberry Pi as a unique identifier
cpuinfo_re = re.compile(br'\nSerial\s+:\s+([0-9a-f]+)\s*\n')
with open('/proc/cpuinfo', 'rb') as cpuinfo:
    data = cpuinfo.read()
    match = cpuinfo_re.search(data)
    if not match:
        sys.stderr.write('Cannot read serial number')
        sys.exit(1)
    serial = match.group(1).decode('ascii')

with open('/opt/rpiwr/etc/config.json','rb') as c:
    config = json.loads(c.read().decode('utf-8'))

try:
    output = textFileLogObserver(sys.stderr, timeFormat="")
    globalLogBeginner.beginLoggingTo([output])
    r = Radio(serial, config)
    reactor.run()
finally:
    GPIO.cleanup()
