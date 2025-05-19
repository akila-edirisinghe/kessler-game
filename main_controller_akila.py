# -*- coding: utf-8 -*-
# Copyright © 2022 Thales. All Rights Reserved.
# NOTICE: This file is subject to the license agreement defined in file 'LICENSE', which is part of
# this source code package.

from src.kesslergame import KesslerController
from typing import Dict, Tuple
from fuzzylogic import get_priority
from impact_time_cal import predict_collision
import math, json

import time

PRINT_EXPLANATION = True
NO_PRINTS = False

_last_print_time = 0
_last_firing_print_time = 0
_last_mine_drop_print_time = 0

_print_interval = 1.0              # normal messages print interval in seconds
_firing_print_interval = 3.0       # firing messages print interval in seconds
_mine_drop_cooldown = 10.0         # cooldown between mine drop prints in seconds (optional)

_mine_dropped_last = False  # Track if previous call was a mine drop

def log_explanation(message: str):
    global _last_print_time, _last_firing_print_time, _last_mine_drop_print_time, _mine_dropped_last
    if NO_PRINTS:
        return

    message_lower = message.lower()
    is_mine_drop = "mine" in message_lower
    is_firing = "action" in message_lower or "decision" in message_lower

    current_time = time.time()

    if PRINT_EXPLANATION:
        if is_mine_drop:
            if not _mine_dropped_last:
                # Print once per new mine drop event
                print(message)
                _last_mine_drop_print_time = current_time
                _mine_dropped_last = True
            # else: suppress repeated mine drop prints until a non-mine drop event happens
        else:
            _mine_dropped_last = False  # Reset flag when no mine drop in this call

            if is_firing:
                if current_time - _last_firing_print_time >= _firing_print_interval:
                    print(message)
                    _last_firing_print_time = current_time
            else:
                if current_time - _last_print_time >= _print_interval:
                    print(message)
                    _last_print_time = current_time
    else:
        with open('explanations_akila.txt', 'a+') as file:
            file.write(message + '\n')



#account for asteroids coming off screen
#adding smarter mines  ISH
# if limited bullets, don't spam. if not, keep shooting all the time.

class AkilaController(KesslerController):
    def __init__(self):
        """
        Any variables or initialization desired for the controller can be set up here
        """
        self.delay = 0
        self.asteroids_shot = []
        self.rest_counter = 0
        self.lookup_table = {}
        self.prev_best_ast = None
        
        '''
        priority_lookup = {}
        for size in range(1,5):
            for impact_time in range(301):
                for turn_time in range(31):
                    
                    priority_lookup[f"{size},{impact_time},{turn_time}"] = get_priority(size,impact_time, turn_time)
                    
        with open('priorty_lookup_table.json', 'w') as json_file:
            json.dump(priority_lookup, json_file)
            '''
        with open('priorty_lookup_table.json', 'r') as json_file:
            self.lookup_table = json.load(json_file)
          
        ...
        #add a frame counter to keep track of the time
    def get_fuzzy_values(self, size, impact_time, turn_time):
   
        if impact_time > 300:
            
            #print("\n","size", size, "impact time", impact_time, "turn time", turn_time,"\n")
            impact_time = 300
                     
        #print("\n","size", size, "impact time", impact_time, "turn time", turn_time,"\n")
        key = f"{size},{impact_time},{turn_time}"
        return self.lookup_table[key]

    def actions(self, ship_state: Dict, game_state: Dict) -> Tuple[float, float, bool, bool]:
        
        
        
        
        
        #consider where the asteroid will be in like 2 or 3 seconds in the future and turn towards it(consideration)
        #priority system /use fuzzy logic for this part
        #for invulnerability, check if you are going to hit or not. if no collision, start firing
        
   
        # rounding stuff and then creating a lookup table. //json or pickle to store the data. TODO DONE
        # u can check the future asteroid position for if it is going off screen and if the bullet won'T make it in time.
        # including mines in the future prediction( u are already doing the calculations for it) kamikaze mines TODO ***  DONE 
        #edge case = asteroids not moving -- ex_adv_four_corners_pt1 TODO *** DONE
        #consider wrapping asteroids and collision *consider the impact time so that priority will be inflated TODO ***
        #change priority for fuzzy logic to allow to shoot more asteroids within the same heading TODO *DONE
        #make it shoot no matter what and not wait until it reaches the asteroid it needs to shoot. TODO DONE
        if game_state["time"] == 0:
            self.delay = 0
            self.asteroids_shot = []
            self.rest_counter = 0
            self.prev_best_ast = None
            
        #1 bullet every 3 frames
        # current frame, turning and shooting at the same time,  bullet goes where u were looking
        
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
        if not hasattr(self, "last_logged_target_pos"):
            self.last_logged_target_pos = None

        #pixels per frame
        #bullet speed frames aka how many pixels the bullet move in one frame
        bsf  = 800/30
        heading = ship_state['heading'] # angle between 0-360 your ship is facing.
        fire = False
        drop_mine = False
        
        best_ast = None
        highest_prio = -1*math.inf
        asteroids_already_shot = False
        
        found_prev_best_ast = False
        #print("asteroids in the game", len(game_state['asteroids']))
        #picking the closest asteroid
        '''
        filtering out asteroids that have been shot aka we need not shot ones
        '''
        for asteroid in game_state['asteroids']:
            asteroids_already_shot = False
            for shot_ast in self.asteroids_shot:
                    if shot_ast["velocity"] == asteroid["velocity"] and shot_ast["size"] == asteroid["size"] : #identifer - [velocity, size]
                        asteroids_already_shot = True
                        break
            if asteroids_already_shot == True:
                continue
            
            asteroid_size = asteroid['size']
            impact_time_interval= predict_collision(ship_state['position'], (0,0), 20, asteroid['position'], asteroid['velocity'], asteroid['radius'])
            
            # 0 start time of collision, 1 end time of collision - impact_time_interval 
            turn_time = 0
            impact_time = 0
            #nan not impact
            #inf in impact
            #- means /// - + in collision   -- past coliision ++ future collision**
            
            if math.isinf(impact_time_interval[0]):
                impact_time = 0
            elif math.isnan(impact_time_interval[0]):
                impact_time = 300 #changed from math.inf to 300 because of lookup table keys
            else:
                if impact_time_interval[0] <= 0 and impact_time_interval[1] >= 0:
                    impact_time = 0
                elif impact_time_interval[0] <= 0 and impact_time_interval[1] <= 0:
                    impact_time = 300  #changed from math.inf to 300
                elif impact_time_interval[0] >= 0 and impact_time_interval[1] >= 0:
                    impact_time = impact_time_interval[0]*30
                    #impact is getting rounded later
                else:
                    #print("impact_time_interval", impact_time_interval)
                    raise ValueError("impact time is not being calculated correctly")
                    
                        
         
            distance = math.sqrt((asteroid['position'][0] - ship_state['position'][0])**2 + (asteroid['position'][1] - ship_state['position'][1])**2)   
            time_bullet = distance/bsf + 1 #frames
            future_ast_x = asteroid["position"][0] + time_bullet*(asteroid["velocity"][0]/30)
            future_ast_y = asteroid["position"][1] + time_bullet*(asteroid["velocity"][1]/30)
            desired_angle = math.degrees(math.atan2(future_ast_y - ship_state['position'][1], future_ast_x - ship_state['position'][0]))
           
            turn_time = min(abs(desired_angle - heading),abs(360-abs(desired_angle - heading)))/6 #added abs for the y because it was getting an error for lookup table
            #round down probably
            turn_time = round(turn_time)
            
            '''
            u can do a check here so that if the impact_time is eveer more than 300, we make it 300
            
            '''
            #print("\nimpact_time_interval", impact_time_interval)
            
           #if isinstance(impact_time, int):
            
            #priority = get_priority(asteroid_size,impact_time, turn_time)
            
            priority = self.get_fuzzy_values(asteroid_size,round(impact_time), turn_time)
            #rounding priority
            priority = round(priority)
           
            
            #asteroid_priority_list.append({"priority": priority, "asteroid": asteroid})
            
            prev_asteroids_pos = []#x,y
            if self.prev_best_ast is not None:
                prev_asteroids_pos.append(self.prev_best_ast["position"][0] +self.prev_best_ast["velocity"][0]/30)
                prev_asteroids_pos.append(self.prev_best_ast["position"][1] +self.prev_best_ast["velocity"][1]/30)
                
                if math.isclose(prev_asteroids_pos[0],asteroid["position"][0]) and math.isclose(prev_asteroids_pos[1],asteroid["position"][1]) and self.prev_best_ast["size"] == asteroid["size"] :
                    prev_prio = self.prev_best_ast["priority"]
                    self.prev_best_ast = dict(asteroid)
                    self.prev_best_ast["priority"] = prev_prio
                    found_prev_best_ast = True
                
                    
            
            #mine logic // issue when live is 1 and mine is 1, need to drop mine earlier to save life
            if impact_time_interval[0] > 0 and impact_time_interval[1] > 0 and ship_state["mines_remaining"] > 0 and impact_time !=0 and ship_state["is_respawning"] == False:
                
                '''
                #mine do damage to the ship as well hence no point in dropping mine
                if ship_state["lives_remaining"] == 1 and ship_state["mines_remaining"] >0:
                    if impact_time_interval[0]*30 <= 90:
                        drop_mine = True
                '''
                if impact_time_interval[0]*30 <= 7 :
                    if (asteroid["velocity"] not in self.asteroids_shot ) :#or ship_state["lives_remaining"] > 1
                        drop_mine = True
                        
                       
                                    
            if best_ast is None or priority > highest_prio:
                #if asteroids_already_shot == False:
                best_ast = dict(asteroid)
                highest_prio = priority
            #asteroids_already_shot = False
            #print("best_ast", best_ast)
            
        
        
        if best_ast is None:
            
            if self.delay == 1:
                fire = True
                log_explanation("[Action] Fired a bullet (default behavior, no target)")
                self.delay = 0  
            else:
                fire = False
            self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
            return 0, 0, fire, False
        
        best_ast["priority"] = highest_prio
        
         #meaning it is the first
        if not found_prev_best_ast:
            if self.last_logged_target_pos != tuple(best_ast["position"]):
                log_explanation(f"[Target] New asteroid selected at {tuple(round(x,1)for x in best_ast['position'])} with priority {highest_prio}")
                self.last_logged_target_pos = tuple(best_ast["position"])
            self.prev_best_ast = best_ast

        else:
            if abs(self.prev_best_ast["priority"] - best_ast["priority"]) <= 1:
                best_ast = self.prev_best_ast
                log_explanation(f"[Decision] Staying on target at ({round(best_ast['position'][0],1):.2f}, {round(best_ast['position'][1],1):.2f}) — priority change insignificant ({best_ast['priority']} vs {self.prev_best_ast['priority']})")

            else:
                if self.last_logged_target_pos != tuple(best_ast["position"]):
                    log_explanation(f"[Target] Switching to new higher-priority asteroid at {round(best_ast['position'],1)}")
                    self.last_logged_target_pos = tuple(best_ast["position"])
                self.prev_best_ast = best_ast

        
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
        
        #telling it to keep turning
        if abs(desired_angle - heading) > 6: #180/30 num of degrees u can turn per frame.
            turn_rate = turn_direction*180   # 180 degrees per second aka fastest u can turn.
        #turn rate- degrees per second
           
        #telling it to turn slowly or stop turning
        else:
            turn_rate = turn_direction* 30* abs(desired_angle-heading)  
            if game_state["sim_frame"] - self.rest_counter >=2:
                
            
                self.delay = 1  
                if best_ast is not None:
                    best_ast["sim_frame"] = game_state["sim_frame"] + time_bullet
                    
                    self.asteroids_shot.append(best_ast)
 
        thrust = 0
        self.asteroids_shot = [ast for ast in self.asteroids_shot if ast["sim_frame"] > game_state["sim_frame"]]
                
        
        if ship_state["is_respawning"] :
            fire = False
        
        
        if fire:
            log_explanation(f"[Action] Firing at asteroid at predicted position ({round(future_ast_x,1):.1f}, {round(future_ast_y,1):.1f})")
        else:
            log_explanation("[Decision] Holding fire — no valid target or wrong angle")
        if drop_mine:
            log_explanation(f"[Action] Dropping mine for asteroid at {tuple(round(x,1)for x in best_ast['position'])}")
        return thrust, turn_rate, fire, drop_mine

    

    @property
    def name(self) -> str:
        """
        Simple property used for naming controllers such that it can be displayed in the graphics engine

        Returns:
            str: name of this controller
        """
        return "hitormiss v0.0"
    
    @property
    def custom_sprite_path(self)->str:
        return "akila's turtle fortress spaceship sprite.png"
    
#change best_ast to self.best_ast


