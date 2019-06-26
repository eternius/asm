import asyncio
import logging
import nest_asyncio

from rasa.core.tracker_store import TrackerStore, EventVerbosity
from rasa.core.broker import EventChannel
from rasa.core.domain import Domain
from typing import Optional, Text, Iterable
from rasa.core.trackers import DialogueStateTracker

_LOGGER = logging.getLogger(__name__)


class ArcusTrackerStore(TrackerStore):
    def __init__(
        self, domain: Domain, asm, event_broker: Optional[EventChannel] = None
    ) -> None:
        self.store = {}
        self.asm = asm
        nest_asyncio.apply()
        super(ArcusTrackerStore, self).__init__(domain, event_broker)

    def save(self, tracker: DialogueStateTracker) -> None:
        if self.event_broker:
            self.stream_events(tracker)
        state = tracker.current_state(EventVerbosity.ALL)
        asyncio.get_event_loop().run_until_complete(self.asm.memory.put("rasa_tracker",
                                                                        tracker.sender_id,
                                                                        state))

    def retrieve(self, sender_id: Text) -> Optional[DialogueStateTracker]:
        tracker = asyncio.get_event_loop().run_until_complete(self.asm.memory.get("rasa_tracker", sender_id))
        if tracker:
            _LOGGER.debug("Recreating tracker for id '{}'".format(sender_id))
            return DialogueStateTracker.from_dict(
                sender_id, tracker.getStore()['events'], self.domain.slots
            )
        else:
            _LOGGER.debug("Creating a new tracker for id '{}'.".format(sender_id))
            return None

    @property
    def keys(self) -> Iterable[Text]:
        keys = asyncio.get_event_loop().run_until_complete(self.asm.memory.get_keys("rasa_tracker"))
        return keys
