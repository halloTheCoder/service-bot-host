from rasa_core_sdk import Action
from rasa_core_sdk.events import SlotSet
from rasa_core_sdk.forms import FormAction, FormField

import pandas as pd
import string
import os
import requests
import datetime
import logging
import random
import json

import geocoder

import sendgrid
from sendgrid.helpers.mail import *
from send_message import Msg
from credentials import SENDGRID_API_KEY, PHONE_NO_API_KEY

# SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

logger = logging.getLogger(__name__)


appliances = ['refrigerator', 'fridge', 'freezer', 'dishwasher', 'wall oven', 'microwave', 'washer', 'dryer', 'air conditioner', 'ac', 'a.c.', 'a.c']
pincodes_available = ["12401", "20036", "06360", "06320", "06355", "06351", "06320", "06379", "06340", "06365", "06385", "06360", "27405", "70301", "34135", "15701", "80003"]

# this slot is used to store information needed
# to do the form handling, needs to be part
# of the domain
FORM_SLOT_NAME = "requested_slot"

# EntityFormField(entity_name, slot_name), which will look for an entity called entity_name to fill a slot slot_name.
# BooleanFormField(slot_name, affirm_intent, deny_intent), which looks for the intents affirm_intent and deny_intent to fill a boolean slot called slot_name.
# FreeTextFormField(slot_name) : which will use the next user utterance to fill the text slot slot_name
class CustomFormField(FormField):
    # noinspection PyMethodMayBeStatic
    def validate(self, entity, value, tracker, dispatcher, events_custom = None):
        """Check if extracted value for a requested slot is valid.
        Users should override this to implement custom validation logic,
        returning None indicates a negative validation result, and the slot
        will not be set.
        """
        global pincodes_available

        df = pd.read_excel('SampleModelSerialGEA.xlsx')
        print(entity, value)

        if entity == 'appliance':      ###IMP :: can reduce appliance value to one allowed here
            print('Checking appliance')
            if value not in appliances:
                print('error')
                value = None

            else:
                idx_lis = df.index[df.loc[:, 'Product Line'].map(lambda x : x.lower()) == value.lower()].tolist()

                if tracker.get_slot('serialnumber') and not tracker.get_slot('serialnumber').upper() in [df.loc[i, 'Serial Number'] for i in idx_lis]:
                    dispatcher.utter_message("For appliance %s serial number %s does not match !!!" % (value, tracker.get_slot('serialnumber')))
                    value = None

                elif tracker.get_slot('modelnumber') and not tracker.get_slot('modelnumber').upper() in [df.loc[i, 'Model Number'] for i in idx_lis]:
                    dispatcher.utter_message("For appliance %s model number %s does not match !!!" % (value, tracker.get_slot('modelnumber')))
                    value = None


        if entity == 'modelnumber':
            print('Checking modelnumber')
            if not any(df.loc[:, 'Model Number'] == value.upper()):
                print('error')
                dispatcher.utter_message("Model no %s not in database !!!" % tracker.get_slot('modelnumber'))
                value = None

            else:
                idx_lis = df.index[df.loc[:, 'Model Number'] == value.upper()].tolist()
                idx = idx_lis[0]

                if tracker.get_slot('appliance') and not df.loc[idx, 'Product Line'].lower() == tracker.get_slot('appliance'):
                    dispatcher.utter_message("For model number %s appliance %s does not match !!!" % (value, tracker.get_slot('appliance')))
                    value = None

                elif not tracker.get_slot('appliance'):
                    events_custom.extend([SlotSet("appliance", df.loc[idx, 'Product Line'].lower())]) 
                    dispatcher.utter_message("For model number %s appliance %s added from database !!!" % (value, df.loc[idx, 'Product Line'].lower()))

                if tracker.get_slot('serialnumber') and not tracker.get_slot('serialnumber').upper() in [df.loc[i, 'Serial Number'] for i in idx_lis]:
                    dispatcher.utter_message("For model number %s serial number %s does not match !!!" % (value, tracker.get_slot('serialnumber')))
                    value = None


        if entity == 'serialnumber':
            print('Checking serialnumber')
            
            # if df[idx]['Serial Number'] == value.upper():
            #     print('error')
            #     value = None
            if not any(df.loc[:, 'Serial Number'] == value.upper()):
                print('error')
                dispatcher.utter_message("Serial no %s not in database !!!" % tracker.get_slot('serialnumber'))
                value = None
            else:
                idx = df.index[df.loc[:, 'Serial Number'] == value.upper()].tolist()[0]
                
                if tracker.get_slot('modelnumber') and not df.loc[idx, 'Model Number'] == tracker.get_slot('modelnumber').upper():
                    dispatcher.utter_message("For serial number %s model number %s does not match !!!" % (value, tracker.get_slot('modelnumber')))
                    value = None
                
                elif not tracker.get_slot('modelnumber'):
                    print('Adding modelnumber given serialnumber')
                    events_custom.extend([SlotSet('modelnumber', df.loc[idx, 'Model Number'].lower())])     
                    dispatcher.utter_message("For serial number %s model number %s added from database !!!" % (value, df.loc[idx, 'Model Number'].lower()))

                if tracker.get_slot('appliance') and not df.loc[idx, 'Product Line'].lower() == tracker.get_slot('appliance'):
                    dispatcher.utter_message("For serial number %s appliance %s does not match !!!" % (value, tracker.get_slot('appliance')))
                    value = None

                elif not tracker.get_slot('appliance'):
                    print('Adding appliance given serialnumber')
                    events_custom.extend([SlotSet('appliance', df.loc[idx, 'Product Line'].lower())]) 
                    dispatcher.utter_message("For serial number %s appliance %s added from database !!!" % (value, df.loc[idx, 'Product Line'].lower()))
                

        if entity == 'pincode':
            print(value)
            #print(value.type)
            if value not in pincodes_available:
                print('error')
                dispatcher.utter_message("The provided pincode %s is unavailable for service. We are sorry for the inconvinence." % value)
                value = None

        if entity == 'phonenumber':
            try:
                print('Checking phone number')
                r = requests.get('http://apilayer.net/api/validate?access_key=%s&number=%s&country_code=IN&format=1'%(PHONE_NO_API_KEY, value)).json()
                print(r)
                if not r['valid']:
                    value = None
            except Exception as e:
                print(str(e))
                dispatcher.utter_message("Phone No is unable to be confirmed !!!! Believing entered info is correct")

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
            validated = self.validate(entity["entity"], entity["value"], tracker, dispatcher, events_custom)
            if validated is None:
                # if entity == 'pincode':
                #     dispatcher.utter_message("The provided pincode is unavailable for service. We are sorry for the inconvinence.")
                # else:
                #     dispatcher.utter_message("Entered information is wrong. Please re-enter!!!!")
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
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)
        if any(df.loc[:, 'TrackID'] == trackidnum):
            return create_trackid(size = size)
    return trackidnum

class ActionGetComplaintDetail(FormAction):
    RANDOMIZE = False

    @staticmethod
    def required_fields():
        return [
            FreeTextFormField("serialnumber"),
            FreeTextFormField("appliance"),
            FreeTextFormField("issue"),
            FreeTextFormField("modelnumber"),
            FreeTextFormField("name"),
            FreeTextFormField("email"),
            FreeTextFormField("phonenumber"),
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
            print(e)
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

        day_dict = {'sunday' : 0, 'monday' : 1, 'tuesday' : 2, 'wednesday' : 3, 'thursday' : 4 , 'friday' :  5, 'saturday' : 6}
        technician_dict = {'scott' : 0, 'larry' : 1, 'tim' : 2}

        
        pin_code = tracker.get_slot('pincode')
        time = tracker.get_slot('time')
        technician_slot = None

        if time:
            technician, day, time_slot = time.split('\t')
            technician_slot = technician

            with open('technician.json') as json_file:
                data = json.load(json_file)

            data[pin_code][technician_dict[technician]]['day'][day_dict[day]] = 1

            with open('technician.json', 'w') as outfile:
                json.dump(data, outfile, indent = 2)
        else:
            date = tracker.get_slot('date')
            time_slot = tracker.get_slot('timeslots')

            print(date, time_slot)

            time1 = tracker.get_slot("time1")
            time2 = tracker.get_slot("time2")
            time3 = tracker.get_slot("time3")

            technician1, day1, time_slot1 = time1.split('\t')
            technician2, day2, time_slot2 = time2.split('\t')
            technician3, day3, time_slot3 = time3.split('\t')

            print(day1, time_slot1)

            with open('technician.json') as json_file:
                data = json.load(json_file)

            if(date == day1 and time_slot == time_slot1):
                print(day1, time_slot1)

                technician_slot = technician1
                data[pin_code][technician_dict[technician1]]['day'][day_dict[day1]] = 1

            if(date == day2 and time_slot == time_slot2):
                print(day2, time_slot2)

                technician_slot = technician2
                data[pin_code][technician_dict[technician2]]['day'][day_dict[day2]] = 1

            if(date == day3 and time_slot == time_slot3):
                print(day3, time_slot3)

                technician_slot = technician3
                data[pin_code][technician_dict[technician3]]['day'][day_dict[day3]] = 1


            with open('technician.json', 'w') as outfile:
                json.dump(data, outfile, indent = 2)


        return [SlotSet("trackid", trackidfinal), SlotSet("technician", technician_slot), SlotSet("time", None), SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]


##############################################################################################################################

class GenerateTrackID(Action):
    def name(self):
        return 'action_store_details'

    def run(self, dispatcher, tracker, domain):
        # trackidnum = create_trackid()

        if not os.path.exists('complaints.csv'):
            with open('complaints.csv', 'w') as f:
                f.write('Appliance\tIssue\tModelNumber\tSerialNumber\tName\tEmail\tPhone No\tAddress\tPincode\tTechnician\tDate\tTimeSlots\tTrackID\n')

        with open('complaints.csv', 'a') as f:
            f.write('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tracker.get_slot("appliance"), tracker.get_slot("issue"), tracker.get_slot("modelnumber"), 
                tracker.get_slot("serialnumber"), tracker.get_slot("name"), tracker.get_slot("email"), tracker.get_slot("phonenumber"), tracker.get_slot("address"), 
                tracker.get_slot("pincode"), tracker.get_slot("technician"), tracker.get_slot("date"), tracker.get_slot("timeslots"), tracker.get_slot("trackid")))

        dispatcher.utter_message("Your unique track id is ")
        dispatcher.utter_message(tracker.get_slot("trackid"))
        dispatcher.utter_message("\nYou will recieve the same in your mail and your phone too with all the details.")

        try:
            sg = sendgrid.SendGridAPIClient(apikey = SENDGRID_API_KEY)
            from_email = Email("watchakash1997@gmail.com")
            to_email = Email(tracker.get_slot("email"))
            subject = "Service appoinment of GEA appliance."
            content_message = "Complaint: " + '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' % (tracker.get_slot("appliance"), tracker.get_slot("issue"),
                    tracker.get_slot("modelnumber"), tracker.get_slot("serialnumber"), tracker.get_slot("name"), tracker.get_slot("email"),
                    tracker.get_slot("address"), tracker.get_slot("pincode"), tracker.get_slot("date"), tracker.get_slot("timeslots"), tracker.get_slot("trackid"))

            content = Content(type_ = "text/plain", value = content_message)
            mail = Mail(from_email, subject, to_email, content)
            response = sg.client.mail.send.post(request_body = mail.get())
            print(response.status_code)
            print(response.body)
            print(response.headers)

        except Exception as e:
            dispatcher.utter_message("Error in sending mail to %s !!!" % tracker.get_slot('email'))
            print(str(e))
        
        try:
            msg = Msg()
            msg.send_msg(subject + '\n' + content_message)
        except Exception as e:
            dispatcher.utter_message("Error in sending sms to your phone no %s!!!" % tracker.get_slot('phonenumber'))
            print(str(e))

        return []

##############################################################################################################################

def generate_timeslots(tracker, pin_code, skip_day = None, appliance = None):
    time_slots = []

    time_taken_for_diff_appliance = {'refrigerator' : 3, 'fridge' : 3, 'freezer' : 1, 'dishwasher' : 2, 'wall oven' : 1, 'microwave' : 2,
                             'washer' : 2, 'dryer' : 1, 'air conditioner' : 3, 'ac' : 3, 'a.c.' : 3, 'a.c' : 3}

    day_dict = {0 : 'sunday', 1 : 'monday', 2 : 'tuesday', 3 : 'wednesday', 4 : 'thursday', 5 : 'friday', 6 : 'saturday'}
    technician_dict = {0 : 'scott', 1 : 'larry', 2 : 'tim'}

    with open('technician.json') as json_file:
        data = json.load(json_file)

    technicians = data[pin_code]
    days_choice = []
    technician_choice = []
    count = 0
    
    dy = datetime.datetime.today().weekday() + 1
    dy = (dy + 1)%7

    for _ in range(7):
        if skip_day and dy == skip_day:
            dy = (dy + 1)%7
            continue
        for i in range(len(technicians)):
            print(technician_dict[i], day_dict[dy])
            if technicians[i]['day'][dy] == 0:
                days_choice.append(dy)                                      ## Storing day information
                technician_choice.append(i)                                 ## Storing technician information
                count += 1
                break
        dy = (dy + 1)%7
        if count == 3:
            break

    if count == 3:
        for i in range(3):
            day = days_choice[i]
            
            time_taken = time_taken_for_diff_appliance[tracker.get_slot('appliance')] if tracker.get_slot('appliance') else None
            time_taken = time_taken_for_diff_appliance[appliance] if appliance else time_taken

            am_pm = random.choice([1, 2])
            time = random.randint(7, 9) if am_pm == 1 else random.randint(1, 7)
        
            time_slots.append(technician_dict[technician_choice[i]] + "\t" +  day_dict[day] + "\t" + str(time) + " - " + str(time + (time_taken if time_taken else (time + 2))) + (' am' if am_pm == 1 else ' pm'))


    # for _ in range(3):
    #     # day = random.choice(['sunday', 'monday', 'tuseday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'])
    #     day = random.choice([day_dict[(datetime.datetime.today().weekday() + 1) % 7], day_dict[(datetime.datetime.today().weekday() + 2) % 7]])
    #     time_taken = time_taken_for_diff_appliance[tracker.get_slot('appliance')] if tracker.get_slot('appliance') is not None else None
    #     am_pm = random.choice([1, 2])
    #     time = random.randint(1,9) if am_pm == 1 else random.randint(1, 7)
    #     time_slots.append(day + "\t" + str(time) + "-" + str(time + (time_taken if time_taken is not None else str(time + 2))) + (' am' if am_pm == 1 else ' pm'))

    return time_slots


class GenerateTimeSlot(Action):
    def name(self):
        return 'action_get_timeslots'

    def run(self, dispatcher, tracker, domain):
        pin_code = tracker.get_slot('pincode')

        if not pin_code:
            dispatcher.utter_message("Please enter PINCODE first !!!")
            return []
        
        time_slots = generate_timeslots(tracker, pin_code)
        if time_slots == []:
            dispatcher.utter_message("All the appoinments are made for the week. Please try to book your complain some other day. We are very sorry for the inconvinence.")
            return []

        time1, time2, time3 = time_slots
        
        dispatcher.utter_message("These are three recommended timeslots\n-> %s\n-> %s\n-> %s\n" % (time1, time2, time3))

        return [SlotSet("time1", time1), SlotSet("time2", time2), SlotSet("time3", time3)]


class SetTimeSlot(Action):
    def name(self):
        return 'action_set_timeslots'

    def run(self, dispatcher, tracker, domain):
        # pin_code = tracker.get_slot("pincode")

        time = tracker.get_slot('time')
        
        if time is not None:
            day_dict = {'sunday' : 0, 'monday' : 1, 'tuesday' : 2, 'wednesday' : 3, 'thursday' : 4 , 'friday' :  5, 'saturday' : 6}
            technician_dict = {'scott' : 0, 'larry' : 1, 'tim' : 2}
            
            technician, day, time_slot = time.split('\t')
            dispatcher.utter_message("Your selected timeslot :: %s\t%s :: %s has been selected" % (technician, day, time_slot))
                    
            with open('technician.json') as json_file:
                data = json.load(json_file)

            data[tracker.get_slot('pincode')][technician_dict[technician]]['day'][day_dict[day]] = 1

            with open('technician.json', 'w') as outfile:
                json.dump(data, outfile, indent = 2)

            return [SlotSet("technician", technician), SlotSet("date", day), SlotSet("timeslots", time_slot), SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]

        return [SlotSet("time", None)]


##############################################################################################################################

class GetGeoLocationAddress(Action):
    def name(self):
        return 'action_get_geo_location'

    def run(self, dispatcher, tracker, domain):
        try:
            postcode = None
            g = geocoder.ip('me')
            lat, lng = g.latlng
            
            print(lat, lng)
            r = requests.get('https://nominatim.openstreetmap.org/reverse.php?format=json&lat=%f&lon=%f&zoom=18&addressdetails=1'%(lat,lng)).json()
            print(r)

            address = ""

            for k, v in r['address'].items():
                if k == 'postcode':
                    postcode = r['address'][k]
                if k not in ['country', 'country_code']:
                    address += v + " "

            dispatcher.utter_message('Got geo location')
            dispatcher.utter_message('ADDRESS :: %s'%address)
            dispatcher.utter_message('POSTCODE :: %s'%postcode)

            return [SlotSet("address", address), SlotSet("pincode", postcode)]

        except Exception as e:
            print(str(e))
            dispatcher.utter_message('Failed to capture geo-location !!! Please enter manually ...')

        return []

class SetGeoLocationAddress(Action):
    def name(self):
        return 'action_set_geo_location'

    def run(self, dispatcher, tracker, domain):
        ### see intent
        print(tracker.latest_message)
        confirm = tracker.latest_message['intent']['name']
        
        if confirm == 'affirm':
            return []
        else:
            dispatcher.utter_message('Failed to get address !!! Please enter manually ...')

        return [SlotSet("address", None), SlotSet("pincode", None)]

##############################################################################################################################

class ValidatePinCode(Action):
    def name(self):
        return 'action_validate_pin_code'

    def run(self, dispatcher, tracker, domain):
        global pincodes_available

        pincode = tracker.get_slot('pincode')
        if not pincode:
            dispatcher.utter_message("Enter pincode first")

        if not pincode in pincodes_available:
            dispatcher.utter_message("The provided pincode %s is unavailable for service. We are sorry for the inconvinence. Please enter again" % pincode)
            return [SlotSet("picode", None)]

        return []

##############################################################################################################################

class ActionQueryDetail(Action):
    def name(self):
        return 'action_query_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]

                dispatcher.utter_message("Your complaint with track id: %s has following details ::" % tracker.get_slot("trackid"))

                dispatcher.utter_message("Complaint: {%s} , {%s} Address: {%s} {%s} Complain : (appliance_type: {%s}, Model Number: {%s}, Serial Number: {%s}, issue: {%s}) Date : {%s} Time : {%s}." %
                    (df.loc[idx, 'Name'], df.loc[idx, 'Email'], df.loc[idx, 'Address'], df.loc[idx, 'Pincode'], df.loc[idx, 'Appliance'], df.loc[idx, 'ModelNumber'], df.loc[idx, 'SerialNumber'],
                     df.loc[idx, 'Issue'], df.loc[idx, 'Date'], df.loc[idx, 'TimeSlots']))


        return [SlotSet("trackid", None)]


class ActionQueryTimeDetail(Action):
    def name(self):
        return 'action_query_time_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]

                dispatcher.utter_message("Your complaint with track id: ")
                dispatcher.utter_message(tracker.get_slot("trackid"))
                dispatcher.utter_message("has date ::\n")
                dispatcher.utter_message(df.loc[idx, 'Date'])

        return []


class ActionQueryTimeSlotsDetail(Action):
    def name(self):
        return 'action_query_timeslots_detail'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")

        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

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
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

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
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            # dispatcher.utter_message("Enter trackid again !!!")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]

                dispatcher.utter_message("Your complaint with track id: %s has following details ::" % tracker.get_slot("trackid"))
                dispatcher.utter_message("Complaint: {%s} , {%s} Address: {%s} {%s} Complain : (appliance_type: {%s}, Model Number: {%s}, Serial Number: {%s}, issue: {%s}) Date : {%s} Time : {%s}." %
                    (df.loc[idx, 'Name'], df.loc[idx, 'Email'], df.loc[idx, 'Address'], df.loc[idx, 'Pincode'], df.loc[idx, 'Appliance'], df.loc[idx, 'ModelNumber'], df.loc[idx, 'SerialNumber'],
                     df.loc[idx, 'Issue'], df.loc[idx, 'Date'], df.loc[idx, 'TimeSlots']))

        return []


class ComplainModifyGetTime(Action):
    def name(self):
        return 'action_complain_modify_get_time'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]

                day_dict = {'sunday' : 0, 'monday' : 1, 'tuesday' : 2, 'wednesday' : 3, 'thursday' : 4 , 'friday' :  5, 'saturday' : 6}
                technician_dict = {'scott' : 0, 'larry' : 1, 'tim' : 2}

                pincode, old_technician, old_day, appliance = df.loc[idx, 'Pincode'], df.loc[idx, 'Technician'], df.loc[idx, 'Date'], df.loc[idx, 'Appliance']

                time_slots = generate_timeslots(tracker, pincode, skip_day = day_dict[old_day.lower()], appliance = appliance)

                if time_slots == []:
                    dispatcher.utter_message("All the appoinments are made for the week. Please try to book your complain some other day. We are very sorry for the inconvinence.")
                    return []

                time1, time2, time3 = time_slots
                
                dispatcher.utter_message("These are three recommended timeslots\n-> %s\n-> %s\n-> %s\n" % (time1, time2, time3))

                # unset
                with open('technician.json') as json_file:
                    data = json.load(json_file)

                print('Set or Unset ::', data[pincode][technician_dict[old_technician]]['day'][day_dict[old_day]])
                data[pincode][technician_dict[old_technician]]['day'][day_dict[old_day]] = 0

                with open('technician.json', 'w') as outfile:
                    json.dump(data, outfile, indent = 2)

                return [SlotSet("time1", time1), SlotSet("time2", time2), SlotSet("time3", time3)]

        return []


class ComplainModifySetTime(Action):
    def name(self):
        return 'action_complain_modify_set_time'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            dispatcher.utter_message("Enter trackid again !!!")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                pin_code = df.loc[idx, 'Pincode']
                
                day_dict = {'sunday' : 0, 'monday' : 1, 'tuesday' : 2, 'wednesday' : 3, 'thursday' : 4 , 'friday' :  5, 'saturday' : 6}
                technician_dict = {'scott' : 0, 'larry' : 1, 'tim' : 2}

                time = tracker.get_slot('time')
                if time is not None:
                    technician, day, time_slot = time.split('\t')
                    dispatcher.utter_message("Your selected timeslot :: %s and %s has been selected" % (day, time_slot))
                    
                    with open('technician.json') as json_file:
                        data = json.load(json_file)

                    data[pin_code][technician_dict[technician]]['day'][day_dict[day]] = 1

                    with open('technician.json', 'w') as outfile:
                        json.dump(data, outfile, indent = 2)

                    df.loc[idx, 'Technician'] = technician
                    df.loc[idx, 'Date'] = day
                    df.loc[idx, 'TimeSlots'] = time_slot
                    df.to_csv('complaints.csv', sep = '\t', index = False)

                    dispatcher.utter_message("Your complaint with track id: %s has been successfully updated to %s :: %s !!!" % (track_id, day, time_slot))
                    return [SlotSet("time", None), SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]

                elif tracker.get_slot('date') and tracker.get_slot('timeslots'):
                    date = tracker.get_slot('date')
                    time_slot = tracker.get_slot('timeslots')

                    print(date, time_slot)

                    with open('technician.json') as json_file:
                        data = json.load(json_file)

                    time1 = tracker.get_slot("time1")
                    time2 = tracker.get_slot("time2")
                    time3 = tracker.get_slot("time3")

                    technician1, day1, time_slot1 = time1.split('\t')
                    technician2, day2, time_slot2 = time2.split('\t')
                    technician3, day3, time_slot3 = time3.split('\t')

                    print(day1, time_slot1)

                    technician_slot = None

                    if(date == day1 and time_slot == time_slot1):
                        technician_slot = technician1
                        data[pin_code][technician_dict[technician1]]['day'][day_dict[day1]] = 1

                    if(date == day2 and time_slot == time_slot2):
                        technician_slot = technician2
                        data[pin_code][technician_dict[technician2]]['day'][day_dict[day2]] = 1

                    if(date == day3 and time_slot == time_slot3):
                        technician_slot = technician3
                        data[pin_code][technician_dict[technician3]]['day'][day_dict[day3]] = 1

                    with open('technician.json', 'w') as outfile:
                        json.dump(data, outfile, indent = 2)
                    
                    df.loc[idx, 'Technician'] = technician_slot
                    df.loc[idx, 'Date'] = date
                    df.loc[idx, 'TimeSlots'] = time_slot
                    df.to_csv('complaints.csv', sep = '\t', index = False)

                    dispatcher.utter_message("Your complaint with track id: %s has been successfully updated to %s :: %s !!!" % (track_id, date, time_slot))
                    return [SlotSet("time", None), SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]

                else:
                   dispatcher.utter_message("Either select button or enter text containing both DAY and TIMESLOT in same line ...")
                   # Show again the button

        return []


#------------------------------------------------------------------------------------------------------------------------------------------------------

def generate_timeslots_change(tracker, appliance = None):
    time_slots = []

    time_taken_for_diff_appliance = {'refrigerator' : 3, 'fridge' : 3, 'freezer' : 1, 'dishwasher' : 2, 'wall oven' : 1, 'microwave' : 2,
                             'washer' : 2, 'dryer' : 1, 'air conditioner' : 3, 'ac' : 3, 'a.c.' : 3, 'a.c' : 3}

    for i in range(3):
        time_taken = time_taken_for_diff_appliance[appliance] if appliance else None
        am_pm = random.choice([1, 2])
        time = random.randint(7,9) if am_pm == 1 else random.randint(1, 7)
    
        time_slots.append(str(time) + " - " + str(time + (time_taken if time_taken else (time + 2))) + (' am' if am_pm == 1 else ' pm'))

    return time_slots


class ComplainModifyGetTimeSlots(Action):
    def name(self):
        return 'action_complain_modify_get_timeslots'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            dispatcher.utter_message("Enter trackid again !!!")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                appliance = df.loc[idx, 'Appliance']
                time1, time2, time3 = generate_timeslots_change(tracker, appliance)
                dispatcher.utter_message("These are three recommended timeslots\n-> %s\n-> %s\n-> %s\n" % (time1, time2, time3))
                return [SlotSet("time1", time1), SlotSet("time2", time2), SlotSet("time3", time3)]

        return []


class ComplainModifySetTimeSlots(Action):
    def name(self):
        return 'action_complain_modify_set_timeslots'

    def run(self, dispatcher, tracker, domain):
        track_id = tracker.get_slot("trackid")
        df = pd.read_csv('complaints.csv', sep = '\t', dtype = str)

        if track_id is None:
            dispatcher.utter_message("Please enter track-id !!!")

        elif not os.path.exists('complaints.csv') or not any(df.loc[:, 'TrackID'] == track_id.upper()):
            dispatcher.utter_message("Your trackid is not registred with us !!!\nSorry if it is our fault...")
            dispatcher.utter_message("Enter trackid again !!!")
            return [SlotSet("trackid", None)]

        else:
            if any(df.loc[:, 'TrackID'] == track_id.upper()):
                if not tracker.get_slot('timeslots'):
                    dispatcher.utter_message("Select button or Enter timeslot !!!")
                    return []

                idx = df.index[df.loc[:, 'TrackID'] == track_id.upper()].tolist()[0]
                df.loc[idx, 'TimeSlots'] = tracker.get_slot('timeslots')
                df.to_csv('complaints.csv', sep = '\t', index = False)
                dispatcher.utter_message("Your complaint with track id: %s has been successfully updated to %s!!!" % (tracker.get_slot("trackid"), tracker.get_slot('timeslots')))
        
        return [SlotSet("time1", None), SlotSet("time2", None), SlotSet("time3", None)]