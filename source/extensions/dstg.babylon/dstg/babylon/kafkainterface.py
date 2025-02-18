import asyncio
from typing import Any, Callable, Dict
from dataclasses import dataclass
import msgpack
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import uuid
import socket
from queue import Queue

@dataclass(frozen=True)
class DataRequest:  # Fixed naming to be PEP8 compliant
    requesttype: str
    requestdata: Dict[str, Any]  # Changed to Dict instead of str to avoid serialization issues
    requesthandler: Callable[[Any], Any]

class LambdaStorage:
    def __init__(self):
        self.function_store: Dict[str, Callable] = {}

    def store_function(self, *, uuid: str, func: Callable):
        self.function_store[uuid] = func

    def get_function(self, *, function_id: str) -> Callable:
        return self.function_store.get(function_id)

    def remove_function(self, *, function_id: str) -> bool:
        if function_id in self.function_store:
            del self.function_store[function_id]
            return True
        return False

    def execute_function(self, *, function_id: str, **kwargs) -> Any:
        func = self.get_function(function_id=function_id)
        if func is None:
            raise KeyError(f"No function found with ID: {function_id}")
        result = func(kwargs)  # Execute before removal to handle any exceptions
        self.remove_function(function_id=function_id)
        return result

class AsyncKafkaHandler:
    def __init__(self, kafka_host="localhost:9092", group_id="PythonGroup"):
        self.kafka_host = kafka_host
        self.producer = AIOKafkaProducer(
            bootstrap_servers=kafka_host,
            client_id=socket.gethostname(),
            value_serializer=lambda v: msgpack.packb(v, use_bin_type=True)  # Consistent serialization
        )
        self.consumer = None
        self.group_id = group_id
        self.message_queue = Queue()
        self.messagehandlers = LambdaStorage()

    async def start_producer(self):
        await self.producer.start()

    async def stop_producer(self):
        await self.producer.stop()

    async def send_request(self, *, request: datarequest):
        request_id = None
        try:
            unique_id = uuid.uuid4().hex
            logger.info(f"Preparing request {unique_id}")
            logger.info(f"Topic: {request.requesttype}")
            logger.info(f"Request data: {request.requestdata}")
            sys.stdout.flush()

            # Store handler first
            self.messagehandlers.store_function(uuid=unique_id, func=request.requesthandler)
            logger.info(f"Stored handler for {unique_id}")
            sys.stdout.flush()

            # Prepare the message
            if isinstance(request.requestdata, str):
                try:
                    request_data = eval(request.requestdata)
                    logger.info("Converted string request data to dict")
                except:
                    request_data = {"data": request.requestdata}
                    logger.info("Wrapped string request data")
                sys.stdout.flush()
            else:
                request_data = request.requestdata

            # Pack the message
            packed_data = msgpack.packb(request_data, use_bin_type=True)
            logger.info(f"Packed message size: {len(packed_data)} bytes")
            sys.stdout.flush()

            # Send the message
            logger.info(f"Sending message to topic {request.requesttype}")
            sys.stdout.flush()

            send_task = self.producer.send(
                topic=request.requesttype,
                key=unique_id.encode('utf-8'),
                value=packed_data
            )

            # Wait for the result
            result = await send_task
            logger.info(f"Message sent to partition {result.partition} at offset {result.offset}")
            sys.stdout.flush()

            # Ensure message is sent
            await self.producer.flush()
            logger.info("Producer flushed")
            sys.stdout.flush()

            request_id = unique_id
            return request_id

        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            sys.stdout.flush()
            if request_id and request_id in self.messagehandlers.function_store:
                self.messagehandlers.remove_function(function_id=request_id)
                logger.info(f"Cleaned up handler for failed request {request_id}")
                sys.stdout.flush()
            raise

    async def consume_messages(self, *, topic):
        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.kafka_host,
            group_id=self.group_id,
            max_partition_fetch_bytes=104857600,
            fetch_max_wait_ms= 2000,
            auto_offset_reset='earliest',
            value_deserializer=lambda v: msgpack.unpackb(v, raw=False)
        )

        await self.consumer.start()
        print(f"Consumer started listening to topic: {topic}")

        try:
            async for msg in self.consumer:
                try:
                    key = msg.key.decode('utf-8') if msg.key else None
                    value = msg.value
                    # print(f"Received message - Key: {key}, Value: {value}")
                    self.message_queue.put((key, value))
                except Exception as e:
                    print(f"Error processing message: {e}")
        finally:
            await self.consumer.stop()

    def run_queued_messages(self):
        messages = []
        while not self.message_queue.empty():
            key, value = self.message_queue.get()
            try:
                result = self.messagehandlers.execute_function(function_id=key, kwargs=value)
                messages.append(result)
            except Exception as e:
                print(f"Error executing handler for message {key}: {e}")
        return messages

class KafkaInterface:

    def __init__(self, *args, **kwargs):
      #  super().__init__(*args, **kwargs)
        self.kafka_handler = None
        self.consumer_task = None
        print("kafka running")

    def start_polling(self):
        """Start polling for messages using Omniverse's update subscription"""
        if not self._is_polling:
            self._is_polling = True
            # Use weak reference to prevent memory leaks
            weak_self = weakref.ref(self)

            def _update(dt):
                self_ref = weak_self()
                if self_ref is not None and self_ref._is_polling:
                    self_ref._check_messages()
                return True

            # Subscribe to update events using Omniverse's update mechanism
            self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                _update, name="kafka_polling"
            )

    # Function to run everything
    async def connect(self):
        self.kafka_handler = AsyncKafkaHandler(kafka_host="localhost:9092", group_id="PythonGroup")

        # Start the producer
        await self.kafka_handler.start_producer()

        # Create a non-blocking background task for consuming messages
        self.consumer_task = asyncio.create_task(self.kafka_handler.consume_messages(topic= "DatabaseResult"))

    # kafka_handler, consumer_task = await main()

    # await kafka_handler.send_request(request= request)

    async def write_request(self, *, database: str, write:str, response: Callable[[Any], Any]):
        request:Dict[str,str] = {"operation": "write",
                                "DBName": f"{database}",
                                "dbmod": "nil",}
        request["values"] = write
        await self.kafka_handler(request= datarequest(requesttype="DatabaseWrite", requestdata= request, requesthandler= response))

    # passing handler due to issues with threads?!?!?
    async def query_request(self, *, handler:Callable[[Any], None], database: str, query:str, response: Callable[[Any], Any]):
        request:Dict[str,str] = {"operation": "query",
                                "DBName": f"{database}",
                                "dbmod": "nil",}
        request["values"] = query
        await handler.send_request(request= datarequest(requesttype="DatabaseQuery", requestdata= request, requesthandler= response))

    # await query_request(handler= kafka_handler.send_request, database= "TestDB", query=testquery, response= lambda value: value)


    # result = kafka_handler.run_queued_messages()

# testquery = "[:find ?entityid :where [?entityid :object/name \"edb53fcf32e6719898250de3c56d8027_T_76E4DE7E4882FF9239EA5B90A4784148\"]]"