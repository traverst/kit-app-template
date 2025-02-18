import asyncio
import socket
import uuid
import msgpack
import sys
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from queue import Queue
import omni.kit.app
import carb
import weakref

import omni.kit.utils

import gc

import time

from typing import Optional, Dict, Any, Callable

### LambdaStorage

# This class stores the a function (by a generated uuid) and then later will execute at fuction (recalled by uuid)
# with the provided parameters.

class LambdaStorage:
    def __init__(self):
        self.function_store: Dict[str, Callable] = {}

    def store_function(self, *, uuid: str, func: Callable):
        """
        Store a function and return its UUID key
        """
        self.function_store[uuid] = func

    def get_function(self, *, function_id: str) -> Callable:
        """
        Retrieve a function by its UUID
        """
        return self.function_store.get(function_id)

    def remove_function(self, *, function_id: str) -> bool:
        """
        Remove a function from the store by its UUID

        Returns:
            bool: True if function was removed, False if it didn't exist
        """
        if function_id in self.function_store:
            del self.function_store[function_id]
            return True
        return False

    def execute_function(self, *, function_id: str, **kwargs) -> Any:
        """
        Execute a stored function with provided arguments
        """
        func = self.get_function(function_id = function_id) # retrieve the function matching the key.
        self.remove_function(function_id = function_id) # don't need it anymore.
        if func is None:
            raise KeyError(f"No function found with ID: {function_id}")
        return func(kwargs)


### datarequest

#Stores the data as a group.  Consisting of the request type (the kafka topics... DatabaseQuery, DatabaseWrite)
#The actual data being sent (the query or the write in datalog)
#and the function to run on the results of the request...

from dataclasses import dataclass

@dataclass(frozen=True)
class datarequest:
    requesttype : str
    requestdata : str # stringafied dict (this probably isn't a good idea!)
    requesthandler : Callable[[Any], Any]


class OmniKafkaHandler:
    def __init__(self, kafka_host="localhost:9092", group_id="Omniverse"):
        self.kafka_host = kafka_host
        self.producer = AIOKafkaProducer(
            bootstrap_servers=kafka_host,
            client_id=socket.gethostname()
        )
        self.consumer = None
        self.group_id = group_id
        self.messagehandlers = LambdaStorage()
        self._is_consuming = False
        self._update_sub = None
        self._poll_task = None

    async def start(self, topic: str):
        """Start both producer and consumer"""
        await self.start_producer()
        await self.start_consumer(topic)
        carb.log_info(f"Consuming {topic} and starting polling")
        self.start_polling()

    async def start_producer(self):
        """Start the Kafka producer"""
        await self.producer.start()

    async def start_consumer(self, topic: str):
        """Initialize the Kafka consumer"""
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.kafka_host,
            group_id=self.group_id,
            auto_offset_reset='earliest',
            max_partition_fetch_bytes=50 * 1024 * 1024,  # Increase to 50MB (adjust as needed)
            fetch_max_bytes=50 * 1024 * 1024,  # Increase the max fetch bytes
            request_timeout_ms=30000,  # Increase timeout
            # Critical timeouts for heavy processing
            session_timeout_ms= 300 * 1000 ,  # 45 secs
            max_poll_interval_ms=300000,    # Default 5m → 5m (adjust based on USD op duration)
            heartbeat_interval_ms=10000,     # `10 secs`
            max_poll_records=100            # Reduce batch size for USD workloads
        )
        await self.consumer.start()
        carb.log_info("Kafka consumer initialized")



    def start_polling(self):
        """Start polling for messages using Omniverse's update subscription"""
        if not self._is_consuming:
            self._is_consuming = True
            # Use weak reference to prevent memory leaks
            weak_self = weakref.ref(self)
            carb.log_info("starting the polling")

            async def _poll_messages():
                """Poll for messages from Kafka"""
                try:
                    if self.consumer:
                        #messages = await self.consumer.getmany(timeout_ms=100)
                        msg = await self.consumer.getone()

             #           for tp, msgs in messages.items():
            #               for msg in msgs:
                        try:
                            carb.log_info(f"Received message at {time.time()}: {len(msg.value)} bytes")
                            start = time.time()
                            carb.log_info(f"Starting ...{start}")  # Debug log
                            key = str(msg.key.decode('utf-8')) if msg.key else None

                            gc.disable()
                            value = msgpack.unpackb(msg.value, raw=False)
                            gc.enable()

                            # Process message immediately
                            # carb.log_info(f"Key {key} Value: {value}")
                            if key and key in self.messagehandlers.function_store:
                                carb.log_info("execute function")

                                self.messagehandlers.execute_function(
                                    function_id=key,
                                    kwargs=value
                                )
                            finish = time.time()
                            carb.log_info(f".... finished {finish} with elapsed: {finish - start} secs")  # Debug log
                        except Exception as e:
                            carb.log_error(f"Error processing message: {e}")
                except Exception as e:
                    carb.log_error(f"Error polling messages: {e}")
                return True

            # def _update(dt):
            #     self_ref = weak_self()
            #     if self_ref is not None and self_ref._is_consuming:
            #         # Schedule the async poll in Omniverse's event loop
            #         asyncio.run_coroutine_threadsafe(_poll_messages(), asyncio.get_event_loop())
            #     return True
            def _update(dt):
                self_ref = weak_self()
                if self_ref is not None and self_ref._is_consuming:
                    loop = asyncio.get_event_loop()  # Ensures an event loop is retrieved safely
                    self._poll_task = loop.create_task(_poll_messages())  # Schedule as a task, allows carb logs # record for shutdown!
                return True

            # Subscribe to update events using Omniverse's update mechanism
            self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                _update, name="kafka_consumer_polling"
            )


    async def stop(self):
        """Stop both producer and consumer"""
        self.stop_polling()
        await self.stop_producer()
        await self.stop_consumer()

    async def stop_producer(self):
        """Stop the Kafka producer"""
        await self.producer.stop()

    async def stop_consumer(self):
        """Stop the Kafka consumer"""
        if self.consumer:
            await self.consumer.stop()

    def stop_polling(self):
        """Stop polling for messages"""
        self._is_consuming = False
        if self._poll_task:
            self._poll_task.cancel()  # cancel the poll task!
            self._poll_taks = None
        if self._update_sub is not None:
            self._update_sub.unsubscribe()
            self._update_sub = None

    async def send_message(self, *, topic: str, key_value: str, message_to_send: Any):
        carb.log_info("send_message called.")
        key_bytes = key_value.encode('utf-8') if key_value else None
        try:
            await self.producer.send_and_wait(
                topic,
                key=key_bytes,
                value=msgpack.packb(message_to_send, use_bin_type=True)
            )
            carb.log_info("Message sent successfully.")
        except Exception as e:
            carb.log_error(f"Failed to send message: {e}")


    async def send_request(self, *, request: datarequest):
        """Send a request to Kafka with a unique ID"""
        carb.log_info("send_request")

        unique_id = uuid.uuid4().hex
        self.messagehandlers.store_function(uuid=unique_id, func=request.requesthandler)
        await self.send_message(
            topic=request.requesttype,
            key_value=unique_id,
            message_to_send=request.requestdata
        )
        return unique_id

class OmniKafkaInterface:
    def __init__(self, kafka_host="localhost:9092", group_id="Omniverse"):
        self.kafka_handler = None
        self.kafka_host = kafka_host
        self.group_id = group_id
        carb.log_info("Initializing OmniKafkaInterface")

    async def connect(self, result_topic="DatabaseResult"):
        """Connect to Kafka and start consuming messages"""
        self.kafka_handler = OmniKafkaHandler(
            kafka_host=self.kafka_host,
            group_id=self.group_id
        )
        await self.kafka_handler.start(result_topic)
        carb.log_info("Kafka connection established")

    async def disconnect(self):
        """Disconnect from Kafka"""
        if self.kafka_handler:
            await self.kafka_handler.stop()
            carb.log_info("Kafka connection closed")

    async def write_request(self, *, database: str, write: str, response: Callable[[Any], Any]):
        """Send a write request to Kafka"""
        request: Dict[str, str] = {
            "operation": "write",
            "DBName": f"{database}",
            "dbmod": "nil",
            "values": write
        }
        await self.kafka_handler.send_request(
            request=datarequest(
                requesttype="DatabaseWrite",
                requestdata=request,
                requesthandler=response
            )
        )

    async def query_request(self, *, database: str, query: str, response: Callable[[Any], Any]):
        """Send a query request to Kafka"""
        carb.log_info("query_request")

        request: Dict[str, str] = {
            "operation": "query",
            "DBName": f"{database}",
            "dbmod": "nil",
            "values": query
        }
        await self.kafka_handler.send_request(
            request=datarequest(
                requesttype="DatabaseQuery",
                requestdata=request,
                requesthandler=response
            )
        )