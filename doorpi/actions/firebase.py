"""BRI 14.07.2025 Action that sends a firebase message"""
import logging
import pathlib
from typing import Any, Mapping

import firebase_admin
from firebase_admin import credentials, messaging
from threading import Thread

import doorpi.actions
from doorpi.status.status_class import DoorPiStatus
from doorpi.actions import snapshot

import datetime

from . import Action

LOGGER = logging.getLogger(__name__)

#/home/pi/DoorPi/DoorPi.egg-info/entry_points.txt

firebaseInit = False
def firebase_init():
    global firebaseInit
    LOGGER.debug ("Firebase init firebaseInit=" + str(firebaseInit))
    if (not firebaseInit):
        try:
            firebaseInit = True
            firebase_cred = credentials.Certificate(doorpi.INSTANCE.config["firebase.adminjson"])
            firebase_app  = firebase_admin.initialize_app(firebase_cred)
            LOGGER.info ("Firebase initated")
        except Exception as e:
            LOGGER.info ("Firebase error: " + str(e))

def send_topic_push(channel, requestPrio, timestamp, title, body, snapshot):
    thrf = Thread (target=send_topic_push_thr, args=[channel, requestPrio, timestamp, title, body, snapshot])
    thrf.start()
    LOGGER.debug ("Firebase thread started")
    
def send_topic_push_thr(channel, requestPrio, timestamp, title, body, snapshot):
    try:
        topic = channel
        prio = "normal"
        if requestPrio != "normal": prio = "high"
        message = messaging.Message(
            android=messaging.AndroidConfig(
                #ttl=datetime.timedelta(seconds=3600),
                priority=prio,
                data = {
                    "topic"     : channel,
                    "title"     : title,
                    "body"      : body,
                    "snapshot"  : snapshot,
                    "timestamp" : timestamp,
                    "prio"      : requestPrio
                },
            ),
            topic=topic
        )
        messaging.send(message)
        LOGGER.info ("Sent message '" + title + "' > " + channel + "/" + requestPrio + ", FBM " + prio)
    except Exception as e:
        LOGGER.info ("Firebase error: " + str(e))
    
class FirebaseAction(Action):
    """Sends a firebase message"""

    def __init__(self, topic: str, title: str, content: str) -> None:
        super().__init__()
        self.__content = content
        self.__topic = topic
        self.__title = title
        firebase_init()
        
    def __call__(self, event_id: str, extra: Mapping[str, Any]) -> None:
        snapfile = str(snapshot.SnapshotAction.list_all()[-1])[32:] 
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        send_topic_push(self.__topic, "normal", timestamp, self.__title, self.__content, snapfile)
        
    def __str__(self) -> str:
        return f"Send firebase message '{self.__title}' > '{self.__content}' in topic {self.__topic}"

    def __repr__(self) -> str:
        return f"firebase_{self.__topic}:{self.__title}"
