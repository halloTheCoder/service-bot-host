from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet
from rasa_core_sdk.forms import FormAction, FormField 

import pandas as pd
import string
import os
import datetime
import logging
import random

logger = logging.getLogger(__name__)

# this slot is used to store information needed
# to do the form handling, needs to be part
# of the domain
FORM_SLOT_NAME = "requested_slot"

# EntityFormField(entity_name, slot_name), which will look for an entity called entity_name to fill a slot slot_name.
# BooleanFormField(slot_name, affirm_intent, deny_intent), which looks for the intents affirm_intent and deny_intent to fill a boolean slot called slot_name.
# FreeTextFormField(slot_name) : which will use the next user utterance to fill the text slot slot_name
class CustomFormField(FormField):
    # noinspection PyMethodMayBeStatic
    def validate(self, entity, value):
        """Check if extracted value for a requested slot is valid.
        Users should override this to implement custom validation logic,
        returning None indicates a negative validation result, and the slot
        will not be set.
        """
        df = pd.read_excel('SampleModelSerialGEA.xlsx')
        print(entity, value)
        if entity == 'appliance':      ###IMP :: can reduce appliance value to one allowed here
            print('Checking')
            if value not in ['refrigerator', 'fridge', 'freezer', 'dishwasher', 'wall oven', 'microwave',
                             'washer', 'dryer', 'air conditioner', 'ac', 'a.c.', 'a.c']:
                print('error')
                value = None
        
        if entity == 'modelnumber':
            print('Checking')
            if not any(df.loc[:, 'Model Number'] == value.upper()):
                print('error')
                value = None

        if entity == 'serialnumber':
            print('Checking')
            if not any(df.loc[:, 'Serial Number'] == value.upper()):
                print('error')
                value = None

        return value


class BooleanFormField(CustomFormField):
    """A form field that prompts the user for a yes or no answer.
    The interpreter should map positive and negative answers to
    the intents ``affirm_intent`` and ``deny_intent``.
    """

    def __init__(self, slot_name, affirm_intent, deny_intent):
        self.slot_name = slot_name
        self.affirm_intent = affirm_intent
        self.deny_intent = deny_intent

    def extract(self, tracker, dispatcher):
        # type: (Tracker) -> List[EventType]

        intent = tracker.latest_message.get("intent", {}).get("name")
        if intent == self.affirm_intent:
            value = True
        elif intent == self.deny_intent:
            value = False
        else:
            return []

        return [SlotSet(self.slot_name, value)]


class FreeTextFormField(CustomFormField):

    def __init__(self, slot_name):
        self.slot_name = slot_name

    def extract(self, tracker, dispatcher):
        # type: (Tracker) -> List[EventType]

        print(tracker.latest_message)

        events_custom = []
        
        for entity in tracker.latest_message.get("entities", {}):
            # if entity["entity"] == self.slot_name: 
            validated = self.validate(entity["entity"], entity["value"])
            if validated is None:
                dispatcher.utter_message("Entered information is wrong. Please re-enter!!!!")
                # if validated is not None:
            events_custom.extend([SlotSet(entity["entity"], validated)])
                # return [SlotSet(self.slot_name, validated)]
        return events_custom


def trackid_generator(size = 5, chars = string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def create_trackid(size = 5):
    trackidnum = trackid_generator(size = size)
    if os.path.exists('complaints.csv'):
        df = pd.read_csv('complaints.csv', sep = '\t')
        if any(df.loc[:, 'TrackID'] == trackidnum):
            return create_trackid(size = size)
    return trackidnum

class ActionSearchRestaurants(FormAction):
    RANDOMIZE = False

    @staticmethod
    def required_fields():
        return [
            FreeTextFormField("appliance"),
            FreeTextFormField("issue"),
            FreeTextFormField("modelnumber"),
            FreeTextFormField("serialnumber"),
            FreeTextFormField("name"),
            FreeTextFormField("email"),
            FreeTextFormField("address"),
            FreeTextFormField("pincode"),
            FreeTextFormField("date"),
            FreeTextFormField("timeslots"),
            BooleanFormField("confirmcomplain", "affirm", "deny")
        ]

    def name(self):
        return 'action_get_complaint_detail'

    def get_requested_slot(self, tracker, dispatcher):
        # type: (Tracker) -> List[EventType]

        requested_slot = tracker.get_slot(FORM_SLOT_NAME)

        required = self.required_fields()

        if self.RANDOMIZE:
            random.shuffle(required)

        if requested_slot is None:
            return []
        else:
            fields = [f
                      for f in required
                      if f.slot_name == requested_slot]

            if len(fields) == 1:
                return fields[0].extract(tracker, dispatcher)
            else:
                logger.debug("Unable to extract value "
                             "for requested slot: {}".format(requested_slot))
                return []

    def run(self, dispatcher, tracker, domain):

        events = (self.get_requested_slot(tracker, dispatcher) +
                  self.get_other_slots(tracker))

        temp_tracker = tracker.copy()
        for e in events:
            temp_tracker.slots[e["name"]] = e["value"]

        for field in self.required_fields():
            if self.should_request_slot(temp_tracker, field.slot_name):

                dispatcher.utter_template(
                        "utter_ask_{}".format(field.slot_name),
                        tracker)

                events.append(SlotSet(FORM_SLOT_NAME, field.slot_name))
                return events

        # there is nothing more to request, so we can submit
        events_from_submit = self.submit(dispatcher, temp_tracker, domain) or []

        return events + events_from_submit

    def submit(self, dispatcher, tracker, domain):
        dispatcher.utter_message("Your complaint has been logged successfully !!!!. You will be recieving a unique track-id which can be used to modify/cancel the complaint")
        # return []
        trackidnum = create_trackid()
        trackidfinal = "TR" + trackidnum
        print(trackidnum, trackidfinal)

        # if not os.path.exists('complaints.csv'):
        #     with open('complaints.csv', 'w') as f:
        #         f.write('Appliance\tIssue\tModelNumber\tSerialNumber\tName\tEmail\tAddress\tPincode\tDate\tTimeSlots\tTrackID\n')
        
        # with open('complaints.csv', 'a') as f:
        #     f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tracker.get_slot("appliance"), tracker.get_slot("issue"),
        #         tracker.get_slot("modelnumber"), tracker.get_slot("serialnumber"), tracker.get_slot("name"), tracker.get_slot("email"),
        #         tracker.get_slot("address"), tracker.get_slot("pincode"), tracker.get_slot("date"), tracker.get_slot("timeslots"), tracker.get_slot("trackid")))

        # dispatcher.utter_message("Your unique track id is ") 
        # dispatcher.utter_message(tracker.get_slot("trackid")) 
        return [SlotSet("trackid", trackidfinal)]


##############################################################################################################################


class GenerateTrackID(Action):
    def name(self):
        return 'action_store_details'

    def run(self, dispatcher, tracker, domain):
        # trackidnum = create_trackid()

        if not os.path.exists('complaints.csv'):
            with open('complaints.csv', 'w') as f:
                f.write('Appliance\tIssue\tModelNumber\tSerialNumber\tName\tEmail\tAddress\tPincode\tDate\tTimeSlots\tTrackID\n')
        
        with open('complaints.csv', 'a') as f:
            f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tracker.get_slot("appliance"), tracker.get_slot("issue"),
                tracker.get_slot("modelnumber"), tracker.get_slot("serialnumber"), tracker.get_slot("name"), tracker.get_slot("email"),
                tracker.get_slot("address"), tracker.get_slot("pincode"), tracker.get_slot("date"), tracker.get_slot("timeslots"), tracker.get_slot("trackid")))

        dispatcher.utter_message("Your unique track id is ") 
        dispatcher.utter_message(tracker.get_slot("trackid"))
        return [] 

##############################################################################################################################

def generate_timeslots(tracker):
    time_slots = []

    time_taken_for_diff_appliance = {'refrigerator' : 3, 'fridge' : 3, 'freezer' : 1, 'dishwasher' : 2, 'wall oven' : 1, 'microwave' : 2,
                             'washer' : 2, 'dryer' : 1, 'air conditioner' : 3, 'ac' : 3, 'a.c.' : 3, 'a.c' : 3}

    day_dict = {0 : 'monday', 1 : 'tuseday', 2 : 'wednesday', 3 : 'thursday', 4 : 'friday', 5 : 'saturday', 6 : 'sunday'}

    for _ in range(3):
        # day = random.choice(['sunday', 'monday', 'tuseday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
        day = random.choice([day_dict[(datetime.datetime.today().weekday() + 1) % 7], day_dict[(datetime.datetime.today().weekday() + 2) % 7]])
        
        time_taken = time_taken_for_diff_appliance[tracker.get_slot('appliance')] if tracker.get_slot('appliance') is not None else None

        am_pm = random.choice([1, 2])
        
        time = random.randint(1,9) if am_pm == 1 else random.randint(1, 7)
        
        time_slots.append(day + "\t" + str(time) + "-" + str(time + (time_taken if time_taken is not None else str(time + 2))) + (' am' if am_pm == 1 else ' pm'))
    
    return time_slots

class GenerateTimeSlot(Action):
    def name(self):
        return 'action_get_timeslots'

    def run(self, dispatcher, tracker, domain):
        time1, time2, time3 = generate_timeslots(tracker)
        dispatcher.utter_message("These are three recommended timeslots\n-> %s\n-> %s\n-> %s\n" % (time1, time2, time3))
        # dispatcher.utter_message("You can select one out of these !!!")
        return [SlotSet("time1", time1), SlotSet("time2", time2), SlotSet("time3", time3)]

class SetTimeSlot(Action):
    def name(self):
        return 'action_set_timeslots'

    def run(self, dispatcher, tracker, domain):
        time = tracker.get_slot('time')
        if time is not None:
            day = time.split('\t')[0]
            time_slot = time.split('\t')[1]
            dispatcher.utter_message("Your selected timeslot :: %s " % (time))
            dispatcher.utter_message("has been selected")
            return [SlotSet("date", day), SlotSet("time_slots", time_slot), SlotSet("time", None)]

        return [SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]


##############################################################################################################################


class ActionQueryDetail(Action):
    def name(self):
        return 'action_query_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
        
        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has following details ::\n")
                dispatcher.utter_message("Complaint: {%s} , {%s} Address: {%s} {%s} Complain : (appliance_type: {%s}, Model Number: {%s}, Serial Number: {%s}, issue: {%s}) Date : {%s} Time : {%s}." % 
                    (df.loc[idx, 'Name'], df.loc[idx, 'Email'], df.loc[idx, 'Address'], df.loc[idx, 'Pincode'], df.loc[idx, 'Appliance'], df.loc[idx, 'ModelNumber'], df.loc[idx, 'SerialNumber'], 
                     df.loc[idx, 'Issue'], df.loc[idx, 'Date'], df.loc[idx, 'TimeSlots']))


        return [SlotSet("trackid", None)]


class ActionQueryTimeDetail(Action):
    def name(self):
        return 'action_query_time_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
        
        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has timeslots ::\n")
                dispatcher.utter_message(df.loc[idx, 'Date'])

        return []


class ActionQueryTimeSlotsDetail(Action):
    def name(self):
        return 'action_query_timeslots_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
        
        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has timeslots ::\n")
                dispatcher.utter_message(df.loc[idx, 'TimeSlots'])

        return []


##############################################################################################################################


class CancelComplain(Action):
    def name(self):
        return 'action_cancel_complain'
        
    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")
        
        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
        
        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                df.drop(index = idx, inplace = True)
                df.to_csv('complaints.csv', sep = '\t', index = False)
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has been successfully deleted !!!")

        return [SlotSet("trackid", None)]


##############################################################################################################################


class ComplainModifyCheckTrackID(Action):
    def name(self):
        return 'action_complain_modify_check_track_id'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")
        
        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            return [SlotSet("trackid", None)]

        else:
            dispatcher.utter_message("Your complaint with track id: ")
            dispatcher.utter_message(tracker.get_slot("trackid"))
            dispatcher.utter_message("has following details ::\n")
            dispatcher.utter_message("Complaint: {%s} , {%s} Address: {%s} {%s} Complain : (appliance_type: {%s}, Model Number: {%s}, Serial Number: {%s}, issue: {%s}) Date : {%s} Time : {%s}." % 
                (df.loc[idx, 'Name'], df.loc[idx, 'Email'], df.loc[idx, 'Address'], df.loc[idx, 'Pincode'], df.loc[idx, 'Appliance'], df.loc[idx, 'ModelNumber'], df.loc[idx, 'SerialNumber'], 
                 df.loc[idx, 'Issue'], df.loc[idx, 'Date'], df.loc[idx, 'TimeSlots']))


        return []   


class ComplainModifyTime(Action):
    def name(self):
        return 'action_complain_modify_change_time'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")
        
        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                df.loc[idx, 'Date'] = tracker.get_slot('date')
                df.to_csv('complaints.csv', sep = '\t', index = False)
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has been successfully updated !!!")

        return []   


class ComplainModifyTimeSlots(Action):
    def name(self):
        return 'action_complain_modify_change_timeslots'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t')

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")
        
        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                df.loc[idx, 'TimeSlots'] = tracker.get_slot('timeslots')
                df.to_csv('complaints.csv', sep = '\t', index = False)
                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has been successfully updated !!!")

        return []   