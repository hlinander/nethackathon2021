import curses
from curses import wrapper
import time
import traceback
import db
import sys
import json

banner = r'''             _,---.      ,----.         ___                    
         _.='.'-,  \  ,-.--` , \ .-._ .'=.'\                   
        /==.'-     / |==|-  _.-`/==/ \|==|  |                  
       /==/ -   .-'  |==|   `.-.|==|,|  / - |                  
       |==|_   /_,-./==/_ ,    /|==|  \/  , |                  
       |==|  , \_.' )==|    .-' |==|- ,   _ |                  
       \==\-  ,    (|==|_  ,`-._|==| _ /\   |                  
        /==/ _  ,  //==/ ,     //==/  / / , /                  
        `--`------' `--`-----`` `--`./  `--`                   
   ,-,--.  ,--.--------.   _,.---._                    ,----.  
 ,-.'-  _\/==/,  -   , -\,-.' , -  `.   .-.,.---.   ,-.--` , \ 
/==/_ ,_.'\==\.-.  - ,-./==/_,  ,  - \ /==/  `   \ |==|-  _.-` 
\==\  \    `--`\==\- \ |==|   .=.     |==|-, .=., ||==|   `.-. 
 \==\ -\        \==\_ \|==|_ : ;=:  - |==|   '='  /==/_ ,    / 
 _\==\ ,\       |==|- ||==| , '='     |==|- ,   .'|==|    .-'  
/==/\/ _ |      |==|, | \==\ -    ,_ /|==|_  . ,'.|==|_  ,`-._ 
\==\ - , /      /==/ -/  '.='. -   .' /==/  /\ ,  )==/ ,     / 
 `--`---'       `--`--`    `--`--''   `--`-`--`--'`--`-----``  
'''

menu = [
        { 'name': 'hp', 'x': 8+0, 'y': 19, 'lvl': 0 },
        { 'name': 'pw', 'x': 8+16, 'y': 19, 'lvl': 0 },
        { 'name': 'ac', 'x': 8+32, 'y': 19, 'lvl': 0 },
        { 'name': 'str', 'x': 8+0, 'y': 20, 'lvl': 0 },
        { 'name': 'int', 'x': 8+16, 'y': 20, 'lvl': 0 },
        { 'name': 'wis', 'x': 8+32, 'y': 20, 'lvl': 0 },
        { 'name': 'dex', 'x': 8+0, 'y': 21, 'lvl': 0 },
        { 'name': 'con', 'x': 8+16, 'y': 21, 'lvl': 0 },
        { 'name': 'cha', 'x': 8+32, 'y': 21, 'lvl': 0 },
]

def cost(lvl):
    return lvl * 5 + 1

def update_power_levels(player_id):
    powers = db.get_clan_powers_for_player(player_id)
    for power, level in powers.items():
        for idx, item in enumerate(menu):
            if item["name"] == power:
                    menu[idx]['lvl'] = level

def main(stdscr):
    player_id = int(sys.argv[1])
    db.open_db()
    stdscr.clear()
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    no_color = curses.color_pair(1)
    selection_color = curses.color_pair(2)
    error_color = curses.color_pair(3)

    selection = 0
    error = ""
    power_gems = db.get_power_gems_for_player(player_id)
    open("log", "a").write(json.dumps(menu, indent=4))


    while True:
        power_gems = db.get_power_gems_for_player(player_id)
        update_power_levels(player_id)
        stdscr.addstr(0, 0, banner)
        for i in range(0, len(menu)):
            it = menu[i]
            c = no_color if (i != selection) else selection_color
            stdscr.addstr(it['y'], it['x'], it['name'] + ':')
            stdscr.addstr(it['y'], it['x'] + 5, '%02d' % (it['lvl']), c)
            stdscr.addstr(23, 8, f"Cost to upgrade: {cost(menu[selection]['lvl']):03d}")
            stdscr.addstr(23, 32, f'Team Power gems: {power_gems:03d}')
            stdscr.addstr(24, 8, error, error_color)
            error = ""
            stdscr.refresh()
        try:
            v = stdscr.getch()
            if -1 == v:
                continue
            n = chr(v).lower()
            if 'h' == n:
                selection -= 1
            elif 'l' == n:
                selection += 1
            elif 'k' == n:
                selection -= 3
            elif 'j' == n:
                selection += 3
            elif ' ' == n:
                if power_gems >= cost(menu[selection]['lvl']):
                    thecost = cost(menu[selection]['lvl'])
                    menu[selection]['lvl'] += 1
                    dlevel = db.add_clan_power_for_player(
                            player_id,
                            menu[selection]['name'],
                            menu[selection]['lvl'],
                            thecost)
                    menu[selection]['lvl'] = dlevel
                else:
                    error = "Not enough power gems!"


            elif 'q' == n:
                break

            if selection < 0:
                selection = len(menu) - 1
            if selection >= len(menu):
                selection = 0
        except Exception as e:
            open('/tmp/fisk', 'w').write(str(e) + '\n' + traceback.format_exc())
wrapper(main)
