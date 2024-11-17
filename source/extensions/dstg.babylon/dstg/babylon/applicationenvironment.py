
import logging
logger = logging.getLogger(__name__)

from typing import TYPE_CHECKING # type: ignore

if TYPE_CHECKING:

    from .stageinterface import StageInterface
    from .omnikafkainterface import OmniKafkaInterface


class ApplicationEnvironment(object):
    def __init__(self) -> None:
        super().__init__()


        self._stage_interface = None
        self._omni_kafka_interface = None




    @property
    def Stage_Interface(self) -> 'StageInterface':
        return self._stage_interface

    @Stage_Interface.setter
    def Stage_Interface(self, st : 'StageInterface'):
        self._stage_interface = st

    @property
    def Omni_Kafka_Interface(self) -> 'OmniKafkaInterface':
        return self._omni_kafka_interface

    @Omni_Kafka_Interface.setter
    def Omni_Kafka_Interface(self, kf : 'OmniKafkaInterface'):
        self._omni_kafka_interface = kf


applicationenvironment = ApplicationEnvironment()