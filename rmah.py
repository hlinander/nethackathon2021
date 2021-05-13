import curses
from curses import wrapper
import time
import traceback

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

def main(stdscr):
	stdscr.clear()
	curses.noecho()
	curses.start_color()
	curses.use_default_colors()
	curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
	curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GREEN)
	no_color = curses.color_pair(1)
	selection_color = curses.color_pair(2)

	selection = 0

	while True:
		stdscr.addstr(0, 0, banner)
		for i in range(0, len(menu)):
			it = menu[i]
			c = no_color if (i != selection) else selection_color
			stdscr.addstr(it['y'], it['x'], it['name'] + ':')
			stdscr.addstr(it['y'], it['x'] + 5, '%02d' % (it['lvl']), c)
		stdscr.addstr(23, 8, 'Cost to upgrade: ' + str(menu[selection]['lvl'] * 5))
		stdscr.addstr(23, 32, 'Team Power gems: ' + '123')
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
				menu[selection]['lvl'] += 1
			elif 'q' == n:
				break

			if selection < 0:
				selection = len(menu) - 1
			if selection >= len(menu):
				selection = 0
		except Exception as e:
			open('/tmp/fisk', 'w').write(str(e) + '\n' + traceback.format_exc())
wrapper(main)