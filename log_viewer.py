#!/usr/bin/env python3
"""
Live Log Viewer for Robot Dashboard
Usage: python3 log_viewer.py [options]

Run this from another terminal or SSH session to monitor logs in real-time.
"""

import sys
import time
import argparse
import os
from pathlib import Path

LOG_FILE = "/var/log/robot/robot.log"


def tail_file(filename, lines=50, follow=False):
    """
    Tail a log file similar to 'tail -f'
    
    Args:
        filename: Path to log file
        lines: Number of initial lines to show
        follow: If True, continuously follow the file (like tail -f)
    """
    try:
        with open(filename, 'r') as f:
            # Read all lines
            all_lines = f.readlines()
            
            # Print last N lines
            for line in all_lines[-lines:]:
                print(line, end='')
            
            if follow:
                # Move to end of file
                f.seek(0, 2)
                
                print("\n[Following log file - Press Ctrl+C to exit]")
                print("-" * 60)
                
                while True:
                    line = f.readline()
                    if line:
                        print(line, end='')
                        sys.stdout.flush()
                    else:
                        time.sleep(0.1)
                        
    except FileNotFoundError:
        print(f"Error: Log file not found: {filename}")
        print("\nMake sure the robot service is running:")
        print("  sudo systemctl status robot.service")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied reading {filename}")
        print("\nTry running with sudo:")
        print(f"  sudo python3 {sys.argv[0]}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[Stopped tailing log]")
        sys.exit(0)


def show_service_status():
    """Show the systemd service status"""
    print("Robot Service Status:")
    print("-" * 60)
    os.system("systemctl status robot.service --no-pager")
    print()


def show_recent_errors(filename, minutes=5):
    """Show recent error/warning lines from the log"""
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
            
        print(f"Recent Errors/Warnings (last {len(lines)} lines):")
        print("-" * 60)
        
        error_count = 0
        for line in lines:
            if any(keyword in line.lower() for keyword in ['error', 'warning', 'exception', 'traceback', 'critical']):
                print(line, end='')
                error_count += 1
        
        if error_count == 0:
            print("No errors or warnings found!")
        else:
            print(f"\nFound {error_count} error/warning lines")
            
    except Exception as e:
        print(f"Error reading log: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Live log viewer for Robot Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Show last 50 lines
  %(prog)s -f                 # Follow logs in real-time
  %(prog)s -n 200             # Show last 200 lines
  %(prog)s -f -n 100          # Show last 100 lines then follow
  %(prog)s --errors           # Show only recent errors/warnings
  %(prog)s --status           # Show service status
        """
    )
    
    parser.add_argument(
        '-f', '--follow',
        action='store_true',
        help='Follow log file in real-time (like tail -f)'
    )
    
    parser.add_argument(
        '-n', '--lines',
        type=int,
        default=50,
        help='Number of initial lines to show (default: 50)'
    )
    
    parser.add_argument(
        '--log-file',
        default=LOG_FILE,
        help=f'Path to log file (default: {LOG_FILE})'
    )
    
    parser.add_argument(
        '--errors',
        action='store_true',
        help='Show only recent errors and warnings'
    )
    
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show systemd service status'
    )
    
    args = parser.parse_args()
    
    # Show service status if requested
    if args.status:
        show_service_status()
        return
    
    # Show errors if requested
    if args.errors:
        show_recent_errors(args.log_file)
        return
    
    # Tail the log file
    tail_file(args.log_file, lines=args.lines, follow=args.follow)


if __name__ == '__main__':
    main()
