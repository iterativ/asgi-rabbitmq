import time
from collections import defaultdict

import pytest
from asgi_ipc import IPCChannelLayer
from asgi_rabbitmq import RabbitmqChannelLayer
from asgiref.conformance import ConformanceTestCase
from channels.asgi import ChannelLayerWrapper
from channels.routing import null_consumer, route
from channels.worker import Worker


class RabbitmqChannelLayerTest(ConformanceTestCase):

    @pytest.fixture(autouse=True)
    def init_conformance_test(self, vhost, management):

        url = '%s?heartbeat_interval=%d' % (vhost, self.heartbeat_interval)
        self.channel_layer = RabbitmqChannelLayer(
            url,
            expiry=1,
            group_expiry=2,
            capacity=self.capacity_limit,
        )
        self.management = management

    @property
    def defined_queues(self):
        """Get queue names defined in current vhost."""

        definitions = self.management.get_definitions()
        queue_definitions = defaultdict(set)
        for queue in definitions['queues']:
            queue_definitions[queue['vhost']].add(queue['name'])
        queues = queue_definitions[self.channel_layer.parameters.virtual_host]
        return queues

    expiry_delay = 1.1
    capacity_limit = 5
    heartbeat_interval = 15

    def test_send_to_empty_group(self):
        """Send to empty group works as usual."""

        self.skip_if_no_extension('groups')
        self.channel_layer.send_group('tgroup_1', {'value': 'orange'})

    def test_discard_from_empty_group(self):
        """Discard from empty group works as usual."""

        self.skip_if_no_extension('groups')
        self.channel_layer.group_discard('tgroup_2', 'tg_test3')

    def test_group_persistence_message_expiry(self):
        """
        Discard channel from all its groups when first message expires in
        channel.
        """

        # Setup group membership.
        self.skip_if_no_extension('groups')
        self.channel_layer.group_add('tgme_group1', 'tgme_test')
        self.channel_layer.group_add('tgme_group2', 'tgme_test')
        self.channel_layer.send('tgme_test', {'hello': 'world'})
        # Wait until message in the channel expires.
        time.sleep(self.channel_layer.expiry)
        # Channel lost its membership in the group #1.
        self.channel_layer.send_group('tgme_group1', {'hello': 'world1'})
        channel, message = self.channel_layer.receive(['tgme_test'])
        self.assertIs(channel, None)
        self.assertIs(message, None)
        # Channel lost its membership in the group #2.
        self.channel_layer.send_group('tgme_group2', {'hello': 'world2'})
        channel, message = self.channel_layer.receive(['tgme_test'])
        self.assertIs(channel, None)
        self.assertIs(message, None)

    def test_connection_heartbeats(self):
        """
        We must answer for RabbitMQ heartbeat frames responsively.
        Otherwise connection will be closed by server.
        """

        self.channel_layer.send('x', {'foo': 'bar'})
        channel, message = self.channel_layer.receive(['x'])
        time.sleep(self.heartbeat_interval * 3)
        # Code below will throw an exception if we don't send
        # heartbeat frames during sleep.
        self.channel_layer.send('x', {'baz': 'quux'})
        channel, message = self.channel_layer.receive(['x'])

    @pytest.mark.xfail
    def test_group_channels(self):

        # TODO: figure out how to check group membership.
        super(RabbitmqChannelLayerTest, self).test_group_channels()

    def test_declare_queues_on_worker_ready(self):
        """Declare necessary queues after worker start."""

        wrapper = ChannelLayerWrapper(
            channel_layer=self.channel_layer,
            alias='default',
            # NOTE: Similar to `channels.routing.Router.check_default` result.
            routing=[
                route('http.request', null_consumer),
                route('websocket.connect', null_consumer),
                route('websocket.receive', null_consumer),
            ],
        )
        worker = Worker(channel_layer=wrapper, signal_handlers=False)
        worker.ready()
        assert self.defined_queues == {
            'http.request',
            'websocket.receive',
            'websocket.connect',
        }

    def test_skip_another_layer_on_worker_ready(self):
        """
        Don't try to declare rabbit queues if worker uses another layer
        implementation.
        """

        wrapper = ChannelLayerWrapper(
            channel_layer=IPCChannelLayer(),
            alias='default',
            # NOTE: Similar to `channels.routing.Router.check_default` result.
            routing=[
                route('http.request', null_consumer),
                route('websocket.connect', null_consumer),
                route('websocket.receive', null_consumer),
            ],
        )
        worker = Worker(channel_layer=wrapper, signal_handlers=False)
        worker.ready()
        assert not self.defined_queues

    # FIXME: test_capacity fails occasionally.
    #
    # Maybe first message succeeds to expire so message count don't
    # cross capacity border.

    # FIXME: not so much working right now:

    @pytest.mark.xfail
    def test_send_recv(self):
        super(RabbitmqChannelLayerTest, self).test_send_recv()

    @pytest.mark.xfail
    def test_message_expiry(self):
        super(RabbitmqChannelLayerTest, self).test_message_expiry()

    @pytest.mark.xfail
    def test_new_channel_single_reader(self):
        super(RabbitmqChannelLayerTest, self).test_new_channel_single_reader()

    @pytest.mark.xfail
    def test_new_channel_single_process(self):
        super(RabbitmqChannelLayerTest, self).test_new_channel_single_process()

    @pytest.mark.xfail
    def test_new_channel_failures(self):
        super(RabbitmqChannelLayerTest, self).test_new_channel_failures()

    @pytest.mark.xfail
    def test_strings(self):
        super(RabbitmqChannelLayerTest, self).test_strings()

    @pytest.mark.xfail
    def test_groups(self):
        super(RabbitmqChannelLayerTest, self).test_groups()

    @pytest.mark.xfail
    def test_flush(self):
        super(RabbitmqChannelLayerTest, self).test_flush()

    @pytest.mark.xfail
    def test_flush_groups(self):
        super(RabbitmqChannelLayerTest, self).test_flush_groups()

    @pytest.mark.xfail
    def test_group_expiry(self):
        super(RabbitmqChannelLayerTest, self).test_group_expiry()

    @pytest.mark.xfail
    def test_capacity(self):
        super(RabbitmqChannelLayerTest, self).test_capacity()

    @pytest.mark.xfail
    def test_exceptions(self):
        super(RabbitmqChannelLayerTest, self).test_exceptions()

    @pytest.mark.xfail
    def test_message_alteration_after_send(self):
        super(RabbitmqChannelLayerTest,
              self).test_message_alteration_after_send()
