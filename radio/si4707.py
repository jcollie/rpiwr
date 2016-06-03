# -*- mode: python; coding: utf-8 -*-

# This code is based heavily on the sample code provided by AIW Industries at
# https://github.com/AIWIndustries/Pi_4707/blob/master/firmware/SI4707_I2C_v2.py
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

from twisted.logger import Logger
from twisted.internet.defer import DeferredLock
from twisted.internet.defer import Deferred
from twisted.internet.defer import succeed
from twisted.internet import reactor
from twisted.internet.threads import deferToThread

from RPi import GPIO

from i2c import Device

def locking(fn):
    def _wrap(self, *args, **kw):
        def _runInThread(ignored, response):
            d = deferToThread(fn, self, *args, **kw)
            d.addCallback(_handleReturn, response)
            d.addErrback(_handleError, response)
            
        def _handleReturn(result, response):
            self._lock.release()
            response.callback(result)

        def _handleError(failure, response):
            self.log.error('Error: {failure:}', failure = failure)
            self._lock.release()
            response.errback(failure)
            
        response = Deferred()
        d = self._lock.acquire()
        d.addCallback(_runInThread, response)
        return response
    
    return _wrap

class SI4707(object):
    log = Logger()
    
    ON =                                    0x01      #  Used for Power/Mute On.
    OFF =                                   0x00      #  Used for Power/Mute Off.
    CMD_DELAY =                            0.002      #  Inter-Command delay (>301 usec).
    PROP_DELAY =                           0.010      #  Set Property Delay (>10.001 msec)
    PUP_DELAY =                              0.2      #  Power Up Delay.  (110.001 msec)
    TUNE_DELAY =                            0.25      #  Tune Delay. (250.001 msec)
    RADIO_ADDRESS =                         0x22 >> 1 #  I2C address of the Si4707 (w/SEN pin LOW)
    RADIO_VOLUME =                          0x003F    #  Default Volume.

    #  SAME Definitions.

    SAME_CONFIDENCE_THRESHOLD =               1      #  Must be 1, 2 or 3, nothing else!
    SAME_BUFFER_SIZE =                      255      #  The maximum number of receive bytes.
    SAME_MIN_LENGTH =                        36      #  The SAME message minimum acceptable length.
    SAME_LOCATION_CODES =                    30      #  Subtract 1, because we count from 0.
    SAME_TIME_OUT =                           6      #  Time before buffers are flushed.

    #  Program Control Status Bits.

    INTAVL =                               0x10      #  A status interrupt is available.
    MSGAVL =                               0x01      #  A SAME message is Available to be printed/parsed.
    MSGPAR =                               0x02      #  The SAME message was successfully Parsed.
    MSGUSD =                               0x04      #  When set, this SAME message has been used.
    MSGPUR =                               0x08      #  The SAME message should be Purged (Third Header received).

    #  Weather Band definitions.

    WB_CHANNEL_SPACING =                0x0A         #  25 kHz.
    WB_MIN_FREQUENCY =                  0xFDC0       #  162.400 mHz.
    WB_MAX_FREQUENCY =                  0xFDFC       #  162.550 mHz.

    #  Si4707 Command definitions.

    POWER_UP =                          0x01       #  Powerup device.
    GET_REV =                           0x10       #  Returns revision information on the device.
    POWER_DOWN =                        0x11       #  Powerdown device.
    SET_PROPERTY =                      0x12       #  Sets the value of a property.
    GET_PROPERTY =                      0x13       #  Retrieves a propertys value.
    GET_INT_STATUS =                    0x14       #  Read interrupt status bits.
    PATCH_ARGS =                        0x15       #  Reserved command used for firmware file downloads.
    PATCH_DATA =                        0x16       #  Reserved command used for firmware file downloads.
    WB_TUNE_FREQ =                      0x50       #  Selects the WB tuning frequency.
    WB_TUNE_STATUS =                    0x52       #  Queries the status of the previous WB_TUNE_FREQ command.
    WB_RSQ_STATUS =                     0x53       #  Queries the status of the Received Signal Quality (RSQ) of the current channel.
    WB_SAME_STATUS =                    0x54       #  Returns SAME information for the current channel.
    WB_ASQ_STATUS =                     0x55       #  Queries the status of the 1050 Hz alert tone.
    WB_AGC_STATUS =                     0x57       #  Queries the status of the AGC.
    WB_AGC_OVERRIDE =                   0x58       #  Enable or disable the AGC.
    GPIO_CTL =                          0x80       #  Configures GPO as output or Hi-Z.
    GPIO_SET =                          0X81       #  Sets GPO output level (low or high).

    #  Si4707 property definitions.

    GPO_IEN     =                       0x0001      #  Enables GPO2 interrupt sources.
    REFCLK_FREQ =                       0x0201      #  Sets frequency of reference clock in Hz.
    REFCLK_PRESCALE =                   0x0202      #  Sets the prescaler value for RCLK input.
    RX_VOLUME   =                       0x4000      #  Sets the output volume.
    RX_HARD_MUTE =                      0x4001      #  Mutes the audio output.
    WB_MAX_TUNE_ERROR =                 0x5108      #  Maximum change from the WB_TUNE_FREQ to which the AFC will lock.
    WB_RSQ_INT_SOURCE =                 0x5200      #  Configures interrupts related to RSQ metrics.
    WB_RSQ_SNR_HIGH_THRESHOLD =         0x5201      #  Sets high threshold for SNR interrupt.
    WB_RSQ_SNR_LOW_THRESHOLD =          0x5202      #  Sets low threshold for SNR interrupt.
    WB_RSQ_RSSI_HIGH_THRESHOLD =        0x5203      #  Sets high threshold for RSSI interrupt.
    WB_RSQ_RSSI_LOW_THRESHOLD =         0x5204      #  Sets low threshold for RSSI interrupt.
    WB_VALID_SNR_THRESHOLD =            0x5403      #  Sets SNR threshold to indicate a valid channel.
    WB_VALID_RSSI_THRESHOLD =           0x5404      #  Sets RSSI threshold to indicate a valid channel.
    WB_SAME_INTERRUPT_SOURCE =          0x5500      #  Configures SAME interrupt sources.
    WB_ASQ_INT_SOURCE =                 0x5600      #  Configures 1050 Hz alert tone interrupts.

    #  Si4707 power up command arguments.

    WB =                                0x03      #  Function, 3 = WB receive.
    QUERY =                             0x0F      #  Function, 15 = Query Library ID.
    XOSCEN =                            0x10      #  Crystal Oscillator Enable.
    PATCH =                             0x20      #  Patch Enable.
    GPO2EN =                            0x40      #  GPO2 Output Enable.
    CTSEN =                             0x80      #  CTS Interrupt Enable.

    OPMODE =                            0x05      #  Application Setting, 5 = Analog L & R output.

    # Si4707 returned interrupt status bits.

    STCINT =                        0x01      #  Seek/Tune Complete Interrupt.
    ASQINT =                        0x02      #  1050 Hz Alert Tone Interrupt.
    SAMEINT =                       0x04      #  SAME Interrupt.
    RSQINT =                        0x08      #  Received Signal Quality Interrupt.
    ERRINT =                        0x40      #  Error Interrupt.
    CTSINT =                        0x80      #  Clear To Send Interrupt.

    # Si4707 status register masks.
    
    VALID =                         0x01      #  Valid Channel.
    AFCRL =                         0x02      #  AFC Rail Indicator.

    RSSILINT =                      0x01      #  RSSI was Detected Low.
    RSSIHINT =                      0x02      #  RSSI was Detected High.
    SNRLINT =                       0x04      #  SNR was Detected Low.
    SNRHINT =                       0x08      #  SNR was Detected High.

    HDRRDY =                        0x01      #  SAME Header Ready was detected.
    PREDET =                        0x02      #  SAME Preamble was Detected.
    SOMDET =                        0x04      #  SAME Start Of Message was Detected.
    EOMDET =                        0x08      #  SAME End Of Message was Detected.

    ALERTON =                       0x01      #  Alert Tone has not been detected on since last WB_TUNE_FREQ.
    ALERTOF =                       0x02      #  Alert Tone has not been detected off since last WB_TUNE_FREQ.
    ALERT =                         0x01      #  Alert Tone is currently present.

    #  Si4707 interrupt acknowledge commands.

    CHECK =                         0x00      #  Allows checking of status without clearing interrupt.
    INTACK =                        0x01      #  If set, this bit clears the current interrupt.
    CLRBUF =                        0x02      #  If set, the SAME buffer is cleared.

    #  Si4707 sources for GPO2/INT Interrupt pin.

    STCIEN =                        0x0001      #  Seek/Tune Complete Interrupt Enable.
    ASQIEN =                        0x0002      #  ASQ Interrupt Enable.
    SAMEIEN =                       0x0004      #  SAME Interrupt Enable.
    RSQIEN =                        0x0008      #  RSQ Interrupt Enable.
    ERRIEN =                        0x0040      #  Error Interrupt Enable.
    CTSIEN =                        0x0080      #  CTS Interrupt Enable.
    STCREP =                        0x0100      #  Repeat STCINT even if it is already set.
    ASQREP =                        0x0200      #  Repeat ASQINT even if it is already set.
    SAMEREP =                       0x0400      #  Repeat SAMEINT even if it is already set.
    RSQREP =                        0x0800      #  Repeat RSQINT even if it is already set.

    RSSILIEN =                      0x0001      #  RSSI detect Low Interrupt Enable.
    RSSIHIEN =                      0x0002      #  RSSI detect High Interrupt Enable.
    SNRLIEN =                       0x0004      #  SNR detect Low Interrupt Enable.
    SNRHIEN =                       0x0008      #  SNR detect High Interrupt Enable.

    HDRRDYIEN =                     0x0001      #  SAME Header Ready Interrupt Enable.
    PREDETIEN =                     0x0002      #  SAME Preamble Detected Interrupt Enable.
    SOMDETIEN =                     0x0004      #  SAME Start Of Message Detected Interrupt Enable.
    EOMDETIEN =                     0x0008      #  SAME End Of Message Detected Interrupt Enable.

    ALERTONIEN =                    0x0001      #  Sets 1050 Hz tone on as source of ASQ Interrupt.
    ALERTOFIEN =                    0x0002      #  Sets 1050 Hz tone off as source of ASQ Interrupt.

    #  Si4707 GPO control / set functions.
    
    GPO1OEN =                       0x02      #  GPO1 output enable.
    GPO2OEN =                       0x04      #  GPO2 output enable.  The use of GPO2 as an interrupt pin will override this.
    GPO3OEN =                       0x08      #  GPO3 output enable.
    GPO1LEVEL =                     0x02      #  Sets GPO1 High.
    GPO2LEVEL =                     0x04      #  Sets GPO2 High.
    GPO3LEVEL =                     0x08      #  Sets GPO3 High.

    #  SAME confidence level masks and bit shift positions.
    SAME_STATUS_OUT_CONF0_BYTE =       5
    SAME_STATUS_OUT_CONF1_BYTE =       5
    SAME_STATUS_OUT_CONF2_BYTE =       5
    SAME_STATUS_OUT_CONF3_BYTE =       5
    SAME_STATUS_OUT_CONF4_BYTE =       5
    SAME_STATUS_OUT_CONF5_BYTE =       4
    SAME_STATUS_OUT_CONF6_BYTE =       4
    SAME_STATUS_OUT_CONF7_BYTE =       4
    SAME_STATUS_OUT_CONF0_MASK =       4
    SAME_STATUS_OUT_CONF1_MASK =       0x0C
    SAME_STATUS_OUT_CONF2_MASK =       0x30
    SAME_STATUS_OUT_CONF3_MASK =       0xC0
    SAME_STATUS_OUT_CONF4_MASK =       0x03
    SAME_STATUS_OUT_CONF5_MASK =       0x0C
    SAME_STATUS_OUT_CONF6_MASK =       0x30
    SAME_STATUS_OUT_CONF7_MASK =       0xC0
    SAME_STATUS_OUT_CONF0_SHFT =       0
    SAME_STATUS_OUT_CONF1_SHFT =       2
    SAME_STATUS_OUT_CONF2_SHFT =       4
    SAME_STATUS_OUT_CONF3_SHFT =       6
    SAME_STATUS_OUT_CONF4_SHFT =       0
    SAME_STATUS_OUT_CONF5_SHFT =       2
    SAME_STATUS_OUT_CONF6_SHFT =       4
    SAME_STATUS_OUT_CONF7_SHFT =       6

    #  Radio Variables.
    freqHighByte = 0xFD
    freqLowByte = [0xC0, 0xCA, 0xD4, 0xDE, 0xE8, 0xF2, 0xFC]
    freqNow = ["162.400", "162.425","162.450", "162.475", "162.500", "162.525", "162.550"]

    # Errata patch data from Silicon Labs for the Si4707
    # used to help cure false alarm conditions
    PATCH_COMMANDS = [(PATCH_ARGS, [0x00, 0x00, 0x04, 0xAE, 0x4D, 0x24, 0xBA]),
                      (PATCH_DATA, [0x37, 0xB1, 0x23, 0xAC, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x58, 0xEB, 0x73, 0xC7, 0x0A]),
                      (PATCH_DATA, [0xC1, 0x7D, 0xE9, 0x11, 0x6E, 0xA0, 0xDC]),
                      (PATCH_DATA, [0xE4, 0x01, 0x2A, 0x5F, 0xA9, 0xA9, 0x43]),
                      (PATCH_DATA, [0x34, 0x33, 0x1B, 0x1B, 0xC2, 0x44, 0x6E]),
                      (PATCH_DATA, [0xC2, 0x16, 0xAB, 0xE2, 0x8C, 0x1E, 0x32]),
                      (PATCH_DATA, [0x7F, 0x7E, 0x97, 0x59, 0xB3, 0x12, 0xE0]),
                      (PATCH_DATA, [0x6B, 0xC1, 0xBC, 0xA6, 0xEC, 0x6A, 0x1C]),
                      (PATCH_DATA, [0xB6, 0xFC, 0xD0, 0x89, 0xB8, 0x72, 0xA9]),
                      (PATCH_DATA, [0x64, 0xC3, 0x84, 0x1A, 0x0B, 0x7C, 0x3C]),
                      (PATCH_DATA, [0xCA, 0x3B, 0x16, 0x81, 0x0B, 0x81, 0xD7]),
                      (PATCH_DATA, [0x84, 0x1C, 0xC7, 0x49, 0x0D, 0x30, 0x90]),
                      (PATCH_DATA, [0x8E, 0x2C, 0x98, 0x01, 0xE9, 0x78, 0xAD]),
                      (PATCH_DATA, [0x26, 0x76, 0xAF, 0x0B, 0x13, 0x77, 0xC1]),
                      (PATCH_DATA, [0x1D, 0xF3, 0x61, 0x26, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x04, 0x31, 0x9A, 0x8E, 0xED]),
                      (PATCH_DATA, [0xE5, 0x74, 0x60, 0xA0, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x04, 0x60, 0x2B, 0xAE, 0x2F]),
                      (PATCH_DATA, [0xA9, 0xEA, 0x91, 0x98, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x24, 0xC8, 0x94, 0xC0, 0x30]),
                      (PATCH_DATA, [0x8B, 0x67, 0xDD, 0x55, 0x06, 0x1E, 0x6F]),
                      (PATCH_DATA, [0x50, 0xF0, 0xDE, 0xFF, 0x35, 0xF0, 0x17]),
                      (PATCH_DATA, [0x9A, 0xB3, 0xA0, 0xFA, 0x6F, 0xB6, 0x19]),
                      (PATCH_DATA, [0x7A, 0x2A, 0xA6, 0x26, 0x24, 0x27, 0xAD]),
                      (PATCH_DATA, [0xA3, 0x9F, 0x1F, 0x62, 0x05, 0x22, 0x08]),
                      (PATCH_DATA, [0x52, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x04, 0x76, 0x78, 0x0F, 0xE3]),
                      (PATCH_DATA, [0x8E, 0xB1, 0x84, 0x6C, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x04, 0x1F, 0x72, 0xCA, 0xC6]),
                      (PATCH_DATA, [0x73, 0x65, 0xC2, 0xD4, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x02, 0x69, 0x94, 0xD8, 0x6D]),
                      (PATCH_DATA, [0xDA, 0xED, 0x00, 0x00, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x02, 0xCC, 0x2E, 0x52, 0x86]),
                      (PATCH_DATA, [0x10, 0x36, 0x00, 0x00, 0x00, 0x00, 0x00]),
                      (PATCH_ARGS, [0x00, 0x00, 0x00, 0x00, 0x00, 0xD1, 0x95])]

    def __init__(self):
        self._lock = DeferredLock()
        self._device = Device(0x11, 1)
        self.power = self.OFF
        
    @locking
    def on(self):
        if self.power == self.ON:
            return

        reactor.callInThread(self.log.debug, 'Sending power up in normal mode')
        self._device.writeList(self.POWER_UP, [(self.GPO2EN | self.XOSCEN | self.WB), self.OPMODE])
        self.power = self.ON
        time.sleep(2.0) # was self.PUP_DELAY

    @locking
    def patch(self):
        if self.power == self.ON:
            return

        reactor.callFromThread(self.log.debug, 'Sending power up in patch mode')
        self._device.writeList(self.POWER_UP, [(self.GPO2EN | self.PATCH | self.XOSCEN | self.WB), self.OPMODE])
        time.sleep(self.PUP_DELAY)

        reactor.callFromThread(self.log.debug, 'Starting patch')
        
        for command, data in self.PATCH_COMMANDS:
            self._device.writeList(command, data)
            time.sleep(0.02)
            #result = self._device.readList(0, 1)

        reactor.callFromThread(self.log.debug, 'Patch finished')
        self.power = self.ON
        time.sleep(2.0)
        
    @locking
    def off(self):
        if self.power == self.OFF:
            return
        self._device.write8(self.POWER_DOWN, 0x00)
        self.power = self.OFF
        time.sleep(self.CMD_DELAY)

    @locking
    def getRevision(self):
        self._device.write8(self.GET_REV, 0x0)
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 9)
        return {'part_number': 'Si470{}'.format(result[1]),
                'patch_id': '0x{:04x}'.format(result[4] << 8 | result[5]),
                'firmware_revision': '0x{:02x}{:02x}'.format(result[2], result[3]),
                'component_firmware_revision': '0x{:02x}{:02x}'.format(result[6], result[7]),
                'chip_revision': '0x{:02x}'.format(result[8])}

    @locking
    def getTuneStatus(self, mode = CHECK):
        self._device.write8(self.WB_TUNE_STATUS, mode)
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 6)
        
        channel = result[2] << 8 | result[3]
        frequency = channel * 2500
        rssi = result[4] - 107
        snr = result[5]
        
        return {'channel': channel,
                'frequency': frequency,
                'rssi': rssi,
                'snr': snr}

    @locking
    def getRSQStatus(self, mode = CHECK):
        self._device.write8(self.WB_RSQ_STATUS, mode)
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 8)
        
        rsq_status = result[1]
        rssi = result[4] - 107
        snr = result[5]
        frequency_offset = result[7]
        if frequency_offset >= 128:
            frequency_offset = frequency_offset - 256
        frequency_offset = frequency_offset >> 1
        
        return {'rsq_status': rsq_status,
                'rssi': rssi,
                'rssi_units': 'dBm',
                'snr': snr,
                'snr_unit': 'dBµV',
                'frequency_offset': frequency_offset,
                'frequency_offset_units': 'Hz'}

    @locking
    def getIntStatus(self):
        self._device.write8(self.GET_INT_STATUS, 0)
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 1)
        return result[0]

    @locking
    def getAGCStatus(self):
        self._device.write8(self.WB_AGC_STATUS, 0)
        time.sleep(self.CMD_DELAY)
        response = self._device.readList(0, 2)
        return response[1]

    @locking
    def setAGCStatus(self, setting):
        self._device.write8(self.WB_AGC_OVERRIDE, setting)
        time.sleep(self.CMD_DELAY)

    @locking
    def getASQStatus(self, mode = CHECK):

        self._device.write16(self.WB_ASQ_STATUS, mode)
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 3)
        return result[1]

    def setVolume(self, volume):
        if volume > 0x003F:
            volume = 0x003F

        if volume < 0x0000:
            volume = 0x0000

        self.setProperty(self.RX_VOLUME, volume)

    def getVolume(self):
        return self.getProperty(self.RX_VOLUME)

    def volumeIncrease(self):
        d = self.getVolume()
        d.addCallback(self._volumeIncrease)

    def _volumeIncrease(self, result):
        self.setVolume(result + 1)
        
    def volumeDecrease(self):
        d = self.getVolume()
        d.addCallback(self._volumeDecrease)

    def _volumeDecrease(self, result):
        self.setVolume(result - 1)

    def setMute(self, value):
        if value:
            self.setProperty(self.RX_HARD_MUTE, 0x0003)

        else:
            self.setProperty(self.RX_HARD_MUTE, 0x0000)

    def getMute(self):
        response = Deferred()
        d = self.getProperty(self.RX_HARD_MUTE)
        d.addCallback(self._getMute, response)
        return response

    def _getMute(self, result, response):
        if result == 0x0003:
            response.callback(True)
        elif result == 0x0000:
            response.callback(False)
        else:
            response.callback(None)
    
    @locking
    def setProperty(self, prop, value):
        pHi, pLo = divmod(prop, 0x100)
        vHi, vLo = divmod(value, 0x100)
        reactor.callInThread(self.log.debug,
                             'Set property {pHi:02X}{pLo:02X} = {vHi:02X}{vLo:02X}',
                             pHi = pHi, pLo = pLo, vHi = vHi, vLo = vLo)
        self._device.writeList(self.SET_PROPERTY, [0x00, pHi, pLo, vHi, vLo])
        time.sleep(0.5)

    @locking
    def getProperty(self, prop):
        pHi, pLo = divmod(prop, 0x100)
        self._device.writeList(self.GET_PROPERTY, [0x00, pHi, pLo])
        time.sleep(self.CMD_DELAY)
        result = self._device.readList(0, 4)
        reactor.callInThread(self.log.debug,
                             'Get property {pHi:02X}{pLo:02X}: {result:}',
                             pHi = pHi, pLo = pLo, result = result)
        return result[2] << 8 | result[3]

    @locking
    def getSameStatus(self, mode = CHECK):
        self._device.writeList(self.WB_SAME_STATUS, [mode, 0x00])
        result = self._device.readList(0, 14)

        sameStatus = result[1]
        sameState = result[2]
        sameLength = result[3]

        if not(sameStatus & self.HDRRDY):
            reactor.callInThread(self.log.debug, 'No SAME header ready!')
            return (sameStatus, sameState, sameLength, [], b'', '')

        if sameLength < self.SAME_MIN_LENGTH:
            reactor.callInThread(self.log.debug, 'SAME message too short')
            return (sameStatus, sameState, sameLength, [], b'', '')

        confidence = []
        data = []
        
        for i in range(0, sameLength, 8):
            self._device.writeList(self.WB_SAME_STATUS, [self.CHECK, i])
            result = self._device.readList(0, 14)

            confidence.append((result[self.SAME_STATUS_OUT_CONF0_BYTE] & self.SAME_STATUS_OUT_CONF0_MASK) >> self.SAME_STATUS_OUT_CONF0_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF1_BYTE] & self.SAME_STATUS_OUT_CONF1_MASK) >> self.SAME_STATUS_OUT_CONF1_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF2_BYTE] & self.SAME_STATUS_OUT_CONF2_MASK) >> self.SAME_STATUS_OUT_CONF2_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF3_BYTE] & self.SAME_STATUS_OUT_CONF3_MASK) >> self.SAME_STATUS_OUT_CONF3_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF4_BYTE] & self.SAME_STATUS_OUT_CONF4_MASK) >> self.SAME_STATUS_OUT_CONF4_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF5_BYTE] & self.SAME_STATUS_OUT_CONF5_MASK) >> self.SAME_STATUS_OUT_CONF5_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF6_BYTE] & self.SAME_STATUS_OUT_CONF6_MASK) >> self.SAME_STATUS_OUT_CONF6_SHFT)
            confidence.append((result[self.SAME_STATUS_OUT_CONF7_BYTE] & self.SAME_STATUS_OUT_CONF7_MASK) >> self.SAME_STATUS_OUT_CONF7_SHFT)

            data.append(result[6])
            data.append(result[7])
            data.append(result[8])
            data.append(result[9])
            data.append(result[10])
            data.append(result[11])
            data.append(result[12])
            data.append(result[13])

        return (sameStatus, sameState, sameLength, confidence, bytes(data).decode('ascii', 'replace'), data)

    @locking
    def sameFlush(self):
        reactor.callInThread(self.log.debug, 'SAME flush!')
        self._device.writeList(self.WB_SAME_STATUS, [self.CLRBUF | self.INTACK, 0x00])
        
    #def tuneDirect(self, direct):
    #    if (direct < 162400) or (direct > 162550):
    #        return
    #    channel = int(direct / 2.5)

    @locking
    def tune(self, lowByte):
        self._device.writeList(self.WB_TUNE_FREQ, [0x00, self.freqHighByte, lowByte])
        time.sleep(self.TUNE_DELAY)
