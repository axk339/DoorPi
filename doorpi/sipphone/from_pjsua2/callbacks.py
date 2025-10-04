"""Callbacks from the native library."""
# pylint: disable=protected-access, invalid-name
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Tuple

import pjsua2 as pj

import doorpi

from . import fire_event

if TYPE_CHECKING:
    from . import glue

LOGGER: doorpi.DoorPiLogger = logging.getLogger(__name__)  # type: ignore


class AccountCallback(pj.Account):
    def __init__(self) -> None:
        pj.Account.__init__(self)

    # pylint: disable=arguments-differ
    def onIncomingCall(self, iprm: pj.OnIncomingCallParam) -> None:
        sp: glue.Pjsua2 = doorpi.INSTANCE.sipphone  # type: ignore
        call = CallCallback(self, iprm.callId)
        callInfo = call.getInfo()
        oprm = pj.CallOpParam(False)
        event = None

        fire_event("BeforeCallIncoming", remote_uri=callInfo.remoteUri)

        try:
            if not sp.is_admin(callInfo.remoteUri):
                LOGGER.info(
                    "Rejecting call from unregistered number %s",
                    callInfo.remoteUri,
                )
                oprm.statusCode = pj.PJSIP_SC_FORBIDDEN
                event = "OnCallReject"
            else:
                with sp._call_lock:
                    if (
                        sp.current_call is not None
                        and sp.current_call.isActive()
                    ):
                        LOGGER.info(
                            "Busy-rejecting call from %s", callInfo.remoteUri
                        )
                        oprm.statusCode = pj.PJSIP_SC_BUSY_HERE
                        event = "OnCallBusy"
                    else:
                        LOGGER.info(
                            "Accepting incoming call from %s",
                            callInfo.remoteUri,
                        )
                        oprm.statusCode = pj.PJSIP_SC_OK
                        event = "OnCallIncoming"
                        sp.current_call = call
            call.answer(oprm)
            fire_event(event, remote_uri=callInfo.remoteUri)
        except Exception:
            LOGGER.exception("Error while handling incoming call")
            oprm.statusCode = pj.PJSIP_SC_FORBIDDEN
            call.answer(oprm)


class CallCallback(pj.Call):
    def __init__(
        self,
        acc: AccountCallback,
        callId: int = pj.PJSUA_INVALID_ID,
    ) -> None:
        LOGGER.trace("Constructing call with callId %s", callId)
        super().__init__(acc, callId)

        self.__dtmf = ""
        self.__possible_dtmf = doorpi.INSTANCE.config.view(
            "sipphone.dtmf"
        ).keys()
        self.__call_answered = False

    def __getAudioVideoMedia(self) -> Tuple[pj.AudioMedia, pj.VideoMedia]:
        """Helper function that returns the first audio and video media"""

        audio = None
        video = None
        ci = self.getInfo()
        for i in range(len(ci.media)):
            if ci.media[i].type == pj.PJMEDIA_TYPE_AUDIO and audio is None:
                audio = self.getAudioMedia(i)
            if ci.media[i].type == pj.PJMEDIA_TYPE_VIDEO and video is None:
                video = self.vidStreamIsRunning(i, pj.PJMEDIA_DIR_CAPTURE)
        return (audio, video)

    def onCallState(self, prm: pj.OnCallStateParam) -> None:
        ci = self.getInfo()
        sp: glue.Pjsua2 = doorpi.INSTANCE.sipphone  # type: ignore

        if ci.state == pj.PJSIP_INV_STATE_CALLING:
            LOGGER.debug("Call to %r is now calling", ci.remoteUri)
        elif ci.state == pj.PJSIP_INV_STATE_INCOMING:
            LOGGER.debug("Call from %r is coming in", ci.remoteUri)
        elif ci.state == pj.PJSIP_INV_STATE_EARLY:
            LOGGER.debug("Call to %r is in early state", ci.remoteUri)
        elif ci.state == pj.PJSIP_INV_STATE_CONNECTING:
            LOGGER.debug("Call to %r is now connecting", ci.remoteUri)
        elif ci.state == pj.PJSIP_INV_STATE_CONFIRMED:
            LOGGER.info("Call to %r was accepted", ci.remoteUri)
            self.__call_answered = True
            with sp._call_lock:
                prm = pj.CallOpParam()
                #akx - incoming call set above in AccountCallback already as current_call, gets hungup with beliw check!
                if sp.current_call is not None:
                    LOGGER.info("Current call in PJSIP_INV_STATE_CONFIRMED: %r", sp.current_call.getInfo().remoteUri)
                #    # (note: this should not be possible)
                #    sp.current_call.hangup(prm)
                #    sp.current_call = None

                sp.current_call = self
                for ring in sp._ringing_calls:
                    if self != ring:
                        ring.hangup(prm)
                sp._ringing_calls = []
                sp._waiting_calls = []
                fire_event("OnCallConnect", remote_uri=ci.remoteUri)
        elif ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
            LOGGER.info(
                "Call to %r disconnected after %d seconds (%d total)",
                ci.remoteUri,
                ci.connectDuration.sec,
                ci.totalDuration.sec,
            )
            if sp.current_call == self:
                sp.current_call = None
                LOGGER.trace(
                    "Firing disconnect event for call to %r", ci.remoteUri
                )
                fire_event("OnCallDisconnect", remote_uri=ci.remoteUri)
            elif self in sp._ringing_calls:
                sp._ringing_calls.remove(self)

            if len(sp._ringing_calls) == 0 and not self.__call_answered:
                LOGGER.info("No call was answered")
                fire_event("OnCallUnanswered")
            else:
                LOGGER.trace(
                    "Skipping disconnect event for call to %r",
                    ci.remoteUri,
                )
        else:
            LOGGER.warning(
                "Call to %r: unknown state %d", ci.remoteUri, ci.state
            )

    def onCallMediaState(self, prm: pj.OnCallMediaStateParam) -> None:
        ci = self.getInfo()
        #fix connecting incoming calls (state 2)
        #important to keep supressing other media, e.g. state 3 is ring-tone (overrides doorpi dialtone player)
        #if ci.state != pj.PJSIP_INV_STATE_CONFIRMED:
        if ci.state != pj.PJSIP_INV_STATE_CONFIRMED and ci.state != 2:
            LOGGER.debug("Ignoring media change in call to %r", ci.remoteUri)
            return

        adm = pj.Endpoint.instance().audDevManager()
        # vdm = pj.Endpoint.instance().vidDevManager()
        LOGGER.debug("Call to %r: media changed", ci.remoteUri)
        audio, video = self.__getAudioVideoMedia()

        # TODO Although the video should be automatically started (config.account_config)
        # it would be beneficial to check if it is actually running. Yet
        # a corresponding hw/sw with no video capability would error out on this
        # so there has to be a check accordingly, yet i couldn't decipher the source code in that regard

        # if not video:
        #     __params = pj.CallVidSetStreamParam()
        #     __params.dir = pj.PJMEDIA_DIR_CAPTURE
        #     self.vidSetStream(pj.PJSUA_CALL_VID_STRM_ADD, __params)
        if audio:
            #adding echo cancellation
            #- setEcOptions > https://docs.pjsip.org/en/2.10/pjsua2/media.html#device-manager
            #- setEcOptions / options > pjmedia_echo_create> https://docs.pjsip.org/en/2.10/api/generated/pjmedia/group/group__PJMEDIA__Echo__Cancel.html#group__PJMEDIA__Echo__Cancel_1ga6b2a27be70d96eb16fac66f19b6913d3
            #- pjmedia_echo_create / options > pjmedia_echo_cancel > https://docs.pjsip.org/en/2.10/api/generated/pjmedia/group/group__PJMEDIA__Echo__Cancel.html#group__PJMEDIA__Echo__Cancel_1gaa92df3d6726a21598e25bf5d4a23897e
            #- pjmedia_echo_cancel / AEC3 > https://github.com/pjsip/pjproject/pull/2722
            adm.setEcOptions(100, pj.PJMEDIA_ECHO_WEBRTC_AEC3)
            # Connect call audio to speaker and microphone
            audio.startTransmit(adm.getPlaybackDevMedia())
            adm.getCaptureDevMedia().startTransmit(audio)
            # Apply capture and ring tone loudness
            conf = doorpi.INSTANCE.config
            playback_loudness = conf["sipphone.playback.loudness"]
            capture_loudness = conf["sipphone.capture.loudness"]
            LOGGER.trace("Adjusting RX level to %01.1f", playback_loudness)
            LOGGER.trace("Adjusting TX level to %01.1f", capture_loudness)
            audio.adjustRxLevel(playback_loudness)
            audio.adjustTxLevel(capture_loudness)
        else:
            LOGGER.error("Call to %r: no audio media", ci.remoteUri)

    def onDtmfDigit(self, prm: pj.OnDtmfDigitParam) -> None:
        LOGGER.debug("Received DTMF: %s", prm.digit)

        self.__dtmf += prm.digit
        LOGGER.trace(
            "Processing digit %s; current sequence is %s",
            prm.digit,
            self.__dtmf,
        )

        prefix = False
        exact = False
        for dtmf in self.__possible_dtmf:
            if dtmf == self.__dtmf:
                exact = True
            elif dtmf.startswith(self.__dtmf):
                prefix = True

        if exact:
            remoteUri = self.getInfo().remoteUri
            fire_event(
                f"OnDTMF_{self.__dtmf}", async_only=True, remote_uri=remoteUri
            )
            self.dialDtmf("11")

        if not prefix:
            if not exact:
                self.dialDtmf("#")
            self.__dtmf = ""
