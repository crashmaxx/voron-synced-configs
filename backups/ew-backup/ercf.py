# Enraged Rabbit Carrot Feeder
#
# Copyright (C) 2021  Ette
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import math
from . import pulse_counter
from . import force_move
import toolhead
import copy

class EncoderCounter:

    def __init__(self, printer, pin, sample_time, poll_time, encoder_steps):
        self._last_time = self._last_count = None
        self._counts = 0
        self._encoder_steps = encoder_steps
        self._counter = pulse_counter.MCU_counter(printer, pin, sample_time,
                                    poll_time)
        self._counter.setup_callback(self._counter_callback)

    def _counter_callback(self, time, count, count_time):
        if self._last_time is None:  # First sample
            self._last_time = time
        elif count_time > self._last_time:
            self._last_time = count_time
            self._counts += count - self._last_count
        else:  # No counts since last sample
            self._last_time = time
        self._last_count = count

    def get_counts(self):
        return self._counts

    def get_distance(self):
        return (self._counts/2.) * self._encoder_steps

    def set_distance(self, new_distance):
        self._counts = int( ( new_distance / self._encoder_steps ) * 2. )

    def reset_counts(self):
        self._counts = 0.

class Ercf:

    LONG_MOVE_THRESHOLD = 70.

    def __init__(self, config):
        self.config = config
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.printer.register_event_handler("klippy:connect",
                                            self.handle_connect)
		# Encoder Settings
        self.encoder_pin = config.get('encoder_pin')
        self.encoder_resolution = config.getfloat('encoder_resolution', 1.5,
                                            above=0.)
        self._counter = EncoderCounter(self.printer, self.encoder_pin, 0.01,
                                            0.00001, self.encoder_resolution)
        
        # Parameters
        self.long_moves_speed = config.getfloat('long_moves_speed', 10.)
        self.long_moves_accel = config.getfloat('long_moves_accel', 50.)
        self.short_moves_speed = config.getfloat('short_moves_speed', 5.)
        self.short_moves_accel = config.getfloat('short_moves_accel', 25.)
        self.min_bowden_length = config.getfloat('min_bowden_length', 100.)
        self.clog_detection = config.getboolean('clog_detection', False)
        # GCODE commands
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('ERCF_CALIBRATE_ENCODER',
                    self.cmd_ERCF_CALIBRATE_ENCODER,
                    desc=self.cmd_ERCF_CALIBRATE_ENCODER_help)
        self.gcode.register_command('ERCF_RESET_ENCODER_COUNTS',
                    self.cmd_ERCF_RESET_ENCODER_COUNTS,
                    desc=self.cmd_ERCF_RESET_ENCODER_COUNTS_help)

    def handle_connect(self):
        self.toolhead = self.printer.lookup_object('toolhead')
		
    def get_status(self, eventtime):
        encoder_pos = float(self._counter.get_distance())
        return {'encoder_pos': encoder_pos}
		
    def _sample_stats(self, values):
        mean = 0.
        stdev = 0.
        vmin = 0.
        vmax = 0.
        if values:
            mean = sum(values) / len(values)
            diff2 = [( v - mean )**2 for v in values]
            stdev = math.sqrt( sum(diff2) / ( len(values) - 1 ))
            vmin = min(values)
            vmax = max(values)
        return {'mean': mean, 'stdev': stdev, 'min': vmin,
                        'max': vmax, 'range': vmax - vmin}

    cmd_ERCF_CALIBRATE_ENCODER_help = "Calibration routine for the ERCF encoder"
    def cmd_ERCF_CALIBRATE_ENCODER(self, gcmd):
        dist = gcmd.get_float('DIST', self.min_bowden_length, above=0.)
        dist -= 50.0
        repeats = gcmd.get_int('RANGE', 5, minval=1)
        speed = gcmd.get_float('SPEED', self.long_moves_speed, above=0.)
        accel = gcmd.get_float('ACCEL', self.long_moves_accel, above=0.)
        plus_values, min_values = [], []

        for x in range(repeats):
            # Move forward
            self._counter.reset_counts()
            self.gcode.run_script_from_command(
                        "M83\n"
                        "FORCE_MOVE STEPPER=extruder"
                        " DISTANCE=%s VELOCITY=%s ACCEL=%s"
                        % (dist, speed, accel))
            plus_values.append(self._counter.get_counts())
            self.gcode.respond_info("+ counts =  %.3f"
                        % (self._counter.get_counts()))
            # Move backward
            self._counter.reset_counts()
            self.gcode.run_script_from_command(
                        "M83\n"
                        "FORCE_MOVE STEPPER=extruder"
                        " DISTANCE=-%s VELOCITY=%s ACCEL=%s"
                        % (dist, speed, accel))
            min_values.append(self._counter.get_counts())
            self.gcode.respond_info("- counts =  %.3f"
                        % (self._counter.get_counts()))

        gcmd.respond_info("Load direction: mean=%(mean).2f stdev=%(stdev).2f"
                          " min=%(min)d max=%(max)d range=%(range)d"
                          % self._sample_stats(plus_values))
        gcmd.respond_info("Unload direction: mean=%(mean).2f stdev=%(stdev).2f"
                          " min=%(min)d max=%(max)d range=%(range)d"
                          % self._sample_stats(min_values))

        mean_plus = self._sample_stats(plus_values)['mean']
        mean_minus = self._sample_stats(min_values)['mean']
        half_mean = ( float(mean_plus) + float(mean_minus) ) / 4
        if half_mean == 0:
                          gcmd.respond_info("Filament motion not detected")
        else:
                          old_result = half_mean * self.encoder_resolution
                          new_result = half_mean * resolution

                          gcmd.respond_info("Before calibration measured length = %.6f" 
                                            % old_result)
                          gcmd.respond_info("Resulting resolution for the encoder = %.6f" 
                                            % resolution)
                          gcmd.respond_info("After calibration measured length = %.6f" 
                                            % new_result)

    cmd_ERCF_RESET_ENCODER_COUNTS_help = "Reset the ERCF encoder counts"
    def cmd_ERCF_RESET_ENCODER_COUNTS(self, gcmd):
        self._counter.reset_counts() 
		
def load_config(config):
    return Ercf(config)
