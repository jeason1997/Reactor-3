"""Reactor 3"""

from globals import *
from inputs import *
from player import *

import libtcodpy as tcod
import render_fast_los

import graphics as gfx
import traceback
import cProfile
import maputils
import worldgen
import mainmenu
import language
import profiles
import network
import drawing
import logging
import weapons
import effects
import numbers
import bullets
import dialog
import random
import numpy
import tiles
import menus
import logic
import items
import life
import time
import maps
import smp
import sys

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('[%(asctime)s-%(levelname)s] %(message)s',datefmt='%H:%M:%S %m/%d/%y')
ch = logging.StreamHandler()
ch.setFormatter(console_formatter)
logger.addHandler(ch)

CYTHON_ENABLED = True

def move_camera(pos,scroll=False):
	_orig_pos = CAMERA_POS[:]
	CAMERA_POS[0] = numbers.clip(pos[0]-(MAP_WINDOW_SIZE[0]/2),0,MAP_SIZE[0]-MAP_WINDOW_SIZE[0])
	CAMERA_POS[1] = numbers.clip(pos[1]-(MAP_WINDOW_SIZE[1]/2),0,MAP_SIZE[1]-MAP_WINDOW_SIZE[1])
	CAMERA_POS[2] = pos[2]
	
	if not _orig_pos == CAMERA_POS:
		gfx.refresh_window()

def draw_targeting():
	if LIFE[SETTINGS['controlling']] and LIFE[SETTINGS['controlling']]['targeting']:
		
		SELECTED_TILES[0] = []
		for pos in drawing.diag_line(LIFE[SETTINGS['controlling']]['pos'],LIFE[SETTINGS['controlling']]['targeting']):
			SELECTED_TILES[0].append((pos[0],pos[1],LIFE[SETTINGS['controlling']]['pos'][2]))

CURRENT_UPS = UPS

def main():
	global CURRENT_UPS
	
	get_input()
	handle_input()
	_played_moved = False

	while life.get_highest_action(LIFE[SETTINGS['controlling']]) and not life.find_action(LIFE[SETTINGS['controlling']], matches=[{'action': 'move'}]):
		logic.tick_all_objects(WORLD_INFO['map'])
		_played_moved = True
		
		if CURRENT_UPS:
			CURRENT_UPS-=1
		else:
			if life.is_target_of(LIFE[SETTINGS['controlling']]):
				CURRENT_UPS = 1
			else:
				CURRENT_UPS = 3 #ticks to run while actions are in queue before breaking
			
			gfx.refresh_window()
			break
	
	if not _played_moved:
		if CURRENT_UPS:
			CURRENT_UPS-=1
		else:
			CURRENT_UPS = 3
			logic.tick_all_objects(WORLD_INFO['map'])
			
	draw_targeting()
	move_camera(LIFE[SETTINGS['following']]['pos'])
	
	if LOS_BUFFER[0] == []:
		LOS_BUFFER[0] = maps._render_los(WORLD_INFO['map'],
		                                 LIFE[SETTINGS['following']]['pos'],
		                                 alife.sight.get_vision(LIFE[SETTINGS['following']]),
		                                 cython=True)	
	
	if CYTHON_ENABLED:
		render_map.render_map(WORLD_INFO['map'])
	else:
		maps.render_map(WORLD_INFO['map'])
	
	items.draw_items()
	bullets.draw_bullets()
	life.draw_life()
	maps.render_lights(WORLD_INFO['map'])
	
	if LIFE[SETTINGS['controlling']]['encounters']:
		LOS_BUFFER[0] = maps._render_los(WORLD_INFO['map'],
		                                 LIFE[SETTINGS['controlling']]['pos'],
		                                 alife.sight.get_vision(LIFE[SETTINGS['controlling']]),
		                                 cython=CYTHON_ENABLED)
	
	if not SETTINGS['controlling'] == SETTINGS['following']:
		LOS_BUFFER[0] = maps._render_los(WORLD_INFO['map'],
		                                 LIFE[SETTINGS['controlling']]['pos'],
		                                 alife.sight.get_vision(LIFE[SETTINGS['controlling']]),
		                                 cython=True)
	
	if LIFE[SETTINGS['controlling']]['dead']:
		gfx.fade_to_white(FADE_TO_WHITE[0])
		_col = 255-int(round(FADE_TO_WHITE[0]))*2
		
		if _col<0:
			_col = 0
		
		_string = 'You die.'
		
		gfx.blit_string(MAP_WINDOW_SIZE[0]/2-(len(_string)/2),
			MAP_WINDOW_SIZE[1]/2,
			_string,
			console=MAP_WINDOW,
			fore_color=tcod.Color(255,_col,_col),
			back_color=tcod.Color(255-_col,255-_col,255-_col),
			flicker=0)
		FADE_TO_WHITE[0] += 0.9
	
	life.draw_life_info()
	menus.align_menus()
	menus.draw_menus()
	logic.draw_encounter()
	dialog.draw_dialog()
	gfx.draw_message_box()
	gfx.draw_status_line()
	gfx.draw_console()
	gfx.start_of_frame()
	gfx.end_of_frame_reactor3()
	gfx.end_of_frame()
	
	#print tcod.sys_get_fps()

def tick():
	while SETTINGS['running']==2:
		try:
			main()
		except Exception, e:
			traceback.print_exc(file=sys.stdout)
			SETTINGS['running'] = False
			
			if 'debug' in WORLD_INFO:
				WORLD_INFO['debug'].quit()

if __name__ == '__main__':
	#TODO: Replace with "module_sanity_check"
	#Optional Cython-compiled modules
	try:
		import render_map
		import render_los
		
		if render_map.VERSION == MAP_RENDER_VERSION:
			CYTHON_ENABLED = True
		else:
			logging.error('[Cython] render_map is out of date!')
			logging.error('[Cython] Run \'python compile_cython_modules.py build_ext --inplace\'')
			sys.exit(1)
		
	except ImportError, e:
		CYTHON_ENABLED = False
		logging.warning('[Cython] ImportError with module: %s' % e)
		logging.warning('[Cython] Certain functions can run faster if compiled with Cython.')
		logging.warning('[Cython] Run \'python compile_cython_modules.py build_ext --inplace\'')
	
	gfx.log(WINDOW_TITLE)
	
	tiles.create_all_tiles()
	language.load_strings()
	
	gfx.init_libtcod()
	#smp.init()

	SETTINGS['draw z-levels below'] = True
	SETTINGS['draw z-levels above'] = True
	
	life.initiate_life('human')
	life.initiate_life('dog')
	
	items.initiate_item('white_shirt')
	items.initiate_item('white_cloth')
	items.initiate_item('sneakers')
	items.initiate_item('leather_backpack')
	items.initiate_item('blue_jeans')
	items.initiate_item('glock')
	items.initiate_item('22_rifle')
	items.initiate_item('9x19mm_mag')
	items.initiate_item('9x19mm_round')
	items.initiate_item('radio')
	items.initiate_item('can_of_corn')
	items.initiate_item('soda')
	items.initiate_item('electric_lantern')
	items.initiate_item('burner')
	items.initiate_item('22_rifle')
	items.initiate_item('22_lr_mag')
	items.initiate_item('22_lr_cartridge')
	
	SETTINGS['running'] = 2
	
	if SETTINGS['running'] == 2:
		for world in profiles.get_worlds():
			worldgen.load_world(world)
			break
	
	if not 'start_age' in WORLD_INFO:
		SETTINGS['running'] = 1
	
	while SETTINGS['running'] in [-1, 1]:
		if SETTINGS['running'] == -1:
			mainmenu.draw_intro()
		
		if not MENUS:
			mainmenu.switch_to_main_menu()
		
		get_input()
		handle_input()
		mainmenu.draw_main_menu()
	
	gfx.refresh_window()
	
	if not 'start_age' in WORLD_INFO:
		worldgen.generate_world(WORLD_INFO['map'],
			life_density='Heavy',
			wildlife_density='Sparse',
			simulate_ticks=100,
			save=True,
			thread=False)
	
	if '--debug' in sys.argv:
		_debug_host = network.DebugHost()
		_debug_host.start()
		WORLD_INFO['debug'] = _debug_host
	
	if '--profile' in sys.argv:
		logging.info('Profiling. Exit when completed.')
		cProfile.run('tick()','profile.dat')
	else:
		tick()
	
	if 'debug' in WORLD_INFO:
		WORLD_INFO['debug'].quit()
	
	#effects.create_light((14, 72, 2), (255, 0, 255), 2, 0.1)
	#effects.create_light((12, 76, 2), (255, 0, 255), 7, 0.1)
	#effects.create_light((52, 61, 2), (255, 0, 255), 1, 0.1)
	#effects.create_light((73, 76, 2), (255, 0, 255), 5, 0.1)
	#effects.create_light((73, 76, 2), (255, 0, 255), 5, 0.1)