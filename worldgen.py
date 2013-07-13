from globals import *

import libtcodpy as tcod

import historygen
import threading
import profiles
import logging
import effects
import logic
import items
import tiles
import alife
import life
import maps

import random
import time
import json

BASE_ITEMS = ['sneakers', 'blue jeans', 'white t-shirt', 'leather backpack', 'radio', 'glock', '9x19mm magazine', 'electric lantern', 'soda']
RECRUIT_ITEMS = [ '.22 rifle', 'corn', 'soda']
for i in range(10):
	RECRUIT_ITEMS.append('9x19mm round')

class Runner(threading.Thread):
	def __init__(self, function, source_map, amount):
		self.function = function
		self.source_map = source_map
		self.amount = amount
		self.running = True
		
		threading.Thread.__init__(self)
	
	def run(self):
		try:
			self.function(self.source_map, amount=self.amount)
		except Exception as e:
			logging.error('Crash: %s' % e)
			SETTINGS['running'] = False
			raise
		
		self.running = False


def draw_world_stats():
	tcod.console_print(0, 0, 0, 'World Generation')
	tcod.console_print(0, 0, 2, 'Simulating world: %s (%.2f t/s)' % (WORLD_INFO['ticks'], WORLD_INFO['ticks']/(time.time()-WORLD_INFO['inittime'])))
	tcod.console_print(0, 0, 3, 'Queued ALife actions: %s' % sum([len(alife['actions']) for alife in [LIFE[i] for i in LIFE]]))
	tcod.console_print(0, 0, 4, 'Total ALife memories: %s' % sum([len(alife['memory']) for alife in [LIFE[i] for i in LIFE]]))
	tcod.console_print(0, 0, 5, '%s %s' % (TICKER[int(WORLD_INFO['ticks'] % len(TICKER))], '=' * int((WORLD_INFO['ticks']/float(WORLD_INFO['start_age']))*10)))
	tcod.console_print(0, 0, 6, 'Time elapsed: %.2f' % (time.time()-WORLD_INFO['inittime']))
	tcod.console_flush()

def generate_world(source_map, life=1, simulate_ticks=1000, save=True, thread=True):
	WORLD_INFO['inittime'] = time.time()
	WORLD_INFO['start_age'] = simulate_ticks
	
	tcod.console_print(0, 0, 0, 'Updating chunk map...')
	tcod.console_flush()
	maps.update_chunk_map(source_map)
	
	tcod.console_print(0, 0, 0, 'Smoothing chunk map...')
	tcod.console_flush()
	maps.smooth_chunk_map()
	
	tcod.console_print(0, 0, 0, 'Generating reference map...')
	tcod.console_flush()
	maps.generate_reference_maps()
	
	tcod.console_print(0, 0, 0, 'Creating position maps...')
	tcod.console_flush()
	maps.create_position_maps()
	
	generate_life(source_map, amount=life)
	#generate_wildlife(source_map)
	randomize_item_spawns()
	
	if thread:
		tcod.console_rect(0,0,0,WINDOW_SIZE[0],WINDOW_SIZE[1],True,flag=tcod.BKGND_DEFAULT)
		_r = Runner(simulate_life, source_map, amount=simulate_ticks)
		_r.start()

		while _r.running:
			draw_world_stats()
			
			if not SETTINGS['running']:
				return False
	else:
		simulate_life(source_map, amount=simulate_ticks)
	
	create_player(source_map)
	WORLD_INFO['id'] = 0
	
	if save:
		WORLD_INFO['id'] = profiles.create_world()
		save_world()
	
	logging.info('World generation complete (took %.2fs)' % (time.time()-WORLD_INFO['inittime']))

def load_world(world):
	WORLD_INFO['id'] = world
	maps.load_map('map', base_dir=profiles.get_world(world))
	
	with open(os.path.join(profiles.get_world(WORLD_INFO['id']), 'life.dat'), 'r') as e:
		LIFE.update(json.loads(e.readline()))
	
	logging.info('World loaded.')

def save_world():
	logging.debug('Offloading world...')
	maps.save_map('map', WORLD_INFO['map'], base_dir=profiles.get_world(WORLD_INFO['id']))
	logging.debug('Saving life...')
	_life = life.save_all_life()
	
	with open(os.path.join(profiles.get_world(WORLD_INFO['id']), 'life.dat'), 'w') as e:
		e.write(_life)
	
	logging.info('World saved.')

def randomize_item_spawns():
	for building in REFERENCE_MAP['buildings']:
		_chunk_key = random.choice(building)
		_chunk = maps.get_chunk(_chunk_key)
		
		if not _chunk['ground']:
			continue
		
		_rand_pos = random.choice(_chunk['ground'])
		items.create_item(random.choice(RECRUIT_ITEMS), position=[_rand_pos[0], _rand_pos[1], 2])

def generate_wildlife(source_map, amount='heavy'):
	for i in range(1, 3):
		_p = life.create_life('dog',
			name=['Wild', 'Dog%s' % i],
			map=source_map,
			position=[55+(i*5),81,2])
		
		if random.randint(0, 3)>=2:
			_c = life.create_life('dog',
				name=['(Young) Wild', 'Dog%s' % i],
				map=source_map,
				position=[55+(i*5),82,2])
			_c['icon'] = 'd'
			
			alife.brain.meet_alife(_p, _c)
			alife.brain.meet_alife(_c, _p)
			
			alife.brain.flag_alife(_p, _c, 'son')
			alife.brain.flag_alife(_c, _p, 'father')
			
			#alife.brain.add_impression(_c, _p['id'], 'follow', {'influence': 60})

def generate_life(source_map, amount=1):
	for i in range(amount):
		if i % 2:
			_spawn = (40, 40)
		else:
			_spawn = (30, 70)
		
		alife = life.create_life('human',map=source_map,position=[_spawn[0]+(i*2),_spawn[1]+(i*3),2])
		alife['stats'].update(historygen.create_background(life))
		
		#if random.randint(0,1):
		#	alife['hunger'] = 1000
		#	alife['thirst'] = 1000
		
		for item in BASE_ITEMS:
			life.add_item_to_inventory(alife, items.create_item(item))
		
		for item in RECRUIT_ITEMS:
			if random.randint(0, 1):
				continue
			
			life.add_item_to_inventory(alife, items.create_item(item))
		
		#_wep = life.get_all_unequipped_items(alife, matches=[{'type': 'gun'}])
		#life.equip_item(alife, _wep[0])

def simulate_life(source_map, amount=1000):
	for i in range(amount):
		logic.tick_all_objects(source_map)

def create_player(source_map):
	PLAYER = life.create_life('human',
		name=['Tester','Toaster'],
		map=source_map,
		position=[50,80,2])
	PLAYER['stats'].update(historygen.create_background(life))
	PLAYER['player'] = True
	
	for item in BASE_ITEMS:
		life.add_item_to_inventory(PLAYER, items.create_item(item))
	
	for item in RECRUIT_ITEMS:
		life.add_item_to_inventory(PLAYER, items.create_item(item))

	SETTINGS['controlling'] = PLAYER
	SETTINGS['following'] = PLAYER
	
	_i = items.create_item('sneakers', position=PLAYER['pos'][:])
	items.move(_i, 180, 3)
	
	for x in range(-10, 11):
		for y in range(-10, 11):
			if random.randint(0, 10):
				continue
			effects.create_fire((PLAYER['pos'][0]+x, PLAYER['pos'][1]+y, PLAYER['pos'][2]), intensity=8)
