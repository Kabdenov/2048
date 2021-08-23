from scene import *
import sound
import random
import math
import enum
import numpy as np
import threading
from game_menu import MenuScene
A = Action
	
class Tile(ShapeNode):
	value = None
	label = None
	def __init__(self, value, size, **kwargs):
		self.value = value
		
		# tile body
		rect = ui.Path.rounded_rect(0,0,size,size,10)
		super().__init__(rect, **kwargs)
	
		# tile label
		font = ('Futura', size/3)
		self.label = LabelNode(str(value), font)
		self.label.color='black'
		self.label.anchor_point = (0.5, 0.5)
		self.label.position = (0,0)
		self.add_child(self.label)
		
	# checks if one tile has value equal
	# to the value of another tile
	def eq(self, tile):
		return self.value == tile.value
		
class TileFactory:
	def __init__(self, brd_size, size, tile_mrgn):
		self.brd_size = brd_size
		self.tile_size = size - tile_mrgn*2
		self.tile_mrgn = tile_mrgn
		self.colors = ['#F9C74F', '#F9844A', '#F8961E', '#F3722C', '#90BE6D', '#43AA8B', '#4D908E', '#577590', '#277DA1', '#F94144']
	
	# returns Tile object 
	def get_tile(self, value, r, c):
		color = self.get_color(value)
		tile = Tile(value, self.tile_size)
		tile.anchor_point = (0.5, 0.5)
		tile.fill_color = color
		tile.position = self.get_coords(r,c)
		return tile
		
	def get_color(self, value):
		color_idx = int(math.log2(value)-1)
		return self.colors[color_idx % len(self.colors)]
	
	# return x, y coordinates by row and col index	
	def get_coords(self, r, c):
		b_size = self.brd_size
		c_size = self.tile_size + self.tile_mrgn*2
		x = -b_size/2 + c_size/2 + c * c_size
		y = b_size/2 - c_size/2 - r * c_size
		return (x,y)
		
	def update_tile(self, tile):
		tile.fill_color = self.get_color(tile.value)
		tile.label.text = str(tile.value)
		return tile
		
	
class Board(Node):
	scene_ref = None
	score = 0
	target_tile_value = 2048
	
	def __init__(self, scene_ref, num_tiles, tf):
		self.scene_ref = scene_ref
		self.tf = tf
		
		n = num_tiles
		# build 2D array of equal size
		tile_arr = [None for i in range(n*n)]
		np_tile_arr = np.array(tile_arr)
		self.grid = np_tile_arr.reshape(n, n)
		
		# add 2 tiles to start game with
		for num in range (2):
			self.add_new_tile([2])	
	
	# adds a new tile to a random empty cell	
	# values are chosen randomly
	# value 2 has greater probability
	def add_new_tile(self, values = None):
		if values is None:
			values = [2]*10+[4]*2+[8]
		empty_cells = []
		for r in range(len(self.grid)):
			for c in range(len(self.grid[r])):
				cell = self.grid[r][c]
				if cell is None:
					empty_cells.append((r,c))
		
		# if no empty cells left, cant add any tile
		if len(empty_cells) == 0:
			return 0
		
		(r,c) = random.choice(empty_cells)
		rand_value = random.choice(values)
		
		tile = self.tf.get_tile(rand_value, r, c)
		self.grid[r][c] = (tile, None)
		self.add_child(tile)
		self.scene_ref.flash_tile(tile, 0.1)
		
		return rand_value
	
	# function to find new position for each tile
	def make_move(self, d, is_test = False):
		# 0,1,2,3 for left,right,up,down
		grid = self.grid
		
		# if up or down, we need to transpose the grid 
		if d > 1:
			grid = grid.T
			
		# if right or down, we need to flip the grid
		if d%2 == 1:
			grid = np.fliplr(grid)
		
		# for each row, we take non-empty cells 
		# and check if adjucent tiles can be merged
		has_moves = False
		was_moved = False
		target_reached = False
		for r in range(grid.shape[0]):
			row = grid[r]
			tiles = [x for x in row if x != None]
			for c in range(len(tiles)-1):
				if tiles[c] is None:
					continue
				first, _ = tiles[c]
				second, _ = tiles[c+1]				
				
				# we put tiles to be merged in a tuple
				if first.eq(second):
					tiles[c] = (first, second)
					tiles[c+1] = None
			
			# remove empty cells between tiles						
			tiles = [x for x in tiles if x != None]
			# extend row to original size
			tiles = tiles + [None] * (len(row) - len(tiles))
			
			# if row after move is different from original
			if was_moved is False:
				for i in range(len(tiles)):
					if tiles[i] != row[i]:
						was_moved = True
						break
				
			has_moves = has_moves or (None in tiles)
			if not is_test:
				row[:] = tiles
				
		if is_test:
			return has_moves
			
		# we iterate through resulting rows 
		# and start animation tasks
		self.score = 0
		for r in range(len(self.grid)):
			for c in range(len(self.grid)):
				if self.grid[r][c] is not None:
					first, second = self.grid[r][c]
					# two tiles in a same cell means that 
					# they need to be merged
					if second is not None:
						first.value *= 2
						self.grid[r][c] = (first, None)
						self.scene_ref.merge_tiles(first, second, r, c)
					else:
						self.scene_ref.move_tile(first, r, c)
					
					self.score += first.value
					if first.value == self.target_tile_value:
						target_reached = True
		
		# new tile is added after each move
		if was_moved:
			sound.play_effect('ui:switch24', 1)
			self.score += self.add_new_tile()
		else:
			sound.play_effect('8ve:8ve-beep-timber', 1)
			
		self.scene_ref.update_score(self.score)
		
		if target_reached and not self.scene_ref.you_won_msg_shown:
			self.scene_ref.show_you_won_msg(self.target_tile_value)
	
		elif not self.has_moves():
			self.scene_ref.show_game_over_menu()
		
		return has_moves
		
	# check if any moves are left
	def has_moves(self):
		if self.make_move(0, True):
			return True
		if self.make_move(1, True):
			return True
		if self.make_move(2, True):
			return True
		return self.make_move(3, True)
			
class MyScene (Scene):
	tf = None
	you_won_msg_shown = False
	paused = False
	pause_button = None
	score_label = None
	hs_label = None
	container = None
	
	# clears the scene from child elements 
	def clear(self):
		if self.pause_button:
			self.pause_button.remove_from_parent()
			
		if self.score_label:
			self.score_label.remove_from_parent()
			
		if self.hs_label:
			self.hs_label.remove_from_parent()
			
		if self.container:
			self.container.remove_from_parent()
	
	def new_game(self, num_tiles = 4):
		self.clear()
		board_margin = 32
		tile_margin = 4
		board_size = self.size.w - board_margin * 2
		
		# draw a grid container
		self.container = Node()
		self.container.anchor_point = (0.5, 0.5)
		screen_center = (self.size.w/2, self.size.h/2)
		self.container.position = screen_center
		self.add_child(self.container)

		# draw grid cells
		size = board_size / num_tiles
		y = board_size/2 - size/2
		for i in range(num_tiles):
			x = -board_size/2 + size/2
			for j in range(num_tiles):
				rect = ui.Path.rounded_rect(0,0,size,size,15)
				cell = ShapeNode(rect)
				cell.line_width = tile_margin * 2
				cell.stroke_color = self.background_color
				cell.fill_color = '#B1EDE8'
				cell.anchor_point = (0.5, 0.5)
				cell.position = (x, y)
				self.container.add_child(cell)
				x = x + size
			y = y - size
			
		# add score text
		score_font = ('Futura', 40)
		self.score_label = LabelNode('0', score_font)
		self.score_label.color = 'black'
		self.score_label.anchor_point = (0.5, 0.5)
		pos = (self.size.w/2, self.size.h-70)
		self.score_label.position = pos
		self.score_label.z_position = 1
		self.add_child(self.score_label)
		
		# add highscore text
		hs_font = ('Futura', 14)
		hs_text = 'HIGH: ' + str(self.highscore)
		self.hs_label = LabelNode(hs_text, hs_font)
		self.hs_label.color = 'black'
		self.hs_label.anchor_point = (0, 0.5)
		hs_label_width = self.hs_label.size.w
		x = self.size.w - board_margin - hs_label_width
		y = self.size.h - 70
		self.hs_label.position = (x, y)
		self.hs_label.z_position = 1
		self.add_child(self.hs_label)
		
		# add pause button
		self.pause_button = SpriteNode('iob:pause_32')
		self.pause_button.anchor_point = (0,0)
		x = board_margin - 8
		y = self.size.h - 70 - 16
		self.pause_button.position=(x, y)
		self.add_child(self.pause_button)
		
		# create board object to hold tiles
		self.tf = TileFactory(board_size,size,tile_margin)
		self.board = Board(self, num_tiles, self.tf)
		self.container.add_child(self.board)
	
	def setup(self):
		self.load_highscore()
		self.background_color = '#FFFFFF'	
		self.add_child(Node())
		self.show_start_menu()
		pass
	
	def did_change_size(self):
		pass
	
	def update(self):
		pass
		
	def merge_tiles(self, first, second, r, c):
		if not first or not second:
			return
		next_x, next_y = self.tf.get_coords(r, c)
		move = A.move_to(next_x, next_y, 0.05)
		flash = A.call(self.flash_tile, 0.01)
		remove = A.call(self.remove_tile, 0.05)
		
		seq1 = A.sequence(move, flash)
		seq2 = A.sequence(move, remove)
		
		first.run_action(seq1)
		second.run_action(seq2)
		pass
		
	def remove_tile(self, tile, duration):
		if not tile:
			return
		tile.remove_from_parent()
		
	def flash_tile(self, tile, duration):
		if not tile:
			return
		larger = A.scale_by(0.1, 0.1)
		update = A.call(self.update_tile, 0.01)
		smaller = A.scale_by(-0.1, 0.1)
		seq = A.sequence(larger, smaller)
		group = A.group(seq, update)
		tile.run_action(group)
		pass
		
	def update_tile(self, tile, duration):
		if not tile:
			return
		self.tf.update_tile(tile)
		pass
		
	def move_tile(self, tile, r, c):
		if not tile:
			return
		next_x, next_y = self.tf.get_coords(r,c)
		action = A.move_to(next_x, next_y, 0.1)
		tile.run_action(action)
		pass
	
	old_touch_loc = (0,0)
	def touch_began(self, touch):
		x, y = touch.location
		
		# handle pause button press
		if x <= 100 and y >= self.size.h - 100:
			self.paused = True
			self.show_pause_menu()
			return
			
		self.old_touch_loc = (x,y)
		pass
	
	def touch_moved(self, touch):
		pass
	
	def touch_ended(self, touch):
		# ignore touch events when paused
		if self.paused:
			return
			
		old_x, old_y = self.old_touch_loc
		new_x, new_y = touch.location
		dx =  new_x - old_x
		dy = new_y - old_y
		
		direction = 0 #left
		if abs(dx) > abs(dy) and dx > 0:
			direction = 1 # right
		elif abs(dx) < abs(dy):
			if dy > 0:
				direction = 2 # up
			else:
				direction = 3 #down
		
		self.board.make_move(direction)
		pass
		
	def update_score(self, score):
		# update current score label
		self.score_label.text = str(score)
		
		if score > self.highscore:
			self.highscore = score
			
			# change color and animate score label
			self.score_label.color = '#EF476F'
			larger = A.scale_by(0.1, 0.1)
			smaller = A.scale_by(-0.1, 0.1)
			seq = A.sequence(larger, smaller)
			self.score_label.run_action(seq)
			
			# update high score label
			self.hs_label.text = 'HIGH: ' + str(self.highscore)
			
			# reposition high score label to keep aligned 
			# with the board when its value increases
			x = self.size.w - self.hs_label.size.w - 32
			y = self.size.h - 70
			self.hs_label.position = (x, y)
			
			self.save_highscore()
	
	def load_highscore(self):
		#with open('.2048_highscore', 'w') as f:
		#	f.write(str(0))
		try:
			with open('.2048_highscore', 'r') as f:
				self.highscore = int(f.read())
		except:
			self.highscore = 0
	
	def save_highscore(self):
		with open('.2048_highscore', 'w') as f:
			f.write(str(self.highscore))
		
	def show_start_menu(self):
		title = '2048'
		subtitle = 'Highscore: %i' % self.highscore
		buttons = ['Play 4x4', 'Play 5x5', 'Play 6x6']
		self.menu = MenuScene(title, subtitle, buttons)
		self.present_modal_scene(self.menu)
		
	def show_game_over_menu(self):
		title = 'Game Over'
		subtitle = 'Your score: %i' % self.board.score
		buttons = ['Dismiss']
		self.menu = MenuScene(title, subtitle, buttons)
		self.present_modal_scene(self.menu)
		
	def show_pause_menu(self):
		title = 'Paused'
		subtitle = ''
		buttons = ['Continue', 'Play 4x4', 'Play 5x5', 'Play 6x6']
		self.menu = MenuScene(title, subtitle, buttons)
		self.present_modal_scene(self.menu)
		
	def show_you_won_msg(self, target_tile_value):
		self.you_won_msg_shown = True
		title = 'You Won!'
		subtitle = 'You reached %i!' % target_tile_value
		buttons = ['Continue playing']
		self.menu = MenuScene(title, subtitle, buttons)
		self.present_modal_scene(self.menu)
		
	def menu_button_selected(self, title):
		if title.endswith('4'):
			self.new_game(4)	
		elif title.endswith('5'):
			self.new_game(5)
		elif title.endswith('6'):
			self.new_game(6)	
		self.dismiss_modal_scene()
		self.menu = None
		self.paused = False

if __name__ == '__main__':
	run(MyScene(), PORTRAIT, show_fps=False)
