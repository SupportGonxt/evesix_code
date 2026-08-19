"""Relay stress test - fire the relay at a fixed rate and report the timing.

The default profile is the theory we want to test: 100 relay triggers with
10 seconds between switching on and switching off again. That is a 20 second
cycle - 10s energised, 10s released - so a full 100 cycle run takes about
33 minutes. Shorten it with --cycles while testing.

Same relay and same polarity as the cleaning cycle in pageOne.py: GPIO 20
driven through lgpio, active LOW (write False = coil energised = "relay on",
write True = released). Nothing else in this script touches the LEDs, the
buzzer or the database - it only moves the relay so we can see whether the
hardware keeps up with the rate.

Normally this is started by the "trigger relay" button on the admin settings
screen (pages.py) - press it, then read the results over SSH:

    tail -n 200 ~/apps/evesix_code/logs/relay_test.log

Every run appends a block to that log: the requested profile, a summary line
per pass, then one line per individual trigger showing when it fired, how
long the coil actually stayed energised and how far behind schedule it was.
That per-cycle detail is the point - averages alone hide a relay that is
missing every fifth trigger.

It runs standalone over SSH too:

    python3 relay_stress.py                    # 100 cycles, 10s on / 10s off
    python3 relay_stress.py --cycles 5         # quick 100 second sanity check
    python3 relay_stress.py --on 2 --off 2     # faster cycle
    python3 relay_stress.py --dry-run          # no GPIO, just prove the timing

The admin screen parses the "PROGRESS done total" lines below to drive its
progress bar, so keep that format if you change the output.
"""
import argparse
import os
import platform
import signal
import sys
import time

RELAY_PIN = 20

# The relay board is active LOW: pulling the line low energises the coil.
# These mirror the raw True/False writes used in pageOne.py.
RELAY_ON = 0
RELAY_OFF = 1

# Below this the mechanical relay is being asked to switch faster than it
# can physically settle. We still run it - that is the point of the test -
# but the operator gets told the contacts may be chattering rather than
# cleanly closing.
MIN_SETTLE_PERIOD_MS = 50.0

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'relay_test.log')


class DryRunRelay:
    """Stand-in for the GPIO chip so the timing can be checked off-Pi."""

    def __init__(self, pin):
        self.pin = pin
        self.writes = 0

    def write(self, value):
        self.writes += 1

    def close(self):
        pass


class LgpioRelay:
    """The real thing: GPIO 20 claimed as an output through lgpio."""

    def __init__(self, pin):
        import lgpio

        self._lgpio = lgpio
        self.pin = pin
        self.handle = lgpio.gpiochip_open(0)
        try:
            # Claim with the relay already released so the coil does not
            # click the moment we take the line.
            lgpio.gpio_claim_output(self.handle, pin, RELAY_OFF)
        except Exception:
            lgpio.gpiochip_close(self.handle)
            raise

    def write(self, value):
        self._lgpio.gpio_write(self.handle, self.pin, value)

    def close(self):
        try:
            self._lgpio.gpio_write(self.handle, self.pin, RELAY_OFF)
        finally:
            self._lgpio.gpiochip_close(self.handle)


def open_relay(dry_run):
    if dry_run:
        print('[relay-test] dry run: GPIO is not touched, timing only')
        return DryRunRelay(RELAY_PIN)
    try:
        return LgpioRelay(RELAY_PIN)
    except ImportError:
        print('[relay-test] ERROR: lgpio is not installed - this script only '
              'drives the relay on the robot. Use --dry-run to check timing here.')
        raise SystemExit(2)
    except Exception as e:
        print(f'[relay-test] ERROR: could not claim GPIO {RELAY_PIN}: {e}')
        print('[relay-test] GPIO 20 is held by whoever is driving the relay - '
              'if a cleaning cycle is running, stop it and try again.')
        raise SystemExit(2)


def run_pass(relay, cycles, on_time, off_time, progress_every):
    """Cycle the relay `cycles` times: on_time energised, off_time released.

    Switch-on moments are scheduled against a fixed start point rather than
    by sleeping the period each time round, so one slow cycle does not push
    every later cycle back with it.

    The coil always gets its full on_time though - only the release phase
    absorbs catch-up. Trimming the pulse instead would let the script report
    triggers that were too short for the relay to physically close, which is
    the one number this test must not fake. If the machine cannot keep up,
    the pass simply runs long and the measured rate says so.

    Returns the measured stats for the pass.
    """
    period = on_time + off_time
    start = time.perf_counter()
    on_total = 0.0
    on_min = None
    on_max = 0.0
    slow_cycles = 0
    worst_overrun = 0.0
    samples = []

    for i in range(cycles):
        target_on = start + i * period

        # How late we are taking the line low, i.e. how far behind schedule
        # the previous cycles have left us.
        overrun = time.perf_counter() - target_on
        if overrun > 0.001:
            slow_cycles += 1
            worst_overrun = max(worst_overrun, overrun)

        pulse_start = time.perf_counter()
        relay.write(RELAY_ON)
        time.sleep(on_time)
        relay.write(RELAY_OFF)
        actual_on = time.perf_counter() - pulse_start

        on_total += actual_on
        on_max = max(on_max, actual_on)
        on_min = actual_on if on_min is None else min(on_min, actual_on)

        # Kept per cycle so the log read over SSH shows which individual
        # triggers misbehaved, not just the averages.
        samples.append({
            'n': i + 1,
            'at_s': pulse_start - start,
            'on_s': actual_on,
            'overrun_ms': overrun * 1000.0,
        })

        sleep_until(target_on + period)

        done = i + 1
        if progress_every and (done % progress_every == 0 or done == cycles):
            print(f'PROGRESS {done} {cycles}', flush=True)

    elapsed = time.perf_counter() - start
    return {
        'cycles': cycles,
        'elapsed': elapsed,
        'avg_cycle_s': elapsed / cycles if cycles else 0.0,
        'on_avg_s': on_total / cycles if cycles else 0.0,
        'on_min_s': on_min if on_min is not None else 0.0,
        'on_max_s': on_max,
        'slow_cycles': slow_cycles,
        'worst_overrun_ms': worst_overrun * 1000.0,
        'samples': samples,
    }


def format_duration(seconds):
    """Human duration - runs at 10s on/off are minutes long, not seconds."""
    if seconds < 90:
        return f'{seconds:.1f}s'
    minutes, secs = divmod(int(round(seconds)), 60)
    return f'{minutes}m {secs:02d}s'


def sleep_until(deadline):
    """Sleep to an absolute perf_counter deadline, skipping if already past."""
    remaining = deadline - time.perf_counter()
    if remaining > 0:
        time.sleep(remaining)


def append_log(path, lines):
    """Append one run's block to the log file that gets read over SSH."""
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, 'a') as fh:
            for line in lines:
                fh.write(f'{stamp} {line}\n')
    except OSError as e:
        print(f'[relay-test] WARNING: could not write log {path}: {e}')


def parse_args(argv):
    parser = argparse.ArgumentParser(description='Stress test the GPIO 20 relay.')
    parser.add_argument('--cycles', type=int, default=100,
                        help='relay triggers per pass (default: 100)')
    parser.add_argument('--on', type=float, default=10.0, dest='on_time',
                        help='seconds the relay stays energised (default: 10)')
    parser.add_argument('--off', type=float, default=10.0, dest='off_time',
                        help='seconds the relay stays released (default: 10)')
    parser.add_argument('--repeat', type=int, default=1,
                        help='number of passes to run (default: 1)')
    parser.add_argument('--rest', type=float, default=0.0,
                        help='seconds to rest between passes (default: 0)')
    parser.add_argument('--progress-every', type=int, default=1,
                        help='emit a PROGRESS line every N cycles, 0 to silence')
    parser.add_argument('--dry-run', action='store_true',
                        help='do not touch GPIO, just run and measure the timing')
    parser.add_argument('--log', default=DEFAULT_LOG,
                        help=f'result log file (default: {DEFAULT_LOG})')
    args = parser.parse_args(argv)

    if args.cycles < 1:
        parser.error('--cycles must be at least 1')
    if args.on_time <= 0:
        parser.error('--on must be greater than 0')
    if args.off_time < 0:
        parser.error('--off cannot be negative')
    if args.repeat < 1:
        parser.error('--repeat must be at least 1')
    return args


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)

    on_time = args.on_time
    off_time = args.off_time
    period = on_time + off_time
    total_estimate = period * args.cycles * args.repeat

    print(f'[relay-test] pin={RELAY_PIN} cycles={args.cycles} on={on_time:g}s '
          f'off={off_time:g}s cycle={period:g}s repeat={args.repeat} '
          f'estimated total {format_duration(total_estimate)}')
    if period * 1000 < MIN_SETTLE_PERIOD_MS:
        print(f'[relay-test] WARNING: {period * 1000:.1f}ms per cycle is below the '
              f'{MIN_SETTLE_PERIOD_MS:.0f}ms a mechanical relay needs to settle - '
              'expect contact chatter rather than clean switching')

    relay = open_relay(args.dry_run)

    # A stop from the admin screen or Ctrl-C has to release the coil, never
    # leave it latched on.
    interrupted = {'flag': False}

    def stop(signum, frame):
        interrupted['flag'] = True
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)

    passes = []
    try:
        for n in range(args.repeat):
            stats = run_pass(relay, args.cycles, on_time, off_time, args.progress_every)
            passes.append(stats)
            print(f"[relay-test] pass {n + 1}/{args.repeat}: {stats['cycles']} cycles in "
                  f"{format_duration(stats['elapsed'])} | cycle avg "
                  f"{stats['avg_cycle_s']:.3f}s | on avg {stats['on_avg_s']:.3f}s "
                  f"min {stats['on_min_s']:.3f}s max {stats['on_max_s']:.3f}s | "
                  f"behind schedule on {stats['slow_cycles']} cycles (worst "
                  f"{stats['worst_overrun_ms']:.1f}ms)", flush=True)
            if args.rest and n + 1 < args.repeat:
                time.sleep(args.rest)
    except KeyboardInterrupt:
        print('[relay-test] stopped early - releasing relay')
    finally:
        relay.close()
        print(f'[relay-test] relay {RELAY_PIN} released')

    total_cycles = sum(p['cycles'] for p in passes)
    total_elapsed = sum(p['elapsed'] for p in passes)
    shortest_pulse = min((p['on_min_s'] for p in passes), default=0.0)
    longest_pulse = max((p['on_max_s'] for p in passes), default=0.0)
    worst_overrun = max((p['worst_overrun_ms'] for p in passes), default=0.0)
    total_slow = sum(p['slow_cycles'] for p in passes)
    outcome = 'interrupted' if interrupted['flag'] or len(passes) < args.repeat else 'ok'
    result = (f'RESULT {outcome} passes={len(passes)}/{args.repeat} '
              f'cycles={total_cycles} elapsed={total_elapsed:.3f}s '
              f'avg_cycle_s={total_elapsed / total_cycles if total_cycles else 0:.3f} '
              f'on_min_s={shortest_pulse:.3f} on_max_s={longest_pulse:.3f} '
              f'slow_cycles={total_slow} worst_overrun_ms={worst_overrun:.1f}'
              f'{" dry-run" if args.dry_run else ""}')
    print(f'[relay-test] {result}', flush=True)

    # Build the block that gets read over SSH: what was asked for, what each
    # pass measured, then every individual trigger.
    log_lines = [
        '--- relay test run on ' + platform.node() + ' ---',
        f'request pin={RELAY_PIN} cycles={args.cycles} on={on_time:g}s '
        f'off={off_time:g}s cycle={period:g}s '
        f'repeat={args.repeat} dry_run={args.dry_run}',
    ]
    for n, stats in enumerate(passes, start=1):
        log_lines.append(
            f"pass {n}/{args.repeat} cycles={stats['cycles']} "
            f"elapsed={stats['elapsed']:.3f}s avg_cycle_s={stats['avg_cycle_s']:.3f} "
            f"on_avg_s={stats['on_avg_s']:.3f} on_min_s={stats['on_min_s']:.3f} "
            f"on_max_s={stats['on_max_s']:.3f} slow_cycles={stats['slow_cycles']} "
            f"worst_overrun_ms={stats['worst_overrun_ms']:.1f}")
        for s in stats['samples']:
            log_lines.append(
                f"  pass{n} cycle {s['n']:>4} at {s['at_s']:>9.3f}s "
                f"on {s['on_s']:>8.3f}s overrun {s['overrun_ms']:>8.1f}ms")
    log_lines.append(result)
    append_log(args.log, log_lines)
    print(f'[relay-test] per-cycle detail appended to {args.log}', flush=True)
    return 0 if outcome == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
