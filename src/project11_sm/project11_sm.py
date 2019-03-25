#!/usr/bin/env python

import rospy
import smach
import smach_ros

from sensor_msgs.msg import Joy
from marine_msgs.msg import Helm

class Project11Context():
    '''
    Contains data passes around states.
    '''
    
    def __init__(self):
        self.last_joy_msg = None
        self.joy_subscriber = rospy.Subscriber('/joy', Joy, self.joystickCallback)
        self.helm_publisher = rospy.Publisher('/helm', Helm, queue_size=10)
        
    def joystickCallback(self, msg):
        self.last_joy_msg = msg

    def checkJoystick(self):
        if self.last_joy_msg is not None:
            state_request = None
            if self.last_joy_msg.buttons[0]:
                state_request = 'manual'
            if self.last_joy_msg.buttons[1]:
                state_request = 'autonomous'
            if self.last_joy_msg.buttons[2]:
                state_request = 'standby'
            ret = (self.last_joy_msg,state_request)
            self.last_joy_msg = None
            return ret


class Standby(smach.State):
    def __init__(self):
        super(Standby, self).__init__(outcomes=['manual','autonomous'], input_keys=['context'], output_keys=['context'])
    
    def execute(self, userdata):
        print 'standby'
        while not rospy.is_shutdown():
            js = userdata.context.checkJoystick()
            if js is not None and js[1] is not None and js[1] != 'standby':
                return js[1]
            rospy.sleep(0.1)

class Manual(smach.State):
    def __init__(self):
        super(Manual, self).__init__(outcomes=['standby','autonomous'], input_keys=['context'], output_keys=['context'])
    
    def execute(self, userdata):
        print 'manual'
        while not rospy.is_shutdown():
            js = userdata.context.checkJoystick()
            if js is not None:
                requested_state = js[1]
                if requested_state is not None and requested_state != 'manual':
                    return requested_state
                msg = js[0]
                helm = Helm()
                helm.header.stamp = rospy.Time.now()
                helm.throttle = msg.axes[1]
                helm.rudder = -msg.axes[3]
                userdata.context.helm_publisher.publish(helm)
            rospy.sleep(0.1)

class Autonomous(smach.State):
    def __init__(self):
        super(Autonomous, self).__init__(outcomes=['standby','manual'], input_keys=['context'], output_keys=['context'])
    
    def execute(self, userdata):
        print 'autonomous'
        while not rospy.is_shutdown():
            js = userdata.context.checkJoystick()
            if js is not None and js[1] is not None and js[1] != 'autonomous':
                return js[1]
            rospy.sleep(0.1)


if __name__ == '__main__':
    rospy.init_node('project11_sm')
    
    sm = smach.StateMachine(outcomes=[])
    sm.userdata.context = Project11Context()
    
    with sm:
        smach.StateMachine.add('STANDBY',    Standby(), transitions= {'manual':'MANUAL', 'autonomous':'AUTONOMOUS'})
        smach.StateMachine.add('MANUAL',     Manual(), transitions= {'standby':'STANDBY', 'autonomous':'AUTONOMOUS'})
        smach.StateMachine.add('AUTONOMOUS', Autonomous(), transitions= {'manual':'MANUAL', 'standby':'STANDBY'})

    sm.execute()
