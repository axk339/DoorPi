"""BRI 20.09.2025 Action that gets and writes akuvox status"""
import logging
import pathlib
from typing import Any, Mapping

import doorpi.actions
from doorpi.status.status_class import DoorPiStatus
from doorpi.actions import snapshot

import datetime
import doorpi

from . import Action

LOGGER = logging.getLogger(__name__)

import requests
import time
last_timeout_warning_time = 0

def akuvoxDND (force, dnd_mute):
	global last_timeout_warning_time
	
	getdnd = True		# get always status
	if force:
		setdnd = True	# and update if target is different
	else:
		setdnd = False
	
	getvol = True		# always get volume
	setvol = True		# and set to 10 if different (except 0, which forces setdnd to mute)
	vol_level = 10
	
	indfile = doorpi.INSTANCE.config["akuvox.indfile"]
	akuvoxPasswordHash = doorpi.INSTANCE.config["akuvox.pwhash"]
	url = 'http://' + doorpi.INSTANCE.config["akuvox.ip"] + '/web'
	try:
		### manage login ###
		
		postdata = '{"target":"login","action":"set","data":{"password":"' + akuvoxPasswordHash + '"},"session":"","web":"1"}'
		response = requests.post(url, data=postdata, timeout=2)
		response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
		
		start_index = response.text.find("encrypt") + 11
		end_index = start_index + 32
		encrypt = response.text[start_index:end_index]
		
		postdata = '{"target":"login","action":"login","data":{"userName":"admin","password":"' + encrypt + '"},"session":"","web":"1"}'
		response = requests.post(url, data=postdata, timeout=2)
		response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
		
		start_index = response.text.find("token") + 9
		end_index = start_index + 8
		token = response.text[start_index:end_index]
		
		### get dnd status - store in local file for further processing
		
		if getdnd:
			postdata = '{"target":"config","action":"info","configData":{"item":["WholeDay&24&61"]},"session":"' + token + '","web":"1"}';
			response = requests.post(url, data=postdata, timeout=2)
			response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
			
			## parse dnd status (..."WholeDay": "1"...)
			start_index = response.text.find("WholeDay") + 12
			end_index = start_index + 1
			dndstatus = response.text[start_index:end_index]
			
			if dndstatus == "0":
				if setdnd and not dnd_mute:
					setdnd = False
					LOGGER.debug ("# skipping force unmute, not needed")
				with open(indfile, "w") as f:
					f.write("unmute")
				LOGGER.debug ("# stored status 'unmute' in " + str(indfile))
			else:
				if setdnd and dnd_mute:
					setdnd = False
					LOGGER.debug ("# skipping force mute, not needed")
				with open(indfile, "w") as f:
					f.write("mute")
				LOGGER.debug ("# stored status 'mute' in " + str(indfile))
		
		### set dnd status, both in local file and on ip phone
		
		if setdnd:
			postdata = '{"target":"config","action":"edit","configData":{"item":["' + ('1' if dnd_mute else '0') + '&24&61"]},"session":"' + token + '","web":"1"}'
			response = requests.post(url, data=postdata, timeout=2)
			response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
			
			if dnd_mute:
				with open(indfile, "w") as f:
					f.write("mute")
				LOGGER.debug ("# stored status 'mute' in " + str(indfile))
			else:
				with open(indfile, "w") as f:
					f.write("unmute")
				LOGGER.debug ("# stored status 'unmute' in " + str(indfile))
			
			LOGGER.debug ("# new dnd status: " + ('1' if dnd_mute else '0'))
		
		### get current ring volume
		
		if getvol:
			
			#{"target":"config","action":"info","configData":{"item":["RingVolume&26&266","TalkVolume&26&272","MicVolume&26&273","TouchSoundEnable&26&1561","ringtoneSoundFile&26&224","SelectRingtoneSoundFile&26&2432"]},"session":"E4D37207","web":"1"}
			postdata = '{"target":"config","action":"info","configData":{"item":["RingVolume&26&266"]},"session":"' + token + '","web":"1"}'
			response = requests.post(url, data=postdata, timeout=2)
			response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
			
			# parse dnd status (..."RingVolume": "10"...)
			start_index = response.text.find("RingVolume") + 14
			end_index = start_index + 2
			volstatus = int(response.text[start_index:end_index])
			
			if setvol and vol_level == volstatus:
				setvol = False
				LOGGER.debug ("# skipping force volume, not needed")
			
			LOGGER.debug ("# volume: " + str(volstatus))
		
		### set volume to defined value (0..15, by default always 10)
		
		if setvol:
			
			if vol_level < 0: vol_level = 0
			if vol_level > 15: vol_level = 15
			
			postdata = '{"target":"config","action":"edit","configData":{"item":["' + str(vol_level) + '&26&266"]},"session":"' + token + '","web":"1"}'
			response = requests.post(url, data=postdata, timeout=2)
			response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)
			
			LOGGER.debug ("# new volume: " + str(vol_level) + ", was " + str(volstatus))
	
	except requests.exceptions.Timeout:
		current_time = time.time()
		loggedWarning = False
		if current_time - last_timeout_warning_time >= 3600:
			LOGGER.warning("Akuvox monitor request timed out, defaulting to 'unmute'")
			last_timeout_warning_time = current_time # Update the time of the last warning
			loggedWarning = True
		else:
			LOGGER.debug("Akuvox monitor request timed out, defaulting to 'unmute' (warning suppressed for 1 hour)")
		try:
			with open(indfile) as f:
				content = f.readline()
			if content != "unmute":
				with open(indfile, "w") as f:
					f.write("unmute")
					if not loggedWarning:
						LOGGER.warning("Akuvox monitor request timed out, defaulting to 'unmute'")
					LOGGER.info ("# stored status 'unmute' in " + str(indfile))
		except:
			if not loggedWarning:
				LOGGER.warning("Akuvox monitor request timed out, defaulting to 'unmute'")
			LOGGER.info ("# error processing file " + str(indfile))
	
	except requests.exceptions.RequestException as e:
		LOGGER.error (f"An error occurred: {e}")


class AkuvoxAction(Action):
    """Gets Akuvox status or sends update."""

    def __init__(self, action: str) -> None:
        super().__init__()
        
        if action == "setmute":
            self.__force = True
            self.__dnd_mute = True
        elif action == "setunmute":
            self.__force = True
            self.__dnd_mute = False
        else:
            self.__force = False
            self.__dnd_mute = False
    
    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        try:
            akuvoxDND (self.__force, self.__dnd_mute)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception(
                "[%s] Error contacting akuvox monitor: %s",
                event_id,
                self.__filename,
            )

    def __str__(self) -> str:
        if self.__force:
            return f"Force Akuvox mute={self.__dnd_mute}"
        else:
            return f"Get Akuvox mute status"

    def __repr__(self) -> str:
        return f"akuvox:{self.__force},{self.__dnd_mute}"
