# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.
# NOTICE: This file is subject to the license agreement defined in file 'LICENSE', which is part of
# this source code package.

import time, random
from src.kesslergame import Scenario, KesslerGame, GraphicsType
from main_controller_akila import AkilaController
from graphics_both import GraphicsBoth
from xfc_2023_replica_scenarios import *
from test_controller import TestController

def generate_asteroids(num_asteroids, position_range_x, position_range_y, speed_range, angle_range, size_range):
    asteroids = []
    for _ in range(num_asteroids):
        position = (random.uniform(*position_range_x), random.uniform(*position_range_y))
        speed = random.triangular(*speed_range) #random.randint(*speed_range) 
        angle = random.uniform(*angle_range)
        size = random.randint(*size_range)
        asteroids.append({'position': position, 'speed': speed, 'angle': angle, 'size': size})
    return asteroids
width, height = (1600, 950)

'''
randseed = random.randint(1, 100000000)
random.seed(48925489)
print("Random seed: ", randseed)
'''



asteroids_random = generate_asteroids(
                                num_asteroids=random.randint(20,30),
                                position_range_x=(0, width),
                                position_range_y=(0, height),
                                speed_range=(0,300, 0),
                                angle_range=(-1, 361),
                                size_range=(1, 4)
                            )*random.choice([1])

# Define game scenario
my_test_scenario = Scenario(name='Test Scenario',
                            #num_asteroids=1,
                            asteroid_states=asteroids_random,
                            ship_states=[
                                {'position': (400, 400), 'angle': 90, 'lives': 3, 'team': 1, "mines_remaining": 3},
                                # {'position': (400, 600), 'angle': 90, 'lives': 3, 'team': 2, "mines_remaining": 3},
                            ],
                            map_size=(width, height),
                            time_limit=60,
                            ammo_limit_multiplier=0,
                            stop_if_no_ammo=False)
# Define Game Settings
game_settings = {'perf_tracker': True,
                 'graphics_type': GraphicsType.Tkinter,
                 'realtime_multiplier': 0,
                 'graphics_obj': None,
                 'frequency': 30}

game = KesslerGame(settings=game_settings)  # Use this to visualize the game scenario
# game = TrainerEnvironment(settings=game_settings)  # Use this for max-speed, no-graphics simulation

# Evaluate the game
pre = time.perf_counter()
score, perf_data = game.run(scenario=my_test_scenario, controllers=[AkilaController(), TestController()])

# Print out some general info about the result
print('Scenario eval time: '+str(time.perf_counter()-pre))
print(score.stop_reason)
print('Asteroids hit: ' + str([team.asteroids_hit for team in score.teams]))
print('Deaths: ' + str([team.deaths for team in score.teams]))
print('Accuracy: ' + str([team.accuracy for team in score.teams]))
print('Mean eval time: ' + str([team.mean_eval_time for team in score.teams]))
