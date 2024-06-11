# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.
# NOTICE: This file is subject to the license agreement defined in file 'LICENSE', which is part of
# this source code package.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
import math


class AkilaController(KesslerController):
    def __init__(self):
        """
        Any variables or initialization desired for the controller can be set up here
        """
        self.delay = 0
        self.asteroids_shot = []
        self.rest_counter = 0
        
        ...
        #add a frame counter to keep track of the time

    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool, bool]:
        #consider where the asteroid will be in like 2 or 3 seconds in the future and turn towards it(consideration)
        #priority system /use fuzzy logic for this part
        #for invulnerability, check if you are going to hit or not. if no collision, start firing
        """
        Method processed each time step by this controller to determine what control actions to take

        Arguments:
            ship_state (dict): contains state information for your own ship
            game_state (dict): contains state information for all objects in the game

        Returns:
            float: thrust control value
            float: turn-rate control value
            bool: fire control value. Shoots if true
            bool: mine deployment control value. Lays mine if true
        """

        fire = False
        closest_ast = None
        a_dist = math.inf
        asteroids_already_shot = False
        

        #picking the closest asteroid
        for asteroid in game_state['asteroids']:
            asteroids_already_shot = False
            for shot_ast in self.asteroids_shot:
                    if shot_ast["velocity"] == asteroid["velocity"] and shot_ast["size"] == asteroid["size"] :
                        asteroids_already_shot = True
                        break
            if asteroids_already_shot == True:
                continue
            
            distance = math.sqrt((asteroid['position'][0] - ship_state['position'][0])**2 + (asteroid['position'][1] - ship_state['position'][1])**2)
            
            if closest_ast is None or distance < a_dist:
                #if asteroids_already_shot == False:
                closest_ast = asteroid
                a_dist = distance
            #asteroids_already_shot = False
        if closest_ast is None:
            print("ALL DONE")
            if self.delay == 1:
                fire = True
                self.delay = 0
                
                
            else:
                fire = False
            self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
            return 0, 0, fire, False
        

        
        #predicting the position of the asteroid in the future
        bsf  = 800/30 #pixels per frame
        time_bullet = a_dist/bsf + 1 #frames
        #time_bullet  = 0
        future_ast_x = closest_ast["position"][0] + time_bullet*(closest_ast["velocity"][0]/30)
        future_ast_y = closest_ast["position"][1] + time_bullet*(closest_ast["velocity"][1]/30)
        
        #finding the desired angle to shoot for the closest asteroid
        desired_angle = math.degrees(math.atan2(future_ast_y - ship_state['position'][1], future_ast_x - ship_state['position'][0]))
        
        #delaying so that you wait for the ship to finish turning before firing
        if self.delay == 1:
            self.rest_counter = game_state["sim_frame"]
        
            fire = True
            self.delay = 0
              
        #converting the angle to the range 0-360      
        if desired_angle < 0 :
            desired_angle  = 360 + desired_angle
        
        
        heading = ship_state['heading']
        
        #turning towards the desired angle // finding which direction to turn
        if heading < desired_angle and desired_angle - heading < 180:
            if abs(desired_angle - heading) > 6:
                turn_rate = 180
              
            else:
                turn_rate = 30* abs(desired_angle-heading)  
                if game_state["sim_frame"] - self.rest_counter >=2:
                    self.delay = 1  
                    if closest_ast is not None:
                        closest_ast["sim_frame"] = game_state["sim_frame"] + time_bullet
                        
                        self.asteroids_shot.append(closest_ast)
                
        else:
            if abs(desired_angle - heading) > 6:
                turn_rate = -180
            else:
                turn_rate = -1*(30* abs(desired_angle-heading))    
                if game_state["sim_frame"] - self.rest_counter >=2:
                    self.delay = 1  
                    if closest_ast is not None:
                        closest_ast["sim_frame"] = game_state["sim_frame"] + time_bullet
                        
                        self.asteroids_shot.append(closest_ast)
                
        
        thrust = 0
        
        self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
                
        drop_mine = False
        if ship_state["is_respawning"] :
            fire = False
        print()
        print("\ndelay=", self.delay , "\nrest_counter=", self.rest_counter, "\nsim_frame =", game_state["sim_frame"], "\nfire", fire, 
              "\nclosest_ast =  ", closest_ast, "\nasteroids_shot = ", self.asteroids_shot)
        
        
        return thrust, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        """
        Simple property used for naming controllers such that it can be displayed in the graphics engine

        Returns:
            str: name of this controller
        """
        return "akila Controller"
    
    
    
