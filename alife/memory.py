from globals import *

import life as lfe

import judgement
import rawparse
import action
import brain

import logging

def process_questions(life):
	for question in lfe.get_questions(life):
		_answered = False
		#_matches = {requirement: '*' for requirement in QUESTIONS_ANSWERS[question['text']]}
		
		for match in question['answer_match']:
			for memory in lfe.get_memory(life, matches=match):
				
				if lfe.get_memory(life, match):
					question['answered'].append(memory['id'])
					_answered = True
		
		if _answered:
			if len(question['answered']) == 1:
				lfe.memory(life, 'answered question', question=question['text'])
				logging.debug('%s answered question: %s' % (' '.join(life['name']), memory['text']))
			else:
				lfe.memory(life, 'added detail to answered question', question=question['text'])
				logging.debug('%s added more detail to question: %s' % (' '.join(life['name']), memory['text']))
			
			if question['answer_all']:
				for _question in lfe.get_questions(life):
					if not question['text'] == _question['text']:
						continue
					
					_question['answered'].extend(question['answered'])

def rescore_history(life):
	for memory in life['memory']:
		if (brain.get_flag(life, 'hungry') or brain.get_flag(life, 'thirsty')) and memory['text'] == 'consume_item':
			if not 'trust' in memory:
				memory['trust'] = -2
				memory['danger'] = 3
				print 'HATE!'

def detect_lies(life):
	#for memory in life['memories']:
	for question in lfe.get_questions(life, no_filter=True):		
		for answer in [lfe.get_memory_via_id(life, a) for a in question['answered']]:
			pass
			#print answer.keys()

def reflect(life):
	while life['unchecked_memories']:
		_memory = lfe.get_memory_via_id(life, life['unchecked_memories'].pop())
		
		if not rawparse.raw_section_has_identifier(life, 'memory', _memory['text']):
			continue
		
		_return_value = lfe.execute_raw(life, 'memory', _memory['text'])
		
		if _return_value == 'investigate_chunk':
			judgement.judge_chunk(life, _memory['chunk_key'], investigate=True)

def process(life):
	process_questions(life)
	detect_lies(life)
	rescore_history(life)
	reflect(life)