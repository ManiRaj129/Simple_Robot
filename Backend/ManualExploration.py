import curses
import time
import MotorControl as motor

def main(stdscr):
    motor.initialSetUp()
    motor.setup()
    curses.cbreak()
    stdscr.nodelay(True)
    stdscr.addstr(0, 0, "Use w/a/s/d to move, q to quit.")
    stdscr.refresh()

    while True:
        key = stdscr.getch()

        if key == ord('w'):
            motor.move_forward()
            time.sleep(0.25)
            motor.stop()
        elif key == ord('s'):
            motor.move_backward()
            time.sleep(0.25)
            motor.stop()
        elif key == ord('a'):
            motor.move_left()
            time.sleep(0.7)
            motor.stop()
        elif key == ord('d'):
            motor.move_right()
            time.sleep(0.7)
            motor.stop()
        elif key == ord('q'):
            motor.stop()
            break
        else:
            time.sleep(0.05)
        time.sleep(0.05)
    motor.cleanup()

curses.wrapper(main)
