from globals import WORLD_INFO

import life as lfe

import weapons
import numbers
import combat
import speech
import sight
import brain
import jobs

import random

def score_search(life,target,pos):
	return -numbers.distance(life['pos'],pos)

def score_shootcover(life,target,pos):
	return numbers.distance(life['pos'],pos)

def score_escape(life,target,pos):
	_target_distance_to_pos = numbers.distance(target['pos'], pos)
	_score = numbers.distance(life['pos'],pos)
	_score += 30-_target_distance_to_pos
	
	if not sight.can_see_position(target, pos, distance=False):
		_score -= _target_distance_to_pos
	
	if not sight.can_see_position(life, pos, distance=False):
		_score += _target_distance_to_pos/2
	
	return _score

def score_hide(life,target,pos):
	_score = numbers.distance(life['pos'],pos)
	#_score += (30-numbers.distance(target['pos'],pos))
	
	return _score

def position_for_combat(life,target,position,source_map):
	_cover = {'pos': None,'score': 9000}
	
	#TODO: Eventually this should be written into the pathfinding logic
	if sight.can_see_position(life,target['life']['pos']) and numbers.distance(life['pos'], target['life']['pos'])<=target['life']['engage_distance']:
		lfe.clear_actions(life)
		return True
	
	#What can the target see?
	#TODO: Unchecked Cython flag
	_attack_from = sight.generate_los(life,target,position,source_map,score_shootcover,invert=True)
	
	if _attack_from:
		lfe.clear_actions(life)
		lfe.add_action(life,{'action': 'move','to': _attack_from['pos']},200)
		return False
	
	return True

def travel_to_target(life, target, pos):
	if sight.can_see_position(life, pos):
		return False
	
	lfe.clear_actions(life)
	lfe.add_action(life,{'action': 'move','to': (pos[0],pos[1])},200)
	return True
	#if not tuple(life['pos']) == tuple(pos):
	#	lfe.clear_actions(life)
	#	lfe.add_action(life,{'action': 'move','to': (pos[0],pos[1])},200)

def search_for_target(life, target, source_map):
	if sight.can_see_position(life, target['last_seen_at']):
		print 'We can see where we last saw him.'
	
	if _cover:
		print 'FIND TARGET',_cover['pos']
		lfe.clear_actions(life)
		lfe.add_action(life,{'action': 'move','to': _cover['pos']},200)
		return False
	
	return True

def explore(life,source_map):
	#This is a bit different than the logic used for the other pathfinding functions
	pass

def escape(life, target, source_map):
	#With this function we're trying to get away from the target.
	#You'll see in `score_escape` that we're not trying to find full cover, but instead
	#just finding a way to get behind *something*.
	#
	#TODO: Remove the need for {'life': ...}
	_escape = sight.generate_los(life, {'life': target}, target['pos'], source_map, score_escape)
	print 'escaping', _escape
	
	if _escape:
		lfe.clear_actions(life)
		lfe.add_action(life,{'action': 'move','to': _escape['pos']},200)
		return False
	else:
		if brain.get_flag(life, 'scared') and not speech.has_considered(life, target, 'surrendered_to'):
			speech.communicate(life, 'surrender', target=target)
			brain.flag(life, 'surrendered')
			#print 'surrender'
	
	if lfe.path_dest(life):
		return True
	
	return True

def hide(life, target_id):
	_target = brain.knows_alife_by_id(life, target_id)
	_cover = sight.generate_los(life, _target, _target['last_seen_at'], WORLD_INFO['map'], score_hide)
	
	if _cover:
		lfe.clear_actions(life)
		lfe.add_action(life,{'action': 'move','to': _cover['pos']},200)		
		return False
	
	print 'YAH'
	
	return True

def handle_hide(life,target,source_map):
	_weapon = combat.get_best_weapon(life)	
	_feed = None
	
	if _weapon:
		_feed = weapons.get_feed(_weapon['weapon'])		
	
	#TODO: Can we merge this into get_best_weapon()?
	_has_loaded_ammo = False
	if _feed:
		if _feed['rounds']:
			_has_loaded_ammo = True
	
	if _weapon and _weapon['weapon'] and (_weapon['rounds'] or _has_loaded_ammo):
		return escape(life,target,source_map)
	elif not _weapon and sight.find_known_items(life,matches={'type': 'weapon'},visible=True):
		return collect_nearby_wanted_items(life)
	else:
		return escape(life,target,source_map)

def collect_nearby_wanted_items(life, visible=True, matches={'type': 'gun'}):
	_highest = {'item': None,'score': -100000}
	_nearby = sight.find_known_items(life, matches=matches, visible=visible)
	
	for item in _nearby:
		_score = item['score']
		_score -= numbers.distance(life['pos'], item['item']['pos'])
		
		if not _highest['item'] or _score > _highest['score']:
			_highest['score'] = _score
			_highest['item'] = item['item']
	
	if not _highest['item']:
		return True
	
	_empty_hand = lfe.get_open_hands(life)
	
	if not _empty_hand:
		print 'No open hands, managing....'
		
		return False
	
	if life['pos'] == _highest['item']['pos']:
		lfe.clear_actions(life)
		
		for action in lfe.find_action(life, matches=[{'action': 'pickupholditem'}]):
			#print 'I was picking up something else...',_highest['item']['name']
			return False
		
		lfe.add_action(life,{'action': 'pickupholditem',
			'item': _highest['item'],
			'hand': random.choice(_empty_hand)},
			200,
			delay=lfe.get_item_access_time(life, _highest['item']))
		lfe.lock_item(life, _highest['item'])
	else:
		lfe.clear_actions(life)
		lfe.add_action(life,{'action': 'move','to': _highest['item']['pos'][:2]},200)
	
	return False

def _find_alife(life, target):
	#Almost a 100% chance we know who this person is...
	_target = brain.knows_alife_by_id(life, target)
	
	#We'll try last_seen_at first
	#TODO: In the future we should consider how long it's been since we've seen them
	lfe.clear_actions(life)
	lfe.add_action(life, {'action': 'move','to': _target['last_seen_at'][:2]}, 900)
	
	if sight.can_see_position(life, _target['life']['pos']):
		return True
	
	return False

def find_alife(life):
	if _find_alife(life, jobs.get_job_detail(life['job'], 'target')):
		lfe.stop(life)
		return True
	
	return False

#TODO: Put this in a new file
def find_alife_and_say(life):
	_target = brain.knows_alife_by_id(life, jobs.get_job_detail(life['job'], 'target'))
	
	if _find_alife(life, _target['life']['id']):
		_say = jobs.get_job_detail(life['job'], 'say')
		speech.communicate(life, _say['gist'], matches=[{'id': _target['life']['id']}], camp=_say['camp'], founder=_say['founder'])
		lfe.memory(life,
			'told about founder',
			camp=_say['camp'],
			target=_target['life']['id'])
		return True
	
	return False
