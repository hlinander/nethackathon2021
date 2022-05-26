#!/usr/bin/env python3

import sys, random
import curses

def candlechart(stdscr, x, y, w, h, values, colors):
    # Get max/min range of input values
    vmax_in = max(values)
    vmin_in = min(values)
    deltav_in = (vmax_in - vmin_in) / h

    # Add in some margins
    vmax = vmax_in + deltav_in * 2
    vmin = vmin_in - deltav_in * 2
    if not (deltav_in > 0):
        vmax = vmax_in + 1
        vmin = vmin_in - 1
    deltav = (vmax - vmin) / h

    def v_to_y(v):
        if deltav > 0:
            return (v - vmin) / deltav
        else:
            return

    def y_to_v(y):
        return vmin + deltav * y

    for yp in range(h):
        vp = y_to_v(yp)
        stdscr.addstr(y+h-1-int(yp), x, '% 3d' % (int(vp))) # f"{vp:.1f}")

    nw = len(values) if len(values) < w else w
    values = values[-nw:]
    dx = 2
    for vi, val in enumerate(values):
        if vi == 0:
            continue

        yp = int(v_to_y(val))
        ypp = int(v_to_y(values[vi-1]))

        if yp == ypp:
            # print("\x1b[37;1m", flush=False, end='')
            stdscr.addstr(y+h-1-yp, x+vi+dx, "—")
        elif yp > ypp:
            # print("\x1b[32;1m", flush=False, end='')
            for i in range(ypp, yp):
                stdscr.addstr(y+h-1-i, x+vi+dx, "█", colors[0])
        elif ypp > yp:
            # print("\x1b[31;1m", flush=False, end='')
            for i in range(yp, ypp):
                stdscr.addstr(y+h-1-i, x+vi+dx, "█", colors[1])

        # print("\x1b[0m", flush=False, end='')
        # if ypp != yp:
        #     rnd = random.randint(0, 2)
        #     for i in range(rnd):
        #         yc = y+h-1-max(yp,ypp)-i
        #         if yc > y-1:
        #             movecursor( x+vi+dx, yc )
        #             print( "│", flush=False, end='' )

        #     yc = y+h-1-max(yp,ypp)-rnd
        #     if yc > y-1:
        #         movecursor( x+vi+dx, yc )
        #         print( "┬", flush=False, end='' )

        #     rnd = random.randint(0, 5)
        #     for i in range(rnd):
        #         yc = y+h-min(yp,ypp)+i
        #         if yc < y+h:
        #             movecursor( x+vi+dx, yc )
        #             print( "│", flush=False, end='' )

        #     yc = y+h-min(yp,ypp)+rnd
        #     if yc < y+h:
        #         movecursor( x+vi+dx, yc )
        #         print( "┴", flush=False, end='' )
        #

# candledata = (5, 6, 8, 3, 6, 1, 2, 1, 5, 6, 9, 8, 9, 3, 4, 8, 3, 1, 7, 6, 5, 3, 2, 1, 4, 3, 5, 4, 7, 8, 7, 7, 6, 3, 4, 3, 5, 3, 2, 7, 6, 4, 3, 6, 7, 9, 6, 4, 6, 3, 4, 8, 7)
# candledata = (1, 5, 6, 7, 3, 2)


#framedata = (
#    (2, 2, 50, 30, "Stonks 0", 1),
#    (51, 2, 50, 50, "Stonks 1", 1),
#)
#paint_frames(framedata)

#candlechart(3, 3, 48, 28, 10, candledata)
#candlechart(52, 3, 48, 48, 10, candledata)

# movecursor( 0, 33 )
# sys.stdout.flush()
