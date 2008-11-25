#!/usr/bin/env python
# COPYRIGHT: Openmoko Inc. 2008
# LICENSE: GPL Version 2 or later
# NAME: gsm
# BEFORE: final interactive
# AFTER: python_functions
# SECTION: board gsm
# MENU: none
# DESCRIPTION: test that we can use the GSM module
# AUTHOR: Guillaume Chereau <charlie@openmoko.org>

import time
import serial
import re

import tests


class ATError(Exception):
    """Base class for AT related exceptions"""

    def __init__(self, msg):
        super(ATError, self).__init__(msg)


class SIMBusyError(ATError):

    def __init__(self):
        super(SIMBusyError, self).__init__('SIM busy')


class TimeOut(ATError):
    """Base class for timeout exceptions"""

    def __init__(self):
        super(TimeOut, self).__init__("Timeout")


class Modem(object):

    def __init__(self, dev):
        self.dev = serial.Serial(dev, 115200, rtscts=1, timeout=10)

    def read_line(self):
        """read one line from the modem

        return the line striped (with /r/n removed at the end), if we
        just receive '\r\n' then this return an empty line.
        """
        ret =''
        while True:
            c = self.dev.read(1)
            if not c:
                tests.info("modem timeout")
                raise TimeOut()
            ret += c
            if ret.endswith('\r\n'):
                break
        ret = ret.strip()
        if ret:
            tests.info("recv : %s", repr(ret))
        return ret

    def as_arg(self, arg):
        """convert python object into at command arguments string"""
        if isinstance(arg, (list, tuple)):
            return ','.join([self.as_arg(x) for x in arg])
        if isinstance(arg, str):
            return '"%s"' % arg
        return repr(arg)

    def write(self, str):
        """write to the modem"""
        tests.info('send : %s', repr(str))
        self.dev.write(str)

    def read(self, n=1):
        """read from the modem"""
        ret = self.dev.read(n)
        tests.info("recv : %s", repr(ret))
        return ret

    def chat(self, cmd, *args, **kargs):
        """Send an AT command to the modem and get the reply

        Parameters:

        - cmd : the AT command we send (not including 'AT')

        - args : the list of arguments passed to the command

        keyword parameters:

        - parser : can be used to define a specific parsing function
          for the answer from the modem
        """
        parser = kargs.get('parser', self.parse_answer)

        full_cmd = 'AT%s' % cmd
        arg = self.as_arg(args)
        full_cmd = '%s%s' % (full_cmd, arg)
        full_cmd = '%s\r' % full_cmd

        self.write(full_cmd)
        ret = self.read_answer()
        return parser(cmd, ret)

    def read_answer(self):
        """read an answer from the modem"""
        ret = []
        while True:
            line = self.read_line()
            if not line:
                continue
            if line == 'OK':
                break
            ret.append(line)

            if line.startswith('+CME ERROR'):
                raise ATError(line)
            if line.startswith('+CMS ERROR'):
                if 'SIM busy' in line:
                    raise SIMBusyError()
                raise ATError(line)
            if line.startswith('+EXT ERROR'):
                raise ATError(line)
            if line.startswith('ERROR'):
                raise ATError(line)
        return ret

    def reset(self):
        pass

    def parse_answer(self, cmd, answer):
        """Parse *most* of the AT answer messages

        This should be overriden for specific commands
        """
        if cmd.endswith('?'):
            cmd = cmd[:-1]
        if cmd.endswith('='):
            cmd = cmd[:-1]

        if isinstance(answer, list):
            if len(answer) == 1:
                return self.parse_answer(cmd, answer[0])
            else:
                return [self.parse_answer(cmd, l) for l in answer]

        if answer.startswith('%s:' % cmd): # standard reply
            ret = answer.split(': ', 1)[1].strip()
            return ret
        else:
            return answer

        raise ATError("Bad command format : %s" % answer)


class Calypso(Modem):

    def reset(self):
        """Initialize the modem before we can start sending AT commands
        """
        tests.info("turn modem off")
        sys_dir = '/sys/devices/platform/neo1973-pm-gsm.0'
        open('%s/power_on' % sys_dir, 'w').write('0')
        time.sleep(1)
        tests.info("turn modem on")
        open('%s/power_on' % sys_dir, 'w').write('1')
        time.sleep(1)
        tests.info("reset modem")
        open('%s/reset' % sys_dir, 'w').write('1')
        time.sleep(1)
        open('%s/reset' % sys_dir, 'w').write('0')
        time.sleep(4)
        msg = self.read_line()
        tests.info("got ready messages : %s", repr(msg))
        tests.info("send empty command to calypso")
        self.dev.write('\r')
        self.dev.read()


class GSMTest(tests.Test):
    """Test the gsm module

    This test is supposed to work on both GTA02 using TI Calypso modem
    and on GTA03 with the Siemens MC75i modem.
    """

    def chat(self, cmd, *args, **kargs):
        error = kargs.get('error', 'fail')
        try:
            return self.modem.chat(cmd, *args, **kargs)
        except ATError, e:
            err_msg = "when sending AT%s : %s" % (cmd, e)
            if error == 'fail':
                self.fail(err_msg)
            if error == 'info':
                self.info(err_msg)
            if error == 'raise':
                raise

    def run(self):
        self.conf = tests.parse_conf('tests.cfg')

        self.modem = Calypso('/dev/ttySAC0')
        self.modem.reset()
        self.init()
        self.info("== Testing basics ==")
        self.test_basics()
        self.info("== Testing contacts ==")
        self.test_contacts()
        self.info("== Testing network ==")
        self.test_network()
        self.info("== Testing call ==")
        self.test_call()
        self.info("== Testing SMS ==")
        self.test_sms()
        self.info("== Testing PDU SMS ==")
        self.test_pdu_sms()

    def init(self):
        """initialize the modem"""
        self.chat('')           # void command
        self.chat('E0')       # echo off
        self.chat('Z')        # reset
        self.chat('+CMEE=', 2)  # verbose error

    def test_basics(self):
        """Run some basic tests, not using the SIM"""
        self.chat('+CMUX?')      # Multiplexing mode
        self.chat('+CGMM')       # Model id
        self.chat('+CGMR')       # Firmware version
        self.chat('+CGMI')       # Manufacturer id
        ipr = self.chat('+IPR?') # Bit rate
        self.check(ipr == '115200', "check that baudrate == 115200")
        self.chat('ICF?')        # Character framing
        self.chat('S3?')         # Command line term
        self.chat('S4?')         # Response formating
        self.chat('S5?')         # Command line editing char
        self.chat('+ICF?')       # TE-TA char framing
        self.chat('+IFC?')       # Flow control (calypso != MC75i)
        self.chat('+CSCS?')      # Character set
        self.chat('+CFUN?')      # Phone functionalities
        # self.modem.chat('+CLAC')       # List of AT commands

    def test_network(self):
        """Try to register on the network"""
        self.chat('+CFUN=', 1) # Turn on antenna
        self.chat('+COPS=', 0) # Register on a network
        self.chat('+CREG?')  # check that we are registered

    def test_call(self):
        """Make phone calls"""
        number = self.conf.get('CALLABLE_NUMBER', None)
        if not number:
            self.info("can't find a callable number in conf file")
            self.info("skip call tests")
            return True
        self.chat('D%s;' % number)
        self.operator_confirm("number %s is ringing within ~30 seconds",
                              number)
        self.chat('H')    # release the call
        self.operator_confirm("ringing stopped within ~10 seconds")

    def test_contacts(self):
        """Try to get the contacts list"""
        self.chat('+CPIN?')
        self.chat('+CPBS=', 'SM')

        # with calypso, +CPBR=? sometime fails !
        for i in range(5):
            try:
                ranges = self.chat('+CPBR=?', error='raise')
                break
            except:
                self.info("trying again in one second")
                time.sleep(10)
        else:
            return self.fail("Can't get contact range")

        # parse the returned value
        r = re.compile(r'\((\d+)-(\d+)\),\d+,\d+')
        match = r.match(ranges)
        self.check(match, "+CPBR=? returned a valid answer")
        if not match:
            return
        i_min, i_max = int(match.group(1)), int(match.group(2))

        # Get all the contacts
        r = re.compile(r'(\d+),"(.+)",(\d+),"(.+)"')
        all_contacts = []
        for index in range(i_min, i_max+1):
            contact = self.chat('+CPBR=', index)
            if contact:
                match = r.match(contact)
                self.check(match, "+CPBR=%d returned a valid answer", index)
                i = int(match.group(1))
                number = match.group(2)
                type = int(match.group(3))
                name = match.group(4)
                all_contacts.append((name, number))
        self.test_find_contact(all_contacts)

    def test_find_contact(self, contacts):
        """Check that we found the contact specified in the conf file

        we check for a SIM_CONTACT value in the conf file, that should
        be or the form "name:number"

        Parameters:

        - contacts : a list of tuple (name, number) representing the
          contacts found in the sim
        """
        contact = self.conf.get('SIM_CONTACT', None)
        if not contact:
            self.info('no SIM_CONTACT field in the conf file, skip test')
            return
        name, number = contact.split(':')
        ok = name in [x[0] for x in contacts]
        if not self.check(ok, 'Find contact "%s" in the SIM', name):
            return
        ok = number in [x[1] for x in contacts if x[0] == name]
        self.check(ok, 'Contact "%s" has number "%s"', name, number)

    def _try_send_sms(self, number):
        """try to send an SMS, may raise SIMBusyError"""
        self.chat('+CMGF=', 1)  # Set text mode
        self.modem.write('AT+CMGS="%s"\r' % number)
        self.modem.read(4)      # Wait for the '>'
        self.modem.write('hello')
        self.modem.write('\x1a')
        self.modem.read_answer()

    def _try_send_pdu_sms(self, number):
        """try to send a PDU SMS, may raise SIMBusyError"""
        # We need to invert every two characters in the number
        pdu_number = ''.join(
            '%s%s' % (y, x) for x, y in zip(number[::2], number[1::2]))
        self.chat('+CMGF=', 0)  # Set pdu mode
        self.modem.write('AT+CMGS=%d\r' % 17)
        self.modem.read(4)       # Wait for the '>'
        self.modem.write('0001000A81%s000005E8329BFD06' % pdu_number)
        self.modem.write('\x1a')
        self.modem.read_answer()

    def test_sms(self):
        """Test that we can send and receive SMS"""
        number = self.conf.get('CALLABLE_NUMBER', None)
        if not number:
            self.info("can't find a callable number in conf file")
            self.info("skip sms tests")
            return True
        # Try direct sending of SMS in text mode
        for i in range(3):
            try:
                self._try_send_sms(number)
                self.operator_confirm("received SMS with text : 'hello'")
                break
            except SIMBusyError:
                self.info('sim busy, try again in 10 seconds')
                time.sleep(10)
                continue
        else:
            self.fail("can't send PDU SMS")

    def test_pdu_sms(self):
        # XXX: this test may not work with number that don't have 10
        # digits
        number = self.conf.get('CALLABLE_NUMBER', None)
        if not number:
            self.info("can't find a callable number in conf file")
            self.info("skip pdu sms tests")
            return True
        for i in range(5):
            try:
                self._try_send_sms(number)
                self.operator_confirm("received SMS with text : 'hello'")
                break
            except SIMBusyError:
                self.info('sim busy, try again in 10 seconds')
                time.sleep(10)
                continue
        else:
            self.fail("can't send PDU SMS")

if __name__ == '__main__':
    GSMTest().execute()
