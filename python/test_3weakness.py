"""
CURR_LIMITを適宜変更して第3関節の力を確認する。
"""


import numpy as np
from typing import List
import csv
import os
from datetime import datetime

from leap_hand_utils.dynamixel_client import *
import leap_hand_utils.leap_hand_utils as lhu
import time
#######################################################
"""This can control and query the LEAP Hand

I recommend you only query when necessary and below 90 samples a second.  Used the combined commands if you can to save time.  Also don't forget about the USB latency settings in the readme.

#Allegro hand conventions:
#0.0 is the all the way out beginning pose, and it goes positive as the fingers close more and more in radians.

#LEAP hand conventions:
#3.14 rad is flat out home pose for the index, middle, ring, finger MCPs.
#Applying a positive angle closes the joints more and more to curl closed in radians.
#The MCP is centered at 3.14 and can move positive or negative to that in radians.

#The joint numbering goes from Index (0-3), Middle(4-7), Ring(8-11) to Thumb(12-15) and from MCP Side, MCP Forward, PIP, DIP for each finger.
#For instance, the MCP Side of Index is ID 0, the MCP Forward of Ring is 9, the DIP of Ring is 11

"""


INIT_CURR_LIMIT = 10


########################################################
class LeapNode:
    def __init__(self):
        ####Some parameters
        # I recommend you keep the current limit from 350 for the lite, and 550 for the full hand
        # Increase KP if the hand is too weak, decrease if it's jittery.
        self.kP = 600
        self.kI = 0
        self.kD = 200
        self.curr_lim = INIT_CURR_LIMIT  ##set this to 550 if you are using full motors!!!!
        self.prev_pos = self.pos = self.curr_pos = lhu.allegro_to_LEAPhand(np.zeros(16))
        #You can put the correct port here or have the node auto-search for a hand at the first 3 ports.
        # For example ls /dev/serial/by-id/* to find your LEAP Hand. Then use the result.  
        # For example: /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7W91VW-if00-port0
        self.motors = motors = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
        try:
            self.dxl_client = DynamixelClient(motors, '/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT8ISOJL-if00-port0', 4000000)
            self.dxl_client.connect()
        except Exception:
            try:
                self.dxl_client = DynamixelClient(motors, '/dev/ttyUSB1', 4000000)
                self.dxl_client.connect()
            except Exception:
                self.dxl_client = DynamixelClient(motors, 'COM13', 4000000)
                self.dxl_client.connect()
        #Enables position-current control mode and the default parameters, it commands a position and then caps the current so the motors don't overload
        self.dxl_client.sync_write(motors, np.ones(len(motors))*5, 11, 1)
        self.dxl_client.set_torque_enabled(motors, True)
        self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kP, 84, 2) # Pgain stiffness     
        self.dxl_client.sync_write([0,4,8], np.ones(3) * (self.kP * 0.75), 84, 2) # Pgain stiffness for side to side should be a bit less
        self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kI, 82, 2) # Igain
        self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.kD, 80, 2) # Dgain damping
        self.dxl_client.sync_write([0,4,8], np.ones(3) * (self.kD * 0.75), 80, 2) # Dgain damping for side to side should be a bit less
        #Max at current (in unit 1ma) so don't overheat and grip too hard #500 normal or #350 for lite
        self.dxl_client.sync_write(motors, np.ones(len(motors)) * self.curr_lim, 102, 2)
        self.dxl_client.write_desired_pos(self.motors, self.curr_pos)
        
        # CSV file monitoring
        self.csv_file_path = 'current_limits.csv'
        self.last_modified_time = 0
        self.current_limits_dict = {}

    def load_current_limits_from_csv(self):
        """CSVファイルからcurrent limitを読み込み、ファイルが更新された場合のみモーターに設定する"""
        try:
            # ファイルの最終更新時刻をチェック
            current_modified_time = os.path.getmtime(self.csv_file_path)
            
            # ファイルが更新されていない場合は何もしない
            if current_modified_time <= self.last_modified_time:
                return False
            
            # CSVファイルを読み込み
            new_limits_dict = {}
            with open(self.csv_file_path, 'r') as file:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    motor_id = int(row['motor_id'])
                    # 安全のため、0-250の範囲に制限し、int型に変換
                    current_limit = int(float(row['current_limit']))
                    current_limit = max(0, min(250, current_limit))  # 0-250の範囲に制限
                    new_limits_dict[motor_id] = current_limit
            
            # 変更があった場合のみモーターに設定
            if new_limits_dict != self.current_limits_dict:
                print(f"CSV file updated at {datetime.fromtimestamp(current_modified_time)}")
                print("Setting new current limits:")
                
                for motor_id, current_limit in new_limits_dict.items():
                    if motor_id in self.motors:
                        self.dxl_client.sync_write([motor_id], [current_limit], 102, 2)
                        print(f"  Motor {motor_id}: {current_limit}mA")
                
                self.current_limits_dict = new_limits_dict
                self.last_modified_time = current_modified_time
                return True
            
            self.last_modified_time = current_modified_time
            return False
            
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return False

    def set_each_fingers_current_limit(self, motor_id : List[int], curr_lim : int):
        self.dxl_client.sync_write(motor_id, np.ones(len(motor_id)) * curr_lim, 102, 2)


    #Receive LEAP pose and directly control the robot
    def set_leap(self, pose):
        self.prev_pos = self.curr_pos
        self.curr_pos = np.array(pose)
        self.dxl_client.write_desired_pos(self.motors, self.curr_pos)
    #allegro compatibility joint angles.  It adds 180 to make the fully open position at 0 instead of 180
    def set_allegro(self, pose):
        pose = lhu.allegro_to_LEAPhand(pose, zeros=False)
        self.prev_pos = self.curr_pos
        self.curr_pos = np.array(pose)
        self.dxl_client.write_desired_pos(self.motors, self.curr_pos)
    #Sim compatibility for policies, it assumes the ranges are [-1,1] and then convert to leap hand ranges.
    def set_ones(self, pose):
        pose = lhu.sim_ones_to_LEAPhand(np.array(pose))
        self.prev_pos = self.curr_pos
        self.curr_pos = np.array(pose)
        self.dxl_client.write_desired_pos(self.motors, self.curr_pos)
    #read position of the robot
    def read_pos(self):
        return self.dxl_client.read_pos()
    #read velocity
    def read_vel(self):
        return self.dxl_client.read_vel()
    #read current
    def read_cur(self):
        return self.dxl_client.read_cur()
    #These combined commands are faster FYI and return a list of data
    def pos_vel(self):
        return self.dxl_client.read_pos_vel()
    #These combined commands are faster FYI and return a list of data
    def pos_vel_eff_srv(self):
        return self.dxl_client.read_pos_vel_cur()
#init the node
def main(**kwargs):
    leap_hand = LeapNode()
    
    while True:
        
        # CSVファイルをチェックしてcurrent limitを更新
        leap_hand.load_current_limits_from_csv()
        
        #Set to an open pose and read the joint angles 33hz
        leap_hand.set_allegro(np.zeros(16))
        print("Position: " + str(leap_hand.read_pos()))
        time.sleep(0.03)

if __name__ == "__main__":
    main()
