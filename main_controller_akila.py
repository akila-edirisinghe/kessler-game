# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.
# NOTICE: This file is subject to the license agreement defined in file 'LICENSE', which is part of
# this source code package.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
from fuzzylogic import get_priority
from impact_time_cal import predict_collision
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
        
        
        # rounding stuff and then creating a lookup table. //json or pickle to store the data.
        # u can check the future asteroid position for if it is going off screen and if the bullet won'T make it in time.
        # including mines in the future prediction( u are already doing the calculations for it) kamikaze mines
        #edge case = asteroids not moving -- ex_adv_four_corners_pt1
        #consider wrapping asteroids and collision *consider the impact time so that priority will be inflated
        #change priority for fuzzy logic to allow to shoot more asteroids within the same heading
        
        
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
        #pixels per frame
        bsf  = 800/30
        heading = ship_state['heading']
        fire = False
        best_ast = None
        highest_prio = -1*math.inf
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
            
            asteroid_size = asteroid['size']
            impact_time_interval= predict_collision(ship_state['position'], (0,0), 20, asteroid['position'], asteroid['velocity'], asteroid['radius'])
            turn_time = 0
            impact_time = 0
            #nan not impact
            #inf in impact
            #- means /// - + in collision   -- past coliision ++ future collision**
            
            if math.isinf(impact_time_interval[0]):
                impact_time = 0
            elif math.isnan(impact_time_interval[0]):
                impact_time = math.inf
            else:
                if impact_time_interval[0] < 0 and impact_time_interval[1] > 0:
                    impact_time = 0
                elif impact_time_interval[0] < 0 and impact_time_interval[1] < 0:
                    impact_time = math.inf
                elif impact_time_interval[0] > 0 and impact_time_interval[1] > 0:
                    impact_time = impact_time_interval[0]
                else:
                    raise ValueError("impact time is not being calculated correctly")
                        
            
            distance = math.sqrt((asteroid['position'][0] - ship_state['position'][0])**2 + (asteroid['position'][1] - ship_state['position'][1])**2)   
            time_bullet = distance/bsf + 1 #frames
            future_ast_x = asteroid["position"][0] + time_bullet*(asteroid["velocity"][0]/30)
            future_ast_y = asteroid["position"][1] + time_bullet*(asteroid["velocity"][1]/30)
            desired_angle = math.degrees(math.atan2(future_ast_y - ship_state['position'][1], future_ast_x - ship_state['position'][0]))
           
            turn_time = min(abs(desired_angle - heading),360-abs(desired_angle - heading))/6
            priority = get_priority(asteroid_size,impact_time, turn_time)
            
            if best_ast is None or priority > highest_prio:
                #if asteroids_already_shot == False:
                best_ast = asteroid
                highest_prio = priority
            #asteroids_already_shot = False
        if best_ast is None:
            print("ALL DONE")
            if self.delay == 1:
                fire = True
                self.delay = 0
                
            else:
                fire = False
            self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
            return 0, 0, fire, False
        

        a_distance = math.sqrt((best_ast['position'][0] - ship_state['position'][0])**2 + (best_ast['position'][1] - ship_state['position'][1])**2)

        
        #predicting the position of the asteroid in the future
         
        time_bullet = a_distance/bsf + 1 #frames
        #time_bullet  = 0
        future_ast_x = best_ast["position"][0] + time_bullet*(best_ast["velocity"][0]/30)
        future_ast_y = best_ast["position"][1] + time_bullet*(best_ast["velocity"][1]/30)
        
       
        
        #delaying so that you wait for the ship to finish turning before firing
        if self.delay == 1:
            self.rest_counter = game_state["sim_frame"]
        
            fire = True
            self.delay = 0
              
         #finding the desired angle to shoot for the closest asteroid
        desired_angle = math.degrees(math.atan2(future_ast_y - ship_state['position'][1], future_ast_x - ship_state['position'][0]))
   
        #converting the angle to the range 0-360      
        if desired_angle < 0 :
            desired_angle  = 360 + desired_angle
     
        
        
        turn_direction = 0
        if heading < desired_angle :
            if desired_angle - heading < 180:
                turn_direction = 1
            else:
                turn_direction = -1
        else:
            if heading - desired_angle < 180:
                turn_direction = -1
            else:
                turn_direction = 1
                
        #turning towards the desired angle // finding which direction to turn
        
        if abs(desired_angle - heading) > 6:
            turn_rate = turn_direction*180 
        else:
            turn_rate = turn_direction* 30* abs(desired_angle-heading)  
            if game_state["sim_frame"] - self.rest_counter >=2:
                print()
                print("\nturn rate", turn_rate, "\nheading", heading, "\ndesired angle", desired_angle)
                self.delay = 1  
                if best_ast is not None:
                    best_ast["sim_frame"] = game_state["sim_frame"] + time_bullet
                    
                    self.asteroids_shot.append(best_ast)
 
        thrust = 0
        self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
                
        drop_mine = False
        if ship_state["is_respawning"] :
            fire = False
        
        return thrust, turn_rate, fire, drop_mine

    @property
    def name(self) -> str:
        """
        Simple property used for naming controllers such that it can be displayed in the graphics engine

        Returns:
            str: name of this controller
        """
        return "akila Controller"
    
    
    
